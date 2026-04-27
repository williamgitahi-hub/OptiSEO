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


async def get_access_token():
    client_id = os.getenv("GOOGLE_ADS_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_ADS_CLIENT_SECRET")
    refresh_token = os.getenv("GOOGLE_ADS_REFRESH_TOKEN")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token"
            }
        )
    token_data = response.json()
    print("Token response status:", token_data.get("token_type"))
    return token_data.get("access_token")


@app.post("/optimize")
async def optimize(req: Request):
    keyword = req.keyword.lower()

    try:
        access_token = await get_access_token()
        if not access_token:
            raise ValueError("Failed to get access token")

        customer_id = os.getenv("GOOGLE_ADS_CUSTOMER_ID")
        developer_token = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "developer-token": developer_token,
            "login-customer-id": customer_id,
            "Content-Type": "application/json"
        }

        # Correct payload format using keywordSeed
        payload = {
            "keywordSeed": {
                "keywords": [keyword]
            },
            "pageSize": 10,
            "keywordPlanNetwork": "GOOGLE_SEARCH",
            "language": "languageConstants/1000",
            "geoTargetConstants": ["geoTargetConstants/2840"],
            "historicalMetricsOptions": {
                "includeAverageCpc": True
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://googleads.googleapis.com/v17/customers/{customer_id}:generateKeywordIdeas",
                headers=headers,
                json=payload,
                timeout=30.0
            )

        print("Status code:", response.status_code)
        print("Raw response:", response.text[:1000])

        if not response.text.strip():
            raise ValueError(f"Empty response. Status: {response.status_code}")

        api_data = response.json()

        results = api_data.get("results", [])

        if results and len(results) > 0:
            item = results[0]
            metrics = item.get("keywordIdeaMetrics", {})

            search_volume = metrics.get("avgMonthlySearches", 0) or 0
            competition = metrics.get("competition", "UNKNOWN")
            competition_index = metrics.get("competitionIndex", 0) or 0
            cpc_micros = metrics.get("averageCpcMicros", 0) or 0
            cpc = round(cpc_micros / 1_000_000, 2)

            difficulty_map = {
                "LOW": "Easy",
                "MEDIUM": "Medium",
                "HIGH": "Hard",
                "UNKNOWN": "Medium"
            }
            difficulty = difficulty_map.get(competition, "Medium")

            volume_score = min(int(search_volume) / 1000, 40)
            competition_score = (1 - competition_index / 100) * 40
            cpc_score = min(cpc * 2, 20)
            seo_score = int(volume_score + competition_score + cpc_score)
            seo_score = max(10, min(seo_score, 100))

            suggestions = []
            for r in results[:6]:
                text = r.get("text", "")
                if text and text.lower() != keyword:
                    suggestions.append(text)

            if len(suggestions) < 5:
                suggestions += [
                    f"best {keyword} guide",
                    f"{keyword} tips for beginners",
                    f"how to improve {keyword}",
                    f"{keyword} step by step strategy",
                    f"advanced {keyword} techniques"
                ]
            suggestions = suggestions[:5]

            return {
                "keyword": keyword,
                "seo_score": seo_score,
                "search_volume": int(search_volume),
                "competition": competition,
                "competition_index": competition_index,
                "cpc": cpc,
                "suggestions": suggestions,
                "difficulty": difficulty
            }

        else:
            print("No results. Full API response:", api_data)
            raise ValueError("No results from Google Ads API")

    except Exception as e:
        print(f"Google Ads API error: {e}")

    # Fallback
    return {
        "keyword": keyword,
        "seo_score": 50,
        "search_volume": 0,
        "competition": "UNKNOWN",
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