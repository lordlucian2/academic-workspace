import sys
sys.path.insert(0, '.')

from src.api.semantic_scholar import search_papers

def test_search_papers():
    query = "microplastics marine sediment"
    papers = search_papers(query, limit=3)
    assert len(papers) >= 1, "Should return at least one paper"
    for paper in papers:
        assert paper.title, "Title should not be empty"
        assert paper.doi or paper.url, "Should have DOI or URL"
        print(f"✓ {paper.title[:60]}... ({paper.year})")
    print(f"Test passed: {len(papers)} papers returned")

if __name__ == "__main__":
    test_search_papers()
