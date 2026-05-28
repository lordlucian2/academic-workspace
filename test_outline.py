#!/usr/bin/env python
import json
from src.agents.outline_architect import generate_outline, display_outline
from src.models.schemas import VerifiedPaper

# Load previous result
with open("result.json", "r") as f:
    data = json.load(f)

# Convert to VerifiedPaper objects
papers = []
for vp_data in data.get("verified_papers", []):
    papers.append(VerifiedPaper(
        title=vp_data["title"],
        authors=vp_data.get("authors", []),
        year=vp_data.get("year", 0),
        doi=vp_data.get("doi"),
        url=vp_data.get("url", ""),
        citation_count=vp_data.get("citation_count", 0),
        venue=vp_data.get("venue", "Unknown"),
        abstract=vp_data.get("abstract_preview", ""),
        keep=True,
        reason=vp_data.get("reason", "")
    ))

print(f"Loaded {len(papers)} verified papers")
outline = generate_outline(
    prompt=data["prompt"],
    assignment_type="research paper",
    level=data["level"],
    papers=papers
)

display_outline(outline)

# Save outline to file for later
with open("outline.json", "w") as f:
    json.dump(outline.dict(), f, indent=2)
print("Outline saved to outline.json")
