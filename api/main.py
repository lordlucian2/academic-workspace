import sys
from pathlib import Path

# Add parent directory to path so imports work
sys.path.append(str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any

# Import your existing modules
from src.agents.query_planner import plan_queries
from src.api.semantic_scholar import search_multiple_queries
from src.agents.source_verifier import verify_sources
from src.agents.outline_architect import generate_outline, Outline
from src.agents.writer_fallback import generate_document_fallback
from src.models.schemas import VerifiedPaper

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class GenerateOutlineRequest(BaseModel):
    prompt: str
    level: str = "undergraduate"
    assignment_type: str = "research paper"

class GenerateDocumentRequest(BaseModel):
    outline: Dict[str, Any]
    sources: List[Dict[str, Any]]
    prompt: str = ""
    level: str = "undergraduate"
    assignment_type: str = "research paper"

@app.get("/")
def root():
    return {"status": "ok"}

@app.post("/generate-outline")
async def generate_outline_endpoint(req: GenerateOutlineRequest):
    try:
        # Step 1: generate search queries
        queries = plan_queries(req.prompt, req.level)
        # Step 2: fetch papers
        papers = search_multiple_queries(queries.queries, limit_per_query=3)
        # Step 3: verify sources
        verified = verify_sources(req.prompt, papers, req.level)
        # Step 4: generate outline
        outline = generate_outline(req.prompt, req.assignment_type, req.level, verified.verified_papers)
        return {
            "outline": outline.dict(),
            "sources": [p.dict() for p in verified.verified_papers]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-document")
async def generate_document_endpoint(req: GenerateDocumentRequest):
    try:
        # Convert sources to VerifiedPaper objects
        papers = [VerifiedPaper(**s) for s in req.sources]
        # Convert outline dict to Outline model
        outline = Outline(**req.outline)
        # Generate document using fallback writer (no LLM, fast)
        doc = generate_document_fallback(outline, papers)
        return {"document": doc}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
