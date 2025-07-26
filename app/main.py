from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
import logging
from typing import List, Dict, Any
import os
from dotenv import load_dotenv

from .rag_pipeline import RAGPipeline
from .models import (
    SummariesResponse, InvestmentIdeasResponse,
    IndustrySummary, LongTermStock, ShortTermOption
)
from .config_manager import config_manager

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configurations
app_config = config_manager.get_app_config().get('app', {})
api_config = config_manager.get_api_config().get('api', {})

# Initialize FastAPI app
app = FastAPI(
    title=app_config.get('name', 'RAG-Driven Investment Portfolio API'),
    description=app_config.get('description', 'API for retrieving AI-generated investment insights based on real-time news analysis'),
    version=app_config.get('version', '1.0.0')
)

# Add CORS middleware
cors_config = api_config.get('cors', {})
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_config.get('allow_origins', ["*"]),
    allow_credentials=cors_config.get('allow_credentials', True),
    allow_methods=cors_config.get('allow_methods', ["*"]),
    allow_headers=cors_config.get('allow_headers', ["*"]),
)

# Initialize RAG pipeline
rag_pipeline = RAGPipeline()

@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup"""
    logger.info(f"Starting {app_config.get('name', 'RAG-Driven Investment Portfolio API')}")
    
    # Validate configurations
    if not config_manager.validate_configs():
        logger.error("Configuration validation failed")
        raise Exception("Invalid configuration")
    
    # Run initial pipeline in background
    try:
        await rag_pipeline.run_full_pipeline()
        logger.info("Initial pipeline completed successfully")
    except Exception as e:
        logger.error(f"Error in initial pipeline: {e}")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": app_config.get('name', 'RAG-Driven Investment Portfolio API'),
        "version": app_config.get('version', '1.0.0'),
        "status": "running",
        "environment": app_config.get('environment', 'development')
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        stats = rag_pipeline.get_vector_store_stats()
        return {
            "status": "healthy",
            "vector_store_stats": stats,
            "timestamp": asyncio.get_event_loop().time(),
            "config_loaded": bool(config_manager.get_all_configs())
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")

@app.get("/fetchSummaries", response_model=SummariesResponse)
async def fetch_summaries():
    """Get the latest industry summaries"""
    try:
        summaries = rag_pipeline.get_latest_summaries()
        return summaries
    except Exception as e:
        logger.error(f"Error fetching summaries: {e}")
        raise HTTPException(status_code=500, detail="Error fetching summaries")

@app.get("/fetchInvestmentIdeas", response_model=InvestmentIdeasResponse)
async def fetch_investment_ideas():
    """Get the latest investment ideas"""
    try:
        ideas = rag_pipeline.get_latest_investment_ideas()
        return ideas
    except Exception as e:
        logger.error(f"Error fetching investment ideas: {e}")
        raise HTTPException(status_code=500, detail="Error fetching investment ideas")

@app.get("/summaries/history")
async def get_summaries_history():
    """Get the history of summaries"""
    try:
        history = rag_pipeline.get_summaries_history()
        return {
            "history": history,
            "count": len(history)
        }
    except Exception as e:
        logger.error(f"Error fetching summaries history: {e}")
        raise HTTPException(status_code=500, detail="Error fetching summaries history")

@app.get("/investment-ideas/history")
async def get_investment_ideas_history():
    """Get the history of investment ideas"""
    try:
        history = rag_pipeline.get_investment_ideas_history()
        return {
            "history": history,
            "count": len(history)
        }
    except Exception as e:
        logger.error(f"Error fetching investment ideas history: {e}")
        raise HTTPException(status_code=500, detail="Error fetching investment ideas history")

@app.post("/trigger/ingestion")
async def trigger_data_ingestion(background_tasks: BackgroundTasks):
    """Manually trigger data ingestion"""
    try:
        background_tasks.add_task(rag_pipeline.run_data_ingestion)
        return {"message": "Data ingestion triggered successfully"}
    except Exception as e:
        logger.error(f"Error triggering data ingestion: {e}")
        raise HTTPException(status_code=500, detail="Error triggering data ingestion")

@app.post("/trigger/summarization")
async def trigger_summarization(background_tasks: BackgroundTasks):
    """Manually trigger summarization"""
    try:
        background_tasks.add_task(rag_pipeline.run_summarization)
        return {"message": "Summarization triggered successfully"}
    except Exception as e:
        logger.error(f"Error triggering summarization: {e}")
        raise HTTPException(status_code=500, detail="Error triggering summarization")

@app.post("/trigger/full-pipeline")
async def trigger_full_pipeline(background_tasks: BackgroundTasks):
    """Manually trigger the full pipeline"""
    try:
        background_tasks.add_task(rag_pipeline.run_full_pipeline)
        return {"message": "Full pipeline triggered successfully"}
    except Exception as e:
        logger.error(f"Error triggering full pipeline: {e}")
        raise HTTPException(status_code=500, detail="Error triggering full pipeline")

@app.get("/stats")
async def get_stats():
    """Get system statistics"""
    try:
        vector_stats = rag_pipeline.get_vector_store_stats()
        summaries_count = len(rag_pipeline.get_summaries_history())
        ideas_count = len(rag_pipeline.get_investment_ideas_history())
        
        return {
            "vector_store": vector_stats,
            "summaries_history_count": summaries_count,
            "investment_ideas_history_count": ideas_count,
            "max_history_size": rag_pipeline.max_history,
            "config": {
                "app_name": app_config.get('name'),
                "version": app_config.get('version'),
                "environment": app_config.get('environment')
            }
        }
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail="Error fetching stats")

@app.get("/search/{industry}")
async def search_news(industry: str, query: str = "", top_k: int = None):
    """Search for news in a specific industry"""
    try:
        if industry not in ["defense", "semiconductor"]:
            raise HTTPException(status_code=400, detail="Industry must be 'defense' or 'semiconductor'")
        
        # Use config default or provided top_k
        if top_k is None:
            top_k = api_config.get('search', {}).get('default_top_k', 10)
        
        # Validate top_k
        max_top_k = api_config.get('search', {}).get('max_top_k', 50)
        if top_k > max_top_k:
            top_k = max_top_k
        
        if query:
            results = rag_pipeline.vector_store.search_similar(query, industry, top_k)
        else:
            results = rag_pipeline.vector_store.search_recent_news(industry, top_k=top_k)
        
        return {
            "industry": industry,
            "query": query,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        logger.error(f"Error searching news: {e}")
        raise HTTPException(status_code=500, detail="Error searching news")

@app.get("/search/ticker/{ticker}")
async def search_by_ticker(ticker: str, industry: str = "", top_k: int = None):
    """Search for news by ticker symbol"""
    try:
        if industry and industry not in ["defense", "semiconductor"]:
            raise HTTPException(status_code=400, detail="Industry must be 'defense' or 'semiconductor'")
        
        # Use config default or provided top_k
        if top_k is None:
            top_k = api_config.get('search', {}).get('default_top_k', 10)
        
        # Validate top_k
        max_top_k = api_config.get('search', {}).get('max_top_k', 50)
        if top_k > max_top_k:
            top_k = max_top_k
        
        results = []
        if not industry or industry == "defense":
            defense_results = rag_pipeline.vector_store.search_by_ticker(ticker, "defense", top_k)
            results.extend(defense_results)
        
        if not industry or industry == "semiconductor":
            semiconductor_results = rag_pipeline.vector_store.search_by_ticker(ticker, "semiconductor", top_k)
            results.extend(semiconductor_results)
        
        return {
            "ticker": ticker,
            "industry": industry or "all",
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        logger.error(f"Error searching by ticker: {e}")
        raise HTTPException(status_code=500, detail="Error searching by ticker")

@app.get("/config")
async def get_config():
    """Get current configuration (without sensitive data)"""
    try:
        return {
            "app": {
                "name": app_config.get('name'),
                "version": app_config.get('version'),
                "environment": app_config.get('environment')
            },
            "api": {
                "server": api_config.get('server', {}),
                "search": api_config.get('search', {}),
                "response": api_config.get('response', {})
            },
            "rag": {
                "chunk_size": config_manager.get_nested_config('rag', 'rag', 'chunk_size'),
                "chunk_overlap": config_manager.get_nested_config('rag', 'rag', 'chunk_overlap'),
                "model": config_manager.get_nested_config('rag', 'rag', 'model'),
                "max_tokens": config_manager.get_nested_config('rag', 'rag', 'max_tokens'),
                "temperature": config_manager.get_nested_config('rag', 'rag', 'temperature'),
                "retrieval_top_k": config_manager.get_nested_config('rag', 'rag', 'retrieval_top_k'),
                "max_history_size": config_manager.get_nested_config('rag', 'rag', 'max_history_size'),
                "data_ingestion_interval": config_manager.get_nested_config('rag', 'rag', 'data_ingestion_interval'),
                "summarization_interval": config_manager.get_nested_config('rag', 'rag', 'summarization_interval')
            }
        }
    except Exception as e:
        logger.error(f"Error fetching config: {e}")
        raise HTTPException(status_code=500, detail="Error fetching config")

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    
    # Get server configuration
    server_config = api_config.get('server', {})
    host = server_config.get('host', '0.0.0.0')
    port = server_config.get('port', 8000)
    debug = server_config.get('debug', False)
    log_level = server_config.get('log_level', 'info')
    
    uvicorn.run(app, host=host, port=port, log_level=log_level) 