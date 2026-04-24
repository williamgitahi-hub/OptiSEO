from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import random

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://optiqo-frontend.netlify.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Request(BaseModel):
    keyword: str


@app.post("/optimize")
def optimize(req: Request):
    keyword = req.keyword.lower()

    score = random.randint(40, 95)

    suggestions = [
        f"best {keyword} guide",
        f"{keyword} tips for beginners",
        f"how to improve {keyword}",
        f"{keyword} step by step strategy",
        f"advanced {keyword} techniques"
    ]

    return {
        "keyword": keyword,
        "seo_score": score,
        "suggestions": suggestions,
        "difficulty": "Easy" if score > 70 else "Medium" if score > 50 else "Hard"
    }