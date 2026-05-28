import os
import json
import re
import time
from openai import OpenAI
from dotenv import load_dotenv
from src.models.schemas import SearchQueries

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

# List of free models to try in order
FREE_MODELS = [
    "openai/gpt-oss-20b:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "z-ai/glm-4.5-air:free"
]

PLANNER_PROMPT = """You are a search query planner for academic research. Given a student's research prompt, generate 3-5 specific search queries suitable for academic databases like Crossref.

Rules:
- Each query should be 3-8 words
- Cover different angles (broader, specific, review, recent)
- No quotation marks unless necessary
- Return ONLY a JSON object: {{"queries": ["query1", "query2", ...]}}

Student prompt: {prompt}
Education level: {level}"""

def fallback_planner(prompt: str) -> SearchQueries:
    """Simple keyword-based fallback when LLM is rate-limited."""
    # Extract key terms
    words = prompt.lower().split()
    # Remove common stopwords
    stopwords = {'the', 'a', 'an', 'and', 'of', 'to', 'in', 'for', 'on', 'with', 'by', 'at', 'from', 'is', 'are', 'was', 'were', 'be', 'been', 'being'}
    keywords = [w for w in words if w not in stopwords and len(w) > 2]
    # Take first 3-5 keywords as base
    if len(keywords) > 4:
        base = keywords[:4]
    else:
        base = keywords
    
    queries = []
    # Query 1: original phrase
    queries.append(prompt[:60])
    # Query 2: base keywords joined
    queries.append(' '.join(base))
    # Query 3: base + 'review'
    queries.append(' '.join(base) + ' review')
    # Query 4: base + 'recent' if not too long
    if len(' '.join(base)) < 40:
        queries.append(' '.join(base) + ' recent study')
    
    # Remove duplicates and limit to 4
    queries = list(dict.fromkeys(queries))[:4]
    return SearchQueries(queries=queries)

def plan_queries(prompt: str, level: str = "undergraduate") -> SearchQueries:
    """Generate search queries using LLM with fallback to keyword extraction."""
    formatted_prompt = PLANNER_PROMPT.format(prompt=prompt, level=level)
    
    for model_index, model in enumerate(FREE_MODELS):
        for attempt in range(3):  # 3 attempts per model
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are an academic assistant. Return only valid JSON."},
                        {"role": "user", "content": formatted_prompt}
                    ],
                    temperature=0.3,
                    max_tokens=500,
                )
                
                content = response.choices[0].message.content.strip()
                # Extract JSON
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    content = json_match.group(0)
                data = json.loads(content)
                return SearchQueries(queries=data["queries"])
                
            except Exception as e:
                print(f"   Plan attempt {attempt+1} with {model} failed: {str(e)[:100]}")
                if attempt < 2:
                    time.sleep(2 ** attempt)  # exponential backoff
                continue
        print(f"   Model {model} exhausted, trying next...")
    
    print("   All LLM models rate-limited. Using fallback keyword planner.")
    return fallback_planner(prompt)
