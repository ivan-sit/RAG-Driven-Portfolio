from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
import logging
from typing import List, Dict, Any
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import random

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="RAG-Driven Investment Portfolio API",
    description="API for retrieving AI-generated investment insights based on real-time news analysis",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock data for demonstration
MOCK_SUMMARIES = {
    "defense": {
        "summary": "The defense sector is experiencing significant growth due to increased global tensions and rising defense budgets. Key developments include major contract wins for Lockheed Martin and Raytheon, with focus on next-generation missile defense systems and AI-powered surveillance technology.",
        "key_points": [
            "Lockheed Martin secured $2.3B contract for missile defense",
            "Raytheon developing AI-powered radar systems",
            "Global defense spending expected to increase 8% in 2024",
            "New cybersecurity initiatives in defense sector"
        ],
        "timestamp": datetime.now().isoformat(),
        "sources": ["Reuters", "Defense News", "Bloomberg"]
    },
    "semiconductor": {
        "summary": "The semiconductor industry is witnessing a surge in demand driven by AI/ML applications, electric vehicles, and 5G infrastructure. TSMC and NVIDIA are leading the charge with advanced chip manufacturing and AI processors.",
        "key_points": [
            "NVIDIA reports 200% revenue growth in AI chips",
            "TSMC expanding 3nm manufacturing capacity",
            "Global chip shortage easing but demand remains high",
            "New investments in semiconductor manufacturing in US"
        ],
        "timestamp": datetime.now().isoformat(),
        "sources": ["CNBC", "TechCrunch", "Wall Street Journal"]
    }
}

MOCK_INVESTMENT_IDEAS = {
    "long_term_stocks": [
        {
            "ticker": "LMT",
            "name": "Lockheed Martin",
            "reasoning": "Strong defense contract pipeline and technological leadership in missile defense systems. Expected to benefit from increased defense spending globally.",
            "target_price": "$520",
            "risk_level": "Medium",
            "timeframe": "12-18 months"
        },
        {
            "ticker": "NVDA",
            "name": "NVIDIA Corporation",
            "reasoning": "Dominant position in AI chips with growing demand from data centers, gaming, and autonomous vehicles. Strong revenue growth and market leadership.",
            "target_price": "$850",
            "risk_level": "Medium-High",
            "timeframe": "12-24 months"
        },
        {
            "ticker": "TSMC",
            "name": "Taiwan Semiconductor",
            "reasoning": "Leading semiconductor manufacturer with advanced 3nm technology. Critical supplier for major tech companies with strong pricing power.",
            "target_price": "$180",
            "risk_level": "Medium",
            "timeframe": "18-24 months"
        }
    ],
    "short_term_options": [
        {
            "ticker": "RTX",
            "strategy": "Bull Call Spread",
            "reasoning": "Expected earnings beat due to strong defense segment performance and recent contract wins.",
            "strike_prices": "$95/$100",
            "expiration": "30 days",
            "risk_level": "High"
        },
        {
            "ticker": "AMD",
            "strategy": "Iron Condor",
            "reasoning": "Range-bound trading expected around earnings with implied volatility providing good premium collection opportunity.",
            "strike_prices": "$140/$145 and $155/$160",
            "expiration": "45 days",
            "risk_level": "Medium"
        }
    ],
    "timestamp": datetime.now().isoformat()
}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "RAG-Driven Investment Portfolio API",
        "version": "1.0.0",
        "status": "running",
        "environment": "development",
        "note": "Running in demo mode with mock data"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "mode": "demo"
    }

@app.get("/fetchSummaries")
async def fetch_summaries():
    """Get the latest industry summaries"""
    return {
        "summaries": MOCK_SUMMARIES,
        "timestamp": datetime.now().isoformat(),
        "count": len(MOCK_SUMMARIES)
    }

@app.get("/fetchInvestmentIdeas")
async def fetch_investment_ideas():
    """Get the latest investment ideas"""
    return MOCK_INVESTMENT_IDEAS

@app.get("/summaries/history")
async def get_summaries_history():
    """Get the history of summaries"""
    # Generate some mock history
    history = []
    for i in range(5):
        date = datetime.now() - timedelta(days=i*2)
        history.append({
            "date": date.isoformat(),
            "defense": {
                "summary": f"Defense sector update from {date.strftime('%Y-%m-%d')}",
                "key_points": ["Contract wins", "Technology advances", "Budget increases"]
            },
            "semiconductor": {
                "summary": f"Semiconductor industry update from {date.strftime('%Y-%m-%d')}",
                "key_points": ["Chip demand", "Manufacturing expansion", "AI growth"]
            }
        })
    
    return {
        "history": history,
        "count": len(history)
    }

@app.get("/investment-ideas/history")
async def get_investment_ideas_history():
    """Get the history of investment ideas"""
    # Generate some mock history
    history = []
    for i in range(3):
        date = datetime.now() - timedelta(days=i*7)
        history.append({
            "date": date.isoformat(),
            "long_term_stocks": [
                {"ticker": "LMT", "name": "Lockheed Martin", "reasoning": "Defense growth"},
                {"ticker": "NVDA", "name": "NVIDIA", "reasoning": "AI leadership"}
            ],
            "short_term_options": [
                {"ticker": "RTX", "strategy": "Bull Call Spread", "reasoning": "Earnings play"}
            ]
        })
    
    return {
        "history": history,
        "count": len(history)
    }

@app.post("/trigger/ingestion")
async def trigger_data_ingestion(background_tasks: BackgroundTasks):
    """Manually trigger data ingestion"""
    return {"message": "Data ingestion triggered successfully (demo mode)"}

@app.post("/trigger/summarization")
async def trigger_summarization(background_tasks: BackgroundTasks):
    """Manually trigger summarization"""
    return {"message": "Summarization triggered successfully (demo mode)"}

@app.post("/trigger/full-pipeline")
async def trigger_full_pipeline(background_tasks: BackgroundTasks):
    """Manually trigger the full pipeline"""
    return {"message": "Full pipeline triggered successfully (demo mode)"}

@app.get("/stats")
async def get_stats():
    """Get system statistics"""
    return {
        "vector_store": {"documents": 150, "collections": 2},
        "summaries_history_count": 5,
        "investment_ideas_history_count": 3,
        "max_history_size": 10,
        "config": {
            "app_name": "RAG-Driven Investment Portfolio API",
            "version": "1.0.0",
            "environment": "demo"
        }
    }

@app.get("/search/{industry}")
async def search_news(industry: str, query: str = "", top_k: int = 10):
    """Search for news in a specific industry"""
    if industry not in ["defense", "semiconductor"]:
        raise HTTPException(status_code=400, detail="Industry must be 'defense' or 'semiconductor'")
    
    # Mock search results
    mock_articles = [
        {
            "title": f"Latest {industry} industry developments",
            "content": f"Recent news about {industry} sector including market trends and company updates.",
            "source": "Reuters",
            "published_at": datetime.now().isoformat(),
            "relevance_score": 0.95
        },
        {
            "title": f"Investment opportunities in {industry}",
            "content": f"Analysis of investment opportunities in the {industry} sector with focus on key players.",
            "source": "Bloomberg",
            "published_at": (datetime.now() - timedelta(hours=2)).isoformat(),
            "relevance_score": 0.88
        }
    ]
    
    return {
        "industry": industry,
        "query": query,
        "results": mock_articles[:top_k],
        "count": len(mock_articles[:top_k])
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 