import re
import html
from typing import List
from src.models.schemas import VerifiedPaper
from src.agents.outline_architect import Outline, OutlineSubsection, SourceHook

def clean_abstract(text: str) -> str:
    """Remove XML/HTML tags and decode HTML entities."""
    if not text or text == "No abstract available.":
        return ""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_key_sentences(abstract: str, max_sentences: int = 2) -> str:
    """Extract first few sentences from cleaned abstract, return empty if none."""
    cleaned = clean_abstract(abstract)
    if not cleaned:
        return ""
    sentences = re.split(r'(?<=\.)\s+', cleaned)
    key = '. '.join(sentences[:max_sentences]).strip()
    if key and not key.endswith('.'):
        key += '.'
    return key

def format_citation(paper: VerifiedPaper) -> str:
    """Format citation: Author (Year)"""
    if paper.authors and paper.authors[0]:
        author = paper.authors[0].split()[-1]
    else:
        author = "Author"
    return f"{author} ({paper.year})"

def write_subsection_smart(
    subsection: OutlineSubsection,
    section_title: str,
    papers: List[VerifiedPaper]
) -> str:
    """Generate content using available abstract or fallback to title."""
    if not subsection.source_hooks:
        return f"\n\n### {subsection.title}\n\n*No sources available for this section.*\n\n"
    
    sentences = []
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
                # No abstract: use title to generate a meaningful sentence
                title_short = matched.title[:100]
                sentences.append(f"{citation} discussed the topic in \"{title_short}\", providing relevant insights for this subsection.")
        else:
            # No matching paper found in the papers list
            sentences.append(f"A relevant source indicates that {hook.reason.lower()}.")
    
    paragraph = ' '.join(sentences)
    paragraph = paragraph.replace('. ', '.\n\n')
    return f"\n\n### {subsection.title}\n\n{paragraph}\n\n"

def generate_document_smart(
    outline: Outline,
    papers: List[VerifiedPaper]
) -> str:
    doc = f"# {outline.title}\n\n---\n\n"
    for section in outline.sections:
        doc += f"## {section.title}\n\n"
        for subsection in section.subsections:
            doc += write_subsection_smart(subsection, section.title, papers)
    return doc
