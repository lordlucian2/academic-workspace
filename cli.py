#!/usr/bin/env python
"""
CLI for Academic Workspace Sprint 1
Usage: python cli.py "research prompt" [--level undergraduate]
"""

import sys
import json
import argparse
from datetime import datetime
from src.agents.query_planner import plan_queries
from src.api.semantic_scholar import search_multiple_queries
from src.agents.source_verifier import verify_sources

def run_pipeline(prompt: str, level: str = "undergraduate"):
    print(f"\n{'='*60}")
    print(f"PROMPT: {prompt}")
    print(f"LEVEL: {level}")
    print(f"{'='*60}\n")
    
    # Step 1: Generate search queries
    print("1. Planning search queries...")
    queries = plan_queries(prompt, level)
    print(f"   Queries: {queries.queries}")
    
    # Step 2: Fetch papers from Crossref via Semantic Scholar wrapper
    print("\n2. Fetching papers from academic databases...")
    papers = search_multiple_queries(queries.queries, limit_per_query=3)
    print(f"   Fetched {len(papers)} unique papers")
    
    if not papers:
        print("   WARNING: No papers found. Exiting.")
        return None
    
    # Step 3: Verify sources
    print("\n3. Verifying sources (relevance, recency, credibility)...")
    result = verify_sources(prompt, papers, level)
    print(f"   Kept {len(result.verified_papers)} papers")
    
    # Output summary
    print("\n" + "-"*60)
    print("VERIFIED PAPERS:")
    for i, vp in enumerate(result.verified_papers, 1):
        print(f"{i}. {vp.title} ({vp.year})")
        print(f"   Reason: {vp.reason}")
        print(f"   URL: {vp.url}\n")
    
    return {
        "prompt": prompt,
        "level": level,
        "timestamp": datetime.now().isoformat(),
        "search_queries": queries.queries,
        "total_papers_fetched": len(papers),
        "verified_papers": [
            {
                "title": vp.title,
                "authors": vp.authors,
                "year": vp.year,
                "doi": vp.doi,
                "url": vp.url,
                "citation_count": vp.citation_count,
                "venue": vp.venue,
                "abstract_preview": vp.abstract[:200] if vp.abstract else "",
                "reason": vp.reason
            }
            for vp in result.verified_papers
        ]
    }

def main():
    parser = argparse.ArgumentParser(description="Academic Workspace Source Retrieval Pipeline")
    parser.add_argument("prompt", type=str, help="Research prompt or question")
    parser.add_argument("--level", type=str, default="undergraduate", 
                        choices=["highschool", "undergraduate", "graduate"],
                        help="Education level")
    parser.add_argument("--output", type=str, help="Output JSON file (optional)")
    args = parser.parse_args()
    
    result = run_pipeline(args.prompt, args.level)
    
    if result and args.output:
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"Results saved to {args.output}")
    
    if not result:
        sys.exit(1)

if __name__ == "__main__":
    main()
