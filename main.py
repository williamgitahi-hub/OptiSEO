from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import httpx

app = FastAPI()

origins = os.getenv("ALLOWED_ORIGINS", "").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Request(BaseModel):
    keyword: str


async def fetch_search_data(keyword: str):
    api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
    cx = os.getenv("GOOGLE_SEARCH_CX")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://www.googleapis.com/customsearch/v1",
            params={
                "key": api_key,
                "cx": cx,
                "q": keyword,
                "num": 10
            },
            timeout=30.0
        )

    print("Search API status:", response.status_code)
    data = response.json()
    print("Search API response keys:", list(data.keys()))
    return data


def calculate_seo_metrics(keyword: str, search_data: dict):
    items = search_data.get("items", [])
    search_info = search_data.get("searchInformation", {})

    total_results = int(search_info.get("totalResults", 0))
    result_count = len(items)

    # Calculate competition based on total results
    if total_results > 100_000_000:
        competition = "HIGH"
        competition_index = 85
        difficulty = "Hard"
    elif total_results > 10_000_000:
        competition = "MEDIUM"
        competition_index = 55
        difficulty = "Medium"
    else:
        competition = "LOW"
        competition_index = 25
        difficulty = "Easy"

    # Calculate SEO score
    volume_score = min(total_results / 10_000_000, 40)
    competition_score = (1 - competition_index / 100) * 40
    keyword_length_score = min(len(keyword.split()) * 5, 20)
    seo_score = int(volume_score + competition_score + keyword_length_score)
    seo_score = max(10, min(seo_score, 100))

    # Extract real suggestions from search results
    suggestions = []
    for item in items[:8]:
        title = item.get("title", "")
        snippet = item.get("snippet", "")

        # Extract meaningful phrases from titles
        if title and keyword.lower() in title.lower():
            cleaned = title.split("|")[0].split("-")[0].strip()
            if cleaned and cleaned.lower() != keyword.lower() and len(cleaned) > len(keyword):
                suggestions.append(cleaned)

    # Fill remaining with generated suggestions
    if len(suggestions) < 5:
        suggestions += [
            f"best {keyword} guide",
            f"{keyword} tips for beginners",
            f"how to improve {keyword}",
            f"{keyword} step by step strategy",
            f"advanced {keyword} techniques"
        ]

    # Deduplicate and limit
    seen = set()
    unique_suggestions = []
    for s in suggestions:
        if s.lower() not in seen:
            seen.add(s.lower())
            unique_suggestions.append(s)

    return {
        "competition": competition,
        "competition_index": competition_index,
        "difficulty": difficulty,
        "seo_score": seo_score,
        "total_results": total_results,
        "suggestions": unique_suggestions[:5]
    }


@app.post("/optimize")
async def optimize(req: Request):
    keyword = req.keyword.lower()

    try:
        search_data = await fetch_search_data(keyword)

        if "error" in search_data:
            error_msg = search_data["error"].get("message", "Unknown error")
            print(f"Search API error: {error_msg}")
            raise ValueError(error_msg)

        metrics = calculate_seo_metrics(keyword, search_data)

        return {
            "keyword": keyword,
            "seo_score": metrics["seo_score"],
            "search_volume": metrics["total_results"],
            "competition": metrics["competition"],
            "competition_index": metrics["competition_index"],
            "cpc": 0.0,
            "suggestions": metrics["suggestions"],
            "difficulty": metrics["difficulty"]
        }

    except Exception as e:
        print(f"Optimize error: {e}")

    # Fallback
    return {
        "keyword": keyword,
        "seo_score": 50,
        "search_volume": 0,
        "competition": "UNKNOWN",
        "competition_index": 0,
        "cpc": 0.0,
        "suggestions": [
            f"best {keyword} guide",
            f"{keyword} tips for beginners",
            f"how to improve {keyword}",
            f"{keyword} step by step strategy",
            f"advanced {keyword} techniques"
        ],
        "difficulty": "Medium"
    }