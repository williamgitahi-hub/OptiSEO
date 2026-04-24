from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import random

app = FastAPI()

# Allow frontend (React) to talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Request structure
class KeywordRequest(BaseModel):
    keyword: str

# Generate keyword ideas
def generate_keywords(base):
    return [
        f"best {base}",
        f"{base} in kenya",
        f"cheap {base}",
        f"{base} for beginners",
        f"how to start {base}"
    ]

# Score keywords
def score_keyword(keyword):
    search_volume = random.randint(100, 10000)
    competition = random.uniform(0.1, 1.0)
    score = search_volume / (competition + 1)

    return {
        "keyword": keyword,
        "search_volume": search_volume,
        "competition": round(competition, 2),
        "score": round(score, 2)
    }

# Test route
@app.get("/")
def home():
    return {"message": "API is running"}

# Main optimization endpoint
@app.post("/optimize")
def optimize(data: KeywordRequest):
    keywords = generate_keywords(data.keyword)
    results = [score_keyword(k) for k in keywords]
    return {"results": results}