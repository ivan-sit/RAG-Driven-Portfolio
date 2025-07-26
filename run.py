#!/usr/bin/env python3
"""
RAG-Driven Investment Portfolio - Main Startup Script
"""

import asyncio
import uvicorn
import logging
import os
from dotenv import load_dotenv
from app.main import app
from app.rag_pipeline import RAGPipeline
from app.config_manager import config_manager

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Main startup function"""
    # Load configurations
    app_config = config_manager.get_app_config().get('app', {})
    api_config = config_manager.get_api_config().get('api', {})
    
    logger.info(f"Starting {app_config.get('name', 'RAG-Driven Investment Portfolio System')}")
    
    # Validate configurations
    if not config_manager.validate_configs():
        logger.error("Configuration validation failed")
        return
    
    # Check required environment variables
    required_vars = [
        'OPENAI_API_KEY',
        'NEWSAPI_API_KEY',
        'ALPHA_VANTAGE_API_KEY',
        'FINNHUB_API_KEY'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        logger.error("Please set these variables in your .env file")
        return
    
    # Initialize RAG pipeline
    try:
        rag_pipeline = RAGPipeline()
        logger.info("RAG pipeline initialized successfully")
        
        # Run initial pipeline
        logger.info("Running initial data ingestion and summarization...")
        await rag_pipeline.run_full_pipeline()
        logger.info("Initial pipeline completed")
        
    except Exception as e:
        logger.error(f"Error initializing RAG pipeline: {e}")
        return
    
    # Start the FastAPI server
    server_config = api_config.get('server', {})
    host = server_config.get('host', '0.0.0.0')
    port = server_config.get('port', 8000)
    log_level = server_config.get('log_level', 'info')
    
    logger.info(f"Starting FastAPI server on {host}:{port}")
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=log_level
    )

if __name__ == "__main__":
    asyncio.run(main()) 