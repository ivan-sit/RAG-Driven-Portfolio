import re
from typing import List, Dict, Any
from langchain.text_splitter import RecursiveCharacterTextSplitter
from .models import NewsArticle, ProcessedChunk
from .config_manager import config_manager
import logging
from .supabase_client import hash_chunk, get_chunk_by_hash, upsert_chunk

logger = logging.getLogger(__name__)

class TextProcessor:
    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        # Load configuration
        self.rag_config = config_manager.get_rag_config().get('rag', {})
        
        # Use config values or fall back to parameters
        self.chunk_size = chunk_size or self.rag_config.get('chunk_size', 1000)
        self.chunk_overlap = chunk_overlap or self.rag_config.get('chunk_overlap', 200)
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        # Get industry configurations
        industries_config = self.rag_config.get('industries', {})
        
        # Defense keywords and tickers
        defense_config = industries_config.get('defense', {})
        self.defense_keywords = defense_config.get('keywords', [])
        self.defense_tickers = defense_config.get('tickers', [])
        
        # Semiconductor keywords and tickers
        semiconductor_config = industries_config.get('semiconductor', {})
        self.semiconductor_keywords = semiconductor_config.get('keywords', [])
        self.semiconductor_tickers = semiconductor_config.get('tickers', [])

    def clean_text(self, text: str) -> str:
        """Clean and standardize text"""
        if not text:
            return ""
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s\.\,\!\?\-\:\;\-\'\"\(\)]', '', text)
        
        # Standardize quotes and dashes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        text = text.replace('–', '-').replace('—', '-')
        
        # Remove multiple periods
        text = re.sub(r'\.{2,}', '.', text)
        
        return text.strip()

    def extract_tickers_from_text(self, text: str) -> List[str]:
        """Extract stock ticker symbols from text"""
        # Common ticker patterns (1-5 capital letters)
        ticker_pattern = r'\b[A-Z]{1,5}\b'
        tickers = re.findall(ticker_pattern, text)
        
        # Filter to known defense and semiconductor tickers
        known_tickers = set(self.defense_tickers + self.semiconductor_tickers)
        
        return [ticker for ticker in tickers if ticker in known_tickers]

    def classify_industry(self, text: str) -> str:
        """Classify text as defense or semiconductor"""
        text_lower = text.lower()
        
        defense_score = sum(1 for keyword in self.defense_keywords if keyword.lower() in text_lower)
        semiconductor_score = sum(1 for keyword in self.semiconductor_keywords if keyword.lower() in text_lower)
        
        if defense_score > semiconductor_score and defense_score > 0:
            return 'defense'
        elif semiconductor_score > 0:
            return 'semiconductor'
        return None

    def process_article(self, article: NewsArticle) -> List[ProcessedChunk]:
        """Process a single article into chunks, using Supabase for chunk deduplication/history."""
        # Clean the text
        cleaned_content = self.clean_text(article.content)
        cleaned_title = self.clean_text(article.title)
        
        if not cleaned_content:
            return []
        
        # Combine title and content for chunking
        full_text = f"Title: {cleaned_title}\n\nContent: {cleaned_content}"
        
        # Split into chunks
        chunks = self.text_splitter.split_text(full_text)
        
        processed_chunks = []
        for i, chunk in enumerate(chunks):
            if len(chunk.strip()) < 50:  # Skip very short chunks
                continue
                
            # Compute chunk hash
            chunk_hash = hash_chunk(chunk)
            if get_chunk_by_hash(chunk_hash):
                logger.info(f"Chunk already in Supabase (skipping): {chunk_hash}")
                continue
            # Extract metadata
            metadata = {
                'title': article.title,
                'url': article.url,
                'source': article.source,
                'published_at': article.published_at,
                'ticker_symbols': ','.join(article.ticker_symbols) if article.ticker_symbols else '',
                'industry': article.industry,
                'chunk_index': i,
                'total_chunks': len(chunks)
            }
            # Add any additional tickers found in this chunk
            chunk_tickers = self.extract_tickers_from_text(chunk)
            if chunk_tickers:
                metadata['chunk_tickers'] = ','.join(chunk_tickers)
            # Insert chunk into Supabase
            upsert_chunk({
                "article_id": article.id,  # Link to the article using the correct foreign key
                "chunk_index": i,
                "content": chunk,
                "chunk_hash": chunk_hash,
                "embedding": None,  # To be filled after embedding
                "metadata": metadata
            })
            processed_chunks.append(ProcessedChunk(
                content=chunk,
                metadata=metadata
            ))
        
        return processed_chunks

    def process_articles(self, articles: List[NewsArticle]) -> List[ProcessedChunk]:
        """Process multiple articles into chunks"""
        all_chunks = []
        
        for article in articles:
            try:
                chunks = self.process_article(article)
                all_chunks.extend(chunks)
                logger.info(f"Processed article '{article.title}' into {len(chunks)} chunks")
            except Exception as e:
                logger.error(f"Error processing article '{article.title}': {e}")
        
        logger.info(f"Total chunks created: {len(all_chunks)}")
        return all_chunks

    def filter_chunks_by_industry(self, chunks: List[ProcessedChunk], industry: str) -> List[ProcessedChunk]:
        """Filter chunks by industry"""
        return [chunk for chunk in chunks if chunk.metadata.get('industry') == industry]

    def filter_chunks_by_time(self, chunks: List[ProcessedChunk], hours: int = None) -> List[ProcessedChunk]:
        """Filter chunks by time (last N hours)"""
        from datetime import datetime, timedelta
        
        # Use config default or provided hours
        if hours is None:
            hours = config_manager.get_api_config().get('api', {}).get('search', {}).get('recent_hours', 24)
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        filtered_chunks = []
        for chunk in chunks:
            try:
                published_time = datetime.fromisoformat(chunk.metadata['published_at'].replace('Z', '+00:00'))
                if published_time >= cutoff_time:
                    filtered_chunks.append(chunk)
            except Exception as e:
                logger.error(f"Error parsing date for chunk: {e}")
                # Include chunks with date parsing errors
                filtered_chunks.append(chunk)
        
        return filtered_chunks 