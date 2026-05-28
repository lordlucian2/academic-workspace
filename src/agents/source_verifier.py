import os
import json
import re
from openai import OpenAI
from dotenv import load_dotenv
from typing import List
from src.models.schemas import RawPaper, VerifiedPaper, VerificationResult

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

FREE_MODELS = [
    "openai/gpt-oss-20b:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
]

VERIFIER_PROMPT = """You are a source verifier for academic writing. Review each paper and decide whether to keep it.

Rules for removal (keep=False):
1. Retracted papers (no specific evidence, but you can infer from low citation count if paper is old)
2. Papers more than 20 years old (unless they are seminal – use judgment)
3. Completely irrelevant to the main topic
4. Predatory journal suspicion (venue name looks like fake conference)

Rules for keeping (keep=True):
- Relevant to the prompt
- Reasonable year (last 20 years or seminal)
- At least moderate relevance

For each paper, provide a short reason.

Return ONLY a JSON object with this structure:
{{"verified_papers": [
    {{"title": "original title", "keep": true, "reason": "..."}},
    ...
]}}

Prompt: {prompt}
Education level: {level}

Papers to verify (as JSON array):
{papers_json}

Return only valid JSON, no extra text."""

def fallback_verifier(prompt: str, papers: List[RawPaper]) -> VerificationResult:
    """Fallback: keep all papers with reasonable recency."""
    from datetime import datetime
    current_year = datetime.now().year
    verified = []
    for p in papers:
        # Keep if less than 20 years old
        if p.year and (current_year - p.year) <= 20:
            verified.append(VerifiedPaper(
                title=p.title, authors=p.authors, year=p.year, doi=p.doi,
                url=p.url, citation_count=p.citation_count, venue=p.venue,
                abstract=p.abstract, keep=True, reason="recent (fallback)"
            ))
        elif not p.year:
            # If year missing, keep anyway
            verified.append(VerifiedPaper(
                title=p.title, authors=p.authors, year=p.year, doi=p.doi,
                url=p.url, citation_count=p.citation_count, venue=p.venue,
                abstract=p.abstract, keep=True, reason="year unknown (fallback)"
            ))
        # else: drop old papers without reason
    return VerificationResult(verified_papers=verified)

def verify_sources(prompt: str, papers: List[RawPaper], level: str = "undergraduate") -> VerificationResult:
    """Verify papers using LLM with fallback."""
    if not papers:
        return VerificationResult(verified_papers=[])
    
    # Prepare papers JSON
    papers_compact = []
    for p in papers:
        papers_compact.append({
            "title": p.title,
            "year": p.year,
            "venue": p.venue,
            "citation_count": p.citation_count,
            "abstract": p.abstract[:300] if p.abstract else ""
        })
    papers_json = json.dumps(papers_compact, indent=2)
    formatted_prompt = VERIFIER_PROMPT.format(
        prompt=prompt,
        level=level,
        papers_json=papers_json
    )
    
    for model in FREE_MODELS:
        for attempt in range(3):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are an academic source verifier. Return only valid JSON."},
                        {"role": "user", "content": formatted_prompt}
                    ],
                    temperature=0.2,
                    max_tokens=2000,
                )
                content = response.choices[0].message.content.strip()
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    content = json_match.group(0)
                data = json.loads(content)
                
                # Map back
                verified_papers = []
                for vp_data in data.get("verified_papers", []):
                    original = next((p for p in papers if p.title == vp_data["title"]), None)
                    if original and vp_data.get("keep", False):
                        verified_papers.append(VerifiedPaper(
                            title=original.title, authors=original.authors, year=original.year,
                            doi=original.doi, url=original.url, citation_count=original.citation_count,
                            venue=original.venue, abstract=original.abstract, keep=True,
                            reason=vp_data.get("reason", "LLM accepted")
                        ))
                return VerificationResult(verified_papers=verified_papers)
            except Exception as e:
                print(f"   Verifier attempt {attempt+1} with {model} failed: {str(e)[:100]}")
                continue
        print(f"   Verifier model {model} exhausted, trying next...")
    
    print("   Using fallback verifier (keep recent papers)")
    return fallback_verifier(prompt, papers)
