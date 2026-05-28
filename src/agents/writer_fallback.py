"""Fallback writer that uses source abstracts directly, no LLM calls."""
from typing import List
from src.models.schemas import VerifiedPaper
from src.agents.outline_architect import Outline, OutlineSubsection, SourceHook

def build_citation(paper: VerifiedPaper) -> str:
    """Create a simple citation from a paper."""
    authors = paper.authors[:2] if paper.authors else ["Unknown"]
    if len(authors) == 1:
        author_str = authors[0]
    else:
        author_str = f"{authors[0]} et al."
    return f"{author_str}, {paper.year}"

def write_subsection_fallback(
    subsection: OutlineSubsection,
    section_title: str,
    papers: List[VerifiedPaper]
) -> str:
    """Generate subsection content by concatenating source abstracts."""
    content = f"\n\n### {subsection.title}\n\n"
    
    if not subsection.source_hooks:
        content += "*No specific sources provided for this section.*\n\n"
        return content
    
    for hook in subsection.source_hooks:
        # Find matching paper
        matched = None
        for p in papers:
            if p.title == hook.paper_title or hook.paper_title in p.title or p.title in hook.paper_title:
                matched = p
                break
        if matched:
            citation = build_citation(matched)
            abstract = matched.abstract if matched.abstract else "Abstract not available."
            content += f"**{citation}** – {abstract}\n\n"
        else:
            content += f"*Source: {hook.paper_title} – {hook.reason}*\n\n"
    
    return content

def generate_document_fallback(outline: Outline, papers: List[VerifiedPaper]) -> str:
    """Generate full document using fallback writer."""
    doc = f"# {outline.title}\n\n"
    doc += "---\n\n"
    for section in outline.sections:
        doc += f"## {section.title}\n\n"
        for subsection in section.subsections:
            doc += write_subsection_fallback(subsection, section.title, papers)
    return doc
