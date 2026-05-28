import re
from typing import List
from src.models.schemas import VerifiedPaper
from src.agents.outline_architect import Outline, OutlineSubsection, SourceHook

def extract_key_sentences(abstract: str, max_sentences: int = 2) -> str:
    """Extract first few sentences from abstract, or return empty if not available."""
    if not abstract or abstract == "No abstract available." or abstract.startswith("Abstract not available"):
        return ""
    sentences = re.split(r'(?<=\.)\s+', abstract)
    key = '. '.join(sentences[:max_sentences]).strip()
    if key and not key.endswith('.'):
        key += '.'
    return key

def format_citation(paper: VerifiedPaper) -> str:
    """Format citation: Author (Year)"""
    if paper.authors and paper.authors[0]:
        author = paper.authors[0].split()[-1]  # last name
    else:
        author = "Author"
    return f"{author} ({paper.year})"

def write_subsection_smart(
    subsection: OutlineSubsection,
    section_title: str,
    papers: List[VerifiedPaper]
) -> str:
    """Generate content using source abstracts with fallback to title/reason."""
    if not subsection.source_hooks:
        return f"\n\n### {subsection.title}\n\n*No sources available for this section.*\n\n"
    
    sentences = []
    # Topic sentence based on subsection title
    topic = f"This section examines {subsection.title.lower()}."
    sentences.append(topic)
    
    for hook in subsection.source_hooks:
        matched = None
        for p in papers:
            if p.title == hook.paper_title or hook.paper_title in p.title or p.title in hook.paper_title:
                matched = p
                break
        if matched:
            citation = format_citation(matched)
            key_sent = extract_key_sentences(matched.abstract, max_sentences=1)
            if key_sent:
                sentences.append(f"According to {citation}, {key_sent[0].lower() + key_sent[1:] if key_sent else ''}")
            else:
                # No abstract: use title to generate a sentence
                title_short = matched.title[:80]
                sentences.append(f"{citation} studied \"{title_short}\", which is directly relevant to {hook.reason.lower()}.")
        else:
            # No matching paper: use hook info
            sentences.append(f"A relevant source indicates that {hook.reason.lower()}.")
    
    paragraph = ' '.join(sentences)
    # Add line breaks for readability
    paragraph = paragraph.replace('. ', '.\n\n')
    return f"\n\n### {subsection.title}\n\n{paragraph}\n\n"

def generate_document_smart(
    outline: Outline,
    papers: List[VerifiedPaper]
) -> str:
    """Generate full document using smart fallback (no LLM)."""
    doc = f"# {outline.title}\n\n---\n\n"
    for section in outline.sections:
        doc += f"## {section.title}\n\n"
        for subsection in section.subsections:
            doc += write_subsection_smart(subsection, section.title, papers)
    return doc
