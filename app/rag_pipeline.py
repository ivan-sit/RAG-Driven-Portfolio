import asyncio
import schedule
import time
import logging
from datetime import datetime
from typing import List, Dict, Any
import os

from .data_ingestion import DataIngestion
from .text_processor import TextProcessor
from .vector_store import VectorStore
from .llm_processor import LLMProcessor
from .models import (
    IndustrySummary, InvestmentIdeasResponse, 
    SummariesResponse, NewsArticle, ProcessedChunk
)
from .config_manager import config_manager

logger = logging.getLogger(__name__)

class RAGPipeline:
    def __init__(self):
        # Load configuration
        self.rag_config = config_manager.get_rag_config().get('rag', {})
        
        self.data_ingestion = DataIngestion()
        self.text_processor = TextProcessor()
        self.vector_store = VectorStore()
        self.llm_processor = LLMProcessor()
        
        # Storage for recent results
        self.recent_summaries = []
        self.recent_investment_ideas = []
        self.max_history = self.rag_config.get('max_history_size', 6)

    async def run_data_ingestion(self):
        """Run the data ingestion process"""
        logger.info("Starting data ingestion...")
        
        try:
            # Fetch articles from all sources
            articles = await self.data_ingestion.fetch_all_articles()
            
            if not articles:
                logger.warning("No articles fetched")
                return
            
            # Process articles into chunks
            chunks = self.text_processor.process_articles(articles)
            
            if not chunks:
                logger.warning("No chunks created from articles")
                return
            
            # Add chunks to vector store
            self.vector_store.add_chunks(chunks)
            
            logger.info(f"Data ingestion completed: {len(articles)} articles, {len(chunks)} chunks")
            
        except Exception as e:
            logger.error(f"Error in data ingestion: {e}")

    async def run_summarization(self):
        """Run the summarization and investment idea generation process"""
        logger.info("Starting summarization process...")
        
        try:
            # Get recent news for each industry
            retrieval_top_k = self.rag_config.get('retrieval_top_k', 15)
            defense_chunks = self.vector_store.search_recent_news('defense', top_k=retrieval_top_k)
            semiconductor_chunks = self.vector_store.search_recent_news('semiconductor', top_k=retrieval_top_k)
            
            # Generate summaries
            defense_summary = self.llm_processor.generate_industry_summary(defense_chunks, 'defense')
            semiconductor_summary = self.llm_processor.generate_industry_summary(semiconductor_chunks, 'semiconductor')
            
            # Create summaries response
            summaries_response = SummariesResponse(
                defense_summary=defense_summary,
                semiconductor_summary=semiconductor_summary
            )
            
            # Store in history
            self.recent_summaries.append(summaries_response)
            if len(self.recent_summaries) > self.max_history:
                self.recent_summaries.pop(0)
            
            # Generate investment ideas
            all_chunks = defense_chunks + semiconductor_chunks
            investment_ideas = self.llm_processor.generate_investment_ideas(all_chunks)
            
            # Store in history
            self.recent_investment_ideas.append(investment_ideas)
            if len(self.recent_investment_ideas) > self.max_history:
                self.recent_investment_ideas.pop(0)
            
            logger.info("Summarization process completed")
            
        except Exception as e:
            logger.error(f"Error in summarization: {e}")

    async def run_full_pipeline(self):
        """Run the complete RAG pipeline"""
        logger.info("Starting full RAG pipeline...")
        
        # Step 1: Data ingestion
        await self.run_data_ingestion()
        
        # Step 2: Summarization
        await self.run_summarization()
        
        logger.info("Full RAG pipeline completed")

    def get_latest_summaries(self) -> SummariesResponse:
        """Get the latest summaries"""
        if self.recent_summaries:
            return self.recent_summaries[-1]
        else:
            # Return empty summaries if none available
            return SummariesResponse(
                defense_summary=IndustrySummary(
                    summary_text="No summaries available yet.",
                    sources=[],
                    generated_at=datetime.now().isoformat()
                ),
                semiconductor_summary=IndustrySummary(
                    summary_text="No summaries available yet.",
                    sources=[],
                    generated_at=datetime.now().isoformat()
                )
            )

    def get_latest_investment_ideas(self) -> InvestmentIdeasResponse:
        """Get the latest investment ideas"""
        if self.recent_investment_ideas:
            return self.recent_investment_ideas[-1]
        else:
            # Return empty ideas if none available
            return InvestmentIdeasResponse(
                long_term_stocks=[],
                short_term_options=[],
                generated_at=datetime.now().isoformat()
            )

    def get_summaries_history(self) -> List[SummariesResponse]:
        """Get the history of summaries"""
        return self.recent_summaries.copy()

    def get_investment_ideas_history(self) -> List[InvestmentIdeasResponse]:
        """Get the history of investment ideas"""
        return self.recent_investment_ideas.copy()

    def get_vector_store_stats(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        return self.vector_store.get_collection_stats()

    def start_scheduled_tasks(self):
        """Start the scheduled tasks"""
        # Get scheduling intervals from config
        data_ingestion_interval = self.rag_config.get('data_ingestion_interval', 60)
        summarization_interval = self.rag_config.get('summarization_interval', 5)
        
        # Schedule data ingestion every N minutes
        schedule.every(data_ingestion_interval).minutes.do(lambda: asyncio.run(self.run_data_ingestion()))
        
        # Schedule summarization every N minutes
        schedule.every(summarization_interval).minutes.do(lambda: asyncio.run(self.run_summarization()))
        
        logger.info(f"Scheduled tasks started - Data ingestion: {data_ingestion_interval}min, Summarization: {summarization_interval}min")
        
        # Run initial pipeline
        asyncio.run(self.run_full_pipeline())
        
        # Keep the scheduler running
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

    async def manual_trigger(self, task_type: str = "full"):
        """Manually trigger pipeline tasks"""
        if task_type == "ingestion":
            await self.run_data_ingestion()
        elif task_type == "summarization":
            await self.run_summarization()
        elif task_type == "full":
            await self.run_full_pipeline()
        else:
            raise ValueError(f"Unknown task type: {task_type}") 