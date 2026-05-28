import os
import re
import time
import random
from typing import List
from openai import OpenAI
from dotenv import load_dotenv
from src.models.schemas import VerifiedPaper
from src.agents.outline_architect import Outline, OutlineSubsection, SourceHook

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

# Use a fast, cheap paid model
PAID_MODEL = "openai/gpt-4o-mini"  # or "anthropic/claude-3-haiku", "meta-llama/llama-3.1-8b-instruct"

WRITER_PROMPT = """You are an academic writer. Write a single subsection of an academic document based on the given outline and supporting sources.

Assignment type: {assignment_type}
Education level: {level}
Section title: {section_title}
Subsection title: {subsection_title}

Supporting sources (each with title, year, authors, and abstract summary):
{sources_text}

Write 150-300 words for this subsection. Follow these rules:
- Write in an academic tone appropriate for {level} level.
- Synthesize information from the sources – do not copy abstracts verbatim.
- Cite sources inline using [Author, Year] format. Use the first author's last name.
- If multiple sources support a claim, cite them together like [Smith, 2020; Jones, 2021].
- Do not invent facts not supported by the sources.
- Keep paragraphs clear and focused on the subsection topic.

Return ONLY the plain text content, no extra commentary."""

def build_sources_text_for_hooks(papers: List[VerifiedPaper], hooks: List[SourceHook]) -> str:
    """Build text for sources referenced in source_hooks."""
    source_text = ""
    used_papers = []
    for hook in hooks:
        matched = None
        # Try exact match first
        for p in papers:
            if p.title == hook.paper_title:
                matched = p
                break
        if not matched:
            for p in papers:
                if hook.paper_title in p.title or p.title in hook.paper_title:
                    matched = p
                    break
        if matched and matched not in used_papers:
            used_papers.append(matched)
            authors = matched.authors[0] if matched.authors else "Unknown"
            abstract = matched.abstract[:400] if matched.abstract else "No abstract available."
            source_text += f"Title: {matched.title} ({matched.year})\nAuthor: {authors}\nAbstract: {abstract}\n\n"
        elif not matched:
            source_text += f"Title: {hook.paper_title}\nReason: {hook.reason}\n(Full source details not available)\n\n"
    return source_text

def write_subsection_llm(
    subsection: OutlineSubsection,
    section_title: str,
    assignment_type: str,
    level: str,
    papers: List[VerifiedPaper]
) -> str:
    """Generate content for a single subsection using LLM."""
    sources_text = build_sources_text_for_hooks(papers, subsection.source_hooks)
    
    if not sources_text.strip():
        return f"\n\n### {subsection.title}\n\n*No specific sources provided for this section.*\n\n"
    
    formatted_prompt = WRITER_PROMPT.format(
        assignment_type=assignment_type,
        level=level,
        section_title=section_title,
        subsection_title=subsection.title,
        sources_text=sources_text
    )
    
    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                model=PAID_MODEL,
                messages=[
                    {"role": "system", "content": "You are an academic writer. Write clearly and cite sources."},
                    {"role": "user", "content": formatted_prompt}
                ],
                temperature=0.5,
                max_tokens=800,
            )
            content = response.choices[0].message.content.strip()
            # Add small delay to avoid rate limits on free tier (if using free)
            time.sleep(0.5 + random.uniform(0, 0.5))
            return f"\n\n### {subsection.title}\n\n{content}\n\n"
        except Exception as e:
            print(f"   Writer LLM error: {str(e)[:100]}, attempt {attempt+1}")
            time.sleep(2 ** attempt)
            continue
    # Fallback to abstract concatenator
    return write_subsection_fallback(subsection, section_title, papers)

def write_subsection_fallback(subsection: OutlineSubsection, section_title: str, papers: List[VerifiedPaper]) -> str:
    """Fallback: use source abstracts when LLM fails."""
    content = f"\n\n### {subsection.title}\n\n"
    for hook in subsection.source_hooks:
        matched = None
        for p in papers:
            if p.title == hook.paper_title or hook.paper_title in p.title:
                matched = p
                break
        if matched:
            authors = matched.authors[0] if matched.authors else "Unknown"
            abstract = matched.abstract if matched.abstract else "No abstract."
            content += f"**{authors}, {matched.year}** – {abstract}\n\n"
        else:
            content += f"*Source: {hook.paper_title}*\n\n"
    return content

def generate_document(
    outline: Outline,
    assignment_type: str,
    level: str,
    papers: List[VerifiedPaper]
) -> str:
    """Generate full Markdown document using LLM writer."""
    doc = f"# {outline.title}\n\n"
    doc += f"**Assignment Type:** {assignment_type}\n"
    doc += f"**Level:** {level}\n\n"
    doc += "---\n\n"
    
    for section in outline.sections:
        doc += f"## {section.title}\n\n"
        for subsection in section.subsections:
            content = write_subsection_llm(subsection, section.title, assignment_type, level, papers)
            doc += content
    return doc
