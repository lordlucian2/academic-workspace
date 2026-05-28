# This file is now a wrapper around Crossref for compatibility
from src.api.crossref import search_papers, search_multiple_queries

# Re-export the functions
__all__ = ["search_papers", "search_multiple_queries"]
