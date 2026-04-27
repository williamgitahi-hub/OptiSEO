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


async def fetch_serpapi_data(keyword: str):
    api_key = os.getenv("SERPAPI_KEY")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://serpapi.com/search",
            params={
                "engine": "google",
                "q": keyword,
                "api_key": api_key,
                "num": 10,
                "gl": "us",
                "hl": "en"
            },
            timeout=30.0
        )

    print("SerpAPI status:", response.status_code)
    data = response.json()
    print("SerpAPI response keys:", list(data.keys()))
    return data


def calculate_seo_metrics(keyword: str, data: dict):
    organic_results = data.get("organic_results", [])
    related_searches = data.get("related_searches", [])
    search_info = data.get("search_information", {})

    total_results_str = search_info.get("total_results", "0")
    try:
        total_results = int(str(total_results_str).replace(",", ""))
    except:
        total_results = 0

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

    # Extract real suggestions from related searches
    suggestions = []
    for item in related_searches[:5]:
        query = item.get("query", "")
        if query and query.lower() != keyword.lower():
            suggestions.append(query)

    # Extract from organic results if not enough
    if len(suggestions) < 5:
        for item in organic_results[:8]:
            title = item.get("title", "")
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
        data = await fetch_serpapi_data(keyword)

        if "error" in data:
            error_msg = data.get("error", "Unknown SerpAPI error")
            print(f"SerpAPI error: {error_msg}")
            raise ValueError(error_msg)

        metrics = calculate_seo_metrics(keyword, data)

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