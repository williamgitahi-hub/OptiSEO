from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import httpx
import base64

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


def get_auth_header():
    login = os.getenv("DATAFORSEO_LOGIN")
    password = os.getenv("DATAFORSEO_PASSWORD")
    credentials = base64.b64encode(f"{login}:{password}".encode()).decode()
    return {"Authorization": f"Basic {credentials}", "Content-Type": "application/json"}


@app.post("/optimize")
async def optimize(req: Request):
    keyword = req.keyword.lower()

    try:
        # Call DataForSEO Keywords Data API
        payload = [
            {
                "keywords": [keyword],
                "language_name": "English",
                "location_code": 2840  # United States
            }
        ]

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.dataforseo.com/v3/keywords_data/google_ads/search_volume/live",
                headers=get_auth_header(),
                json=payload,
                timeout=30.0
            )

        api_data = response.json()

        # Extract results
        result = api_data["tasks"][0]["result"]

        if result and len(result) > 0:
            item = result[0]
            search_volume = item.get("search_volume", 0) or 0
            competition = item.get("competition", 0) or 0
            competition_index = item.get("competition_index", 0) or 0
            cpc = item.get("cpc", 0) or 0

            # Calculate SEO score based on real data
            volume_score = min(search_volume / 1000, 40)
            competition_score = (1 - competition) * 40
            cpc_score = min(cpc * 2, 20)
            seo_score = int(volume_score + competition_score + cpc_score)
            seo_score = max(10, min(seo_score, 100))

            # Difficulty based on competition index
            if competition_index < 33:
                difficulty = "Easy"
            elif competition_index < 66:
                difficulty = "Medium"
            else:
                difficulty = "Hard"

            # Generate smart suggestions from keyword
            suggestions = [
                f"best {keyword} guide",
                f"{keyword} tips for beginners",
                f"how to improve {keyword}",
                f"{keyword} step by step strategy",
                f"advanced {keyword} techniques"
            ]

            return {
                "keyword": keyword,
                "seo_score": seo_score,
                "search_volume": search_volume,
                "competition": round(competition, 2),
                "competition_index": competition_index,
                "cpc": round(cpc, 2),
                "suggestions": suggestions,
                "difficulty": difficulty
            }

    except Exception as e:
        print(f"DataForSEO error: {e}")

    # Fallback if API fails
    return {
        "keyword": keyword,
        "seo_score": 50,
        "search_volume": 0,
        "competition": 0,
        "competition_index": 0,
        "cpc": 0,
        "suggestions": [
            f"best {keyword} guide",
            f"{keyword} tips for beginners",
            f"how to improve {keyword}",
            f"{keyword} step by step strategy",
            f"advanced {keyword} techniques"
        ],
        "difficulty": "Medium"
    }