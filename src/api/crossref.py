import requests
import time
from typing import List, Optional
from src.models.schemas import RawPaper

HEADERS = {
    "User-Agent": "AcademicWorkspace/1.0 (Educational Research Tool; mailto:your-email@example.com)"
}

def search_papers(query: str, limit: int = 5) -> List[RawPaper]:
    """
    Search Crossref for papers matching the query.
    No API key required. Rate limit is ~10 requests per second.
    """
    url = "https://api.crossref.org/works"
    params = {
        "query": query,
        "rows": limit,
        "sort": "relevance",
        "order": "desc"
    }
    
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Error fetching from Crossref: {e}")
        return []
    
    papers = []
    for item in data.get("message", {}).get("items", []):
        # Extract title (first one, fallback to "Untitled")
        title = item.get("title", [""])[0] if item.get("title") else "Untitled"
        
        # Extract authors
        authors = []
        for author in item.get("author", []):
            given = author.get("given", "")
            family = author.get("family", "")
            name = f"{given} {family}".strip()
            if name:
                authors.append(name)
            elif author.get("name"):
                authors.append(author["name"])
        if not authors:
            authors = ["Unknown"]
        
        # Extract year from published-print or created
        year = None
        pub_date = item.get("published-print") or item.get("published-online") or item.get("created")
        if pub_date and "date-parts" in pub_date:
            date_parts = pub_date["date-parts"]
            if date_parts and date_parts[0]:
                year = date_parts[0][0]
        if not year:
            year = 0
        
        # Get DOI
        doi = item.get("DOI")
        if doi:
            url = f"https://doi.org/{doi}"
        else:
            url = ""
        
        # Get citation count
        citations = item.get("is-referenced-by-count", 0)
        
        # Get venue (container-title)
        container_title = item.get("container-title", [])
        venue = container_title[0] if container_title else "Unknown"
        
        # Get abstract (may be HTML, we'll keep as is for now)
        abstract = item.get("abstract", "")
        if abstract is None:
            abstract = ""
        # Remove HTML tags if present (optional)
        # abstract = re.sub('<.*?>', '', abstract)
        
        paper = RawPaper(
            title=title,
            authors=authors,
            year=year,
            doi=doi,
            url=url,
            citation_count=citations,
            venue=venue,
            abstract=abstract
        )
        papers.append(paper)
    
    return papers

def search_multiple_queries(queries: List[str], limit_per_query: int = 5) -> List[RawPaper]:
    """
    Search multiple queries, combine and deduplicate by DOI.
    """
    all_papers = []
    seen_dois = set()
    
    for query in queries:
        papers = search_papers(query, limit_per_query)
        for paper in papers:
            if paper.doi and paper.doi in seen_dois:
                continue
            if paper.doi:
                seen_dois.add(paper.doi)
            else:
                # Fallback to title+year
                key = f"{paper.title}_{paper.year}"
                if key in seen_dois:
                    continue
                seen_dois.add(key)
            all_papers.append(paper)
        # Be respectful: wait 0.2 seconds between queries (5 requests per second)
        time.sleep(0.2)
    
    # Sort by citation count (highest first)
    all_papers.sort(key=lambda p: p.citation_count, reverse=True)
    return all_papers
