import re
import html
from typing import List
from src.models.schemas import VerifiedPaper
from src.agents.outline_architect import Outline, OutlineSubsection, SourceHook

def clean_abstract(text: str) -> str:
    if not text or text == "No abstract available.":
        return ""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def format_citation(paper: VerifiedPaper) -> str:
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
        
        citation = "A relevant study"
        title_part = ""
        
        if matched:
            citation = format_citation(matched)
            title_part = f" \"{matched.title[:80]}\""
        else:
            title_part = f" on \"{hook.paper_title[:80]}\""
        
        # Always produce a sentence, regardless of abstract availability
        sentences.append(f"{citation} examined{title_part}, providing insights into {hook.reason.lower()}.")
    
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
