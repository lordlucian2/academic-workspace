import os
import json
import re
from typing import List, Optional
from openai import OpenAI
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from src.models.schemas import VerifiedPaper

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

# Define Pydantic models for outline
class SourceHook(BaseModel):
    paper_title: str
    paper_id: Optional[str] = None  # DOI or URL for exact matching
    reason: str

class OutlineSubsection(BaseModel):
    id: str
    title: str
    level: int = 2
    source_hooks: List[SourceHook] = Field(default_factory=list)

class OutlineSection(BaseModel):
    id: str
    title: str
    level: int = 1
    subsections: List[OutlineSubsection] = Field(default_factory=list)

class Outline(BaseModel):
    title: str
    sections: List[OutlineSection]

OUTLINE_PROMPT = """You are an academic outline architect. Given a research prompt, education level, assignment type, and a list of verified sources, produce a detailed, logical outline for the document.

Assignment type: {assignment_type}
Education level: {level}
Prompt: {prompt}

Verified sources (title + abstract summary):
{sources_text}

Guidelines:
- Outline should be appropriate for {level} level (highschool: simpler structure, fewer subsections; undergraduate: standard; graduate: more detailed, critical analysis sections)
- Each major section (level 1) should have 2-5 subsections (level 2)
- For each subsection, attach source_hooks (1-3 papers that support that subsection). Use the exact paper titles from the sources list. Include the paper_id as the DOI if available, otherwise the URL.
- Include standard academic sections: Introduction, Methods (if empirical), Results/Discussion, Conclusion. Adjust based on assignment type.

Return a valid JSON object with the following structure:
{{"title": "Suggested Title", "sections": [
    {{"id": "s1", "title": "Introduction", "level": 1, "subsections": [
        {{"id": "s1a", "title": "Background", "level": 2, "source_hooks": [{{"paper_title": "Exact Title", "paper_id": "doi or url", "reason": "why"}}]}}
    ]}}
]}}

Do not include any other text outside the JSON."""

def build_sources_text(papers: List[VerifiedPaper], max_abstract_len: int = 300) -> str:
    """Format verified papers for the prompt."""
    text = ""
    for i, p in enumerate(papers, 1):
        abstract = p.abstract[:max_abstract_len] + "..." if len(p.abstract) > max_abstract_len else p.abstract
        paper_id = p.doi if p.doi else p.url
        text += f"{i}. Title: {p.title} ({p.year})\n   ID: {paper_id}\n   Abstract: {abstract}\n\n"
    return text

def fallback_outline(prompt: str, assignment_type: str, level: str, papers: List[VerifiedPaper]) -> Outline:
    """Rule-based outline when LLM is unavailable."""
    sections = [
        OutlineSection(id="s1", title="Introduction", level=1, subsections=[
            OutlineSubsection(id="s1a", title="Background and Context", level=2),
            OutlineSubsection(id="s1b", title="Problem Statement", level=2),
            OutlineSubsection(id="s1c", title="Research Objectives", level=2)
        ])
    ]
    
    if assignment_type.lower() in ["research paper", "thesis"]:
        sections.append(OutlineSection(id="s2", title="Literature Review", level=1, subsections=[
            OutlineSubsection(id="s2a", title="Key Concepts", level=2),
            OutlineSubsection(id="s2b", title="Previous Findings", level=2),
            OutlineSubsection(id="s2c", title="Gaps in Knowledge", level=2)
        ]))
        sections.append(OutlineSection(id="s3", title="Methodology", level=1, subsections=[
            OutlineSubsection(id="s3a", title="Study Design", level=2),
            OutlineSubsection(id="s3b", title="Data Collection", level=2),
            OutlineSubsection(id="s3c", title="Analysis Approach", level=2)
        ]))
        sections.append(OutlineSection(id="s4", title="Results", level=1, subsections=[
            OutlineSubsection(id="s4a", title="Findings", level=2)
        ]))
        sections.append(OutlineSection(id="s5", title="Discussion", level=1, subsections=[
            OutlineSubsection(id="s5a", title="Interpretation", level=2),
            OutlineSubsection(id="s5b", title="Comparison with Literature", level=2),
            OutlineSubsection(id="s5c", title="Limitations", level=2)
        ]))
    else:
        sections.append(OutlineSection(id="s2", title="Main Body", level=1, subsections=[
            OutlineSubsection(id="s2a", title="Point 1", level=2),
            OutlineSubsection(id="s2b", title="Point 2", level=2),
            OutlineSubsection(id="s2c", title="Point 3", level=2)
        ]))
    
    sections.append(OutlineSection(id="s_last", title="Conclusion", level=1, subsections=[
        OutlineSubsection(id="last_a", title="Summary of Key Points", level=2),
        OutlineSubsection(id="last_b", title="Implications and Future Directions", level=2)
    ]))
    
    # Attach source hooks using DOIs if available
    for i, section in enumerate(sections):
        for j, sub in enumerate(section.subsections):
            idx = i*len(section.subsections) + j
            if idx < len(papers):
                paper = papers[idx]
                paper_id = paper.doi if paper.doi else paper.url
                sub.source_hooks = [SourceHook(paper_title=paper.title, paper_id=paper_id, reason="Relevant to this section")]
    
    title = f"Academic {assignment_type.title()} on {prompt[:50]}"
    return Outline(title=title, sections=sections)

def generate_outline(prompt: str, assignment_type: str, level: str, papers: List[VerifiedPaper]) -> Outline:
    """Main function to generate outline using LLM with fallback."""
    if not papers:
        return fallback_outline(prompt, assignment_type, level, papers)
    
    sources_text = build_sources_text(papers)
    formatted_prompt = OUTLINE_PROMPT.format(
        assignment_type=assignment_type,
        level=level,
        prompt=prompt,
        sources_text=sources_text
    )
    
    for model in FREE_MODELS:
        for attempt in range(3):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are an academic outline architect. Return only valid JSON."},
                        {"role": "user", "content": formatted_prompt}
                    ],
                    temperature=0.4,
                    max_tokens=3000,
                )
                content = response.choices[0].message.content.strip()
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    content = json_match.group(0)
                data = json.loads(content)
                outline = Outline(**data)
                return outline
            except Exception as e:
                print(f"   Outline attempt {attempt+1} with {model} failed: {str(e)[:100]}")
                continue
        print(f"   Outline model {model} exhausted, trying next...")
    
    print("   Using fallback outline generator.")
    return fallback_outline(prompt, assignment_type, level, papers)

def display_outline(outline: Outline) -> None:
    """Pretty print outline for user approval."""
    print(f"\nSuggested Title: {outline.title}\n")
    for section in outline.sections:
        print(f"{'  ' * (section.level-1)}├─ {section.title}")
        for sub in section.subsections:
            print(f"{'  ' * (sub.level)}├─ {sub.title}")
            if sub.source_hooks:
                for hook in sub.source_hooks:
                    print(f"{'  ' * (sub.level+1)}└─ Source: {hook.paper_title[:60]}...")
    print("\n")
