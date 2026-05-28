from typing import List, Optional
from pydantic import BaseModel, Field

class SearchQueries(BaseModel):
    """Output from Query Planner agent"""
    queries: List[str] = Field(..., min_items=3, max_items=5)

class RawPaper(BaseModel):
    """Paper as returned from an academic API"""
    title: str
    authors: List[str]
    year: int
    doi: Optional[str] = None
    url: str
    citation_count: int
    venue: str
    abstract: str = ""  # Default to empty string if None

class VerifiedPaper(BaseModel):
    """Paper after verification"""
    title: str
    authors: List[str]
    year: int
    doi: Optional[str] = None
    url: str
    citation_count: int
    venue: str
    abstract: str = ""
    keep: bool
    reason: str

class VerificationResult(BaseModel):
    """Output from Source Verifier agent"""
    verified_papers: List[VerifiedPaper]

class ProcessedPrompt(BaseModel):
    """Full pipeline output for one prompt"""
    prompt: str
    search_queries: List[str]
    total_papers_fetched: int
    verified_papers: List[VerifiedPaper]
