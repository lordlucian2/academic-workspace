import os
import re
import time
import random
from typing import List, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv
from src.models.schemas import VerifiedPaper
from src.agents.outline_architect import Outline, OutlineSection, OutlineSubsection, SourceHook

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

FREE_MODELS = [
    "openai/gpt-oss-20b:free",
    "meta-llama/llama-3.3-70b-instruct:free",
]

WRITER_PROMPT = """You are an academic writer. Write a single section of an academic document based on the given outline, assignment type, and supporting sources.

Assignment type: {assignment_type}
Education level: {level}
Section title: {section_title}
Subsection title: {subsection_title} (if provided)

Supporting sources (with abstracts):
{sources_text}

Write 150-300 words for this subsection. Follow these rules:
- Write in an academic tone appropriate for {level} level.
- Cite sources inline using [Author, Year] – use the author name from the source.
- If a source has no clear author, use [Year] only.
- Do not invent facts not supported by the sources.
- Keep paragraphs clear and focused on the subsection topic.

Return ONLY the plain text content, no extra commentary.
"""

def build_sources_text_for_hooks(papers: List[VerifiedPaper], hooks: List[SourceHook]) -> str:
    """Build text for sources referenced in source_hooks, using best match."""
    source_text = ""
    used_papers = []
    for hook in hooks:
        matched = None
        # Try exact match first
        for p in papers:
            if p.title == hook.paper_title:
                matched = p
                break
        # Try partial match if exact fails
        if not matched:
            for p in papers:
                if hook.paper_title in p.title or p.title in hook.paper_title:
                    matched = p
                    break
        if matched and matched not in used_papers:
            used_papers.append(matched)
            abstract = matched.abstract[:400] if matched.abstract else "No abstract available."
            authors = ', '.join(matched.authors[:2]) if matched.authors else "Unknown"
            source_text += f"Title: {matched.title} ({matched.year})\nAuthors: {authors}\nAbstract: {abstract}\n\n"
        elif not matched:
            # Fallback: use hook info only
            source_text += f"Title: {hook.paper_title}\nReason: {hook.reason}\n(Full source details not available)\n\n"
    return source_text

def write_subsection(
    subsection: OutlineSubsection,
    section_title: str,
    assignment_type: str,
    level: str,
    papers: List[VerifiedPaper]
) -> str:
    """Generate content for a single subsection using LLM with delay and retry."""
    sources_text = build_sources_text_for_hooks(papers, subsection.source_hooks)
    
    if not sources_text.strip():
        # Fallback: no sources attached – write generic
        return f"\n\n### {subsection.title}\n\n[Content to be written. No specific sources provided for this subsection.]\n\n"
    
    formatted_prompt = WRITER_PROMPT.format(
        assignment_type=assignment_type,
        level=level,
        section_title=section_title,
        subsection_title=subsection.title,
        sources_text=sources_text
    )
    
    for model in FREE_MODELS:
        for attempt in range(2):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are an academic writer. Write the requested subsection."},
                        {"role": "user", "content": formatted_prompt}
                    ],
                    temperature=0.5,
                    max_tokens=800,
                )
                content = response.choices[0].message.content.strip()
                # Add delay after successful call to prevent rate limiting
                time.sleep(1.5 + random.uniform(0, 0.5))
                return f"\n\n### {subsection.title}\n\n{content}\n\n"
            except Exception as e:
                wait = (2 ** attempt) + random.uniform(0, 1)
                print(f"   Writer error for {subsection.title}: {str(e)[:100]}. Retrying in {wait:.1f}s...")
                time.sleep(wait)
                continue
        print(f"   Writer model {model} exhausted, trying next...")
    
    # Ultimate fallback
    return f"\n\n### {subsection.title}\n\n[Content generation failed. Please write this section manually based on sources.]\n\n"

def generate_document(
    outline: Outline,
    assignment_type: str,
    level: str,
    papers: List[VerifiedPaper]
) -> str:
    """Generate full Markdown document from outline."""
    document = f"# {outline.title}\n\n"
    document += f"**Assignment Type:** {assignment_type}\n"
    document += f"**Level:** {level}\n\n"
    document += "---\n\n"
    
    for section in outline.sections:
        document += f"## {section.title}\n\n"
        for subsection in section.subsections:
            content = write_subsection(subsection, section.title, assignment_type, level, papers)
            document += content
    return document
