import os
import asyncio
import aiohttp
import feedparser
from datetime import datetime, timedelta
from typing import List, Dict, Any
import yfinance as yf
from alpha_vantage.timeseries import TimeSeries
import finnhub
from newsapi import NewsApiClient
from bs4 import BeautifulSoup
import re
from newspaper import Article
import logging

from .models import NewsArticle
from .config_manager import config_manager
from .supabase_client import (
    hash_article, hash_chunk, get_article_by_hash, upsert_article, get_chunk_by_hash, upsert_chunk
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataIngestion:
    def __init__(self):
        # Load configuration
        self.config = config_manager.get_api_config().get('api', {})
        self.rag_config = config_manager.get_rag_config().get('rag', {})
        
        # Initialize API clients
        self.newsapi = NewsApiClient(api_key=os.getenv('NEWSAPI_API_KEY'))
        self.alpha_vantage = TimeSeries(key=os.getenv('ALPHA_VANTAGE_API_KEY'))
        self.finnhub_client = finnhub.Client(api_key=os.getenv('FINNHUB_API_KEY'))
        
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

    async def fetch_newsapi_articles(self) -> List[NewsArticle]:
        """Fetch articles from NewsAPI"""
        articles = []
        
        # Check if NewsAPI is enabled
        newsapi_config = self.config.get('data_sources', {}).get('newsapi', {})
        if not newsapi_config.get('enabled', True):
            logger.info("NewsAPI is disabled in configuration")
            return articles
        
        try:
            # Build defense query
            defense_query = ' OR '.join(self.defense_keywords + self.defense_tickers)
            
            # Build semiconductor query
            semiconductor_query = ' OR '.join(self.semiconductor_keywords + self.semiconductor_tickers)
            
            # Get NewsAPI settings from config
            page_size = newsapi_config.get('page_size', 50)
            language = newsapi_config.get('language', 'en')
            sort_by = newsapi_config.get('sort_by', 'publishedAt')
            
            # Fetch defense news
            defense_news = self.newsapi.get_everything(
                q=defense_query,
                language=language,
                sort_by=sort_by,
                from_param=(datetime.now() - timedelta(hours=24)).strftime('%Y-%m-%d'),
                page_size=page_size
            )
            
            # Fetch semiconductor news
            semiconductor_news = self.newsapi.get_everything(
                q=semiconductor_query,
                language=language,
                sort_by=sort_by,
                from_param=(datetime.now() - timedelta(hours=24)).strftime('%Y-%m-%d'),
                page_size=page_size
            )
            
            # Process defense articles
            for article in defense_news.get('articles', []):
                title = article.get('title', '')
                description = article.get('description', '')
                content_text = f"{title} {description}".strip()
                
                if self._is_relevant_defense(content_text):
                    articles.append(NewsArticle(
                        title=title,
                        content=description,
                        url=article.get('url', ''),
                        source=article.get('source', {}).get('name', 'Unknown'),
                        published_at=article.get('publishedAt', ''),
                        ticker_symbols=self._extract_tickers(content_text),
                        industry='defense'
                    ))
            
            # Process semiconductor articles
            for article in semiconductor_news.get('articles', []):
                title = article.get('title', '')
                description = article.get('description', '')
                content_text = f"{title} {description}".strip()
                
                if self._is_relevant_semiconductor(content_text):
                    articles.append(NewsArticle(
                        title=title,
                        content=description,
                        url=article.get('url', ''),
                        source=article.get('source', {}).get('name', 'Unknown'),
                        published_at=article.get('publishedAt', ''),
                        ticker_symbols=self._extract_tickers(content_text),
                        industry='semiconductor'
                    ))
                    
        except Exception as e:
            logger.error(f"Error fetching from NewsAPI: {e}")
        
        return articles

    async def fetch_rss_feeds(self) -> List[NewsArticle]:
        """Fetch articles from RSS feeds"""
        articles = []
        
        # Check if RSS feeds are enabled
        rss_config = self.config.get('data_sources', {}).get('rss_feeds', {})
        if not rss_config.get('enabled', True):
            logger.info("RSS feeds are disabled in configuration")
            return articles
        
        feeds = rss_config.get('feeds', [])
        
        for feed_config in feeds:
            try:
                feed_url = feed_config['url']
                max_articles = feed_config.get('max_articles', 20)
                feed_name = feed_config.get('name', 'Unknown')
                
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:max_articles]:
                    title = getattr(entry, 'title', '')
                    link = getattr(entry, 'link', '')
                    published = getattr(entry, 'published', '')
                    
                    content = self._extract_content_from_url(link)
                    if content:
                        content_text = f"{title} {content}".strip()
                        industry = self._classify_industry(content_text)
                        if industry:
                            articles.append(NewsArticle(
                                title=title,
                                content=content,
                                url=link,
                                source=feed_name,
                                published_at=published,
                                ticker_symbols=self._extract_tickers(content_text),
                                industry=industry
                            ))
            except Exception as e:
                logger.error(f"Error fetching RSS feed {feed_config.get('name', 'Unknown')}: {e}")
        
        return articles

    def _extract_content_from_url(self, url: str) -> str:
        """Extract article content from URL"""
        try:
            article = Article(url)
            article.config.browser_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            article.download()
            article.parse()
            return article.text if article.text else ""
        except Exception as e:
            # Don't log 403 errors as they're expected for some sites
            if "403" not in str(e):
                logger.error(f"Error extracting content from {url}: {e}")
            return ""

    def _classify_industry(self, text: str) -> str:
        """Classify text as defense or semiconductor"""
        text_lower = text.lower()
        
        defense_score = sum(1 for keyword in self.defense_keywords if keyword.lower() in text_lower)
        semiconductor_score = sum(1 for keyword in self.semiconductor_keywords if keyword.lower() in text_lower)
        
        if defense_score > semiconductor_score and defense_score > 0:
            return 'defense'
        elif semiconductor_score > 0:
            return 'semiconductor'
        return ''

    def _is_relevant_defense(self, text: str) -> bool:
        """Check if text is relevant to defense industry"""
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in self.defense_keywords)

    def _is_relevant_semiconductor(self, text: str) -> bool:
        """Check if text is relevant to semiconductor industry"""
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in self.semiconductor_keywords)

    def _extract_tickers(self, text: str) -> List[str]:
        """Extract stock ticker symbols from text"""
        if not text:
            return []
            
        # Common ticker patterns
        ticker_pattern = r'\b[A-Z]{1,5}\b'
        tickers = re.findall(ticker_pattern, text)
        
        # Filter to known defense and semiconductor tickers
        known_tickers = set(self.defense_tickers + self.semiconductor_tickers)
        
        return [ticker for ticker in tickers if ticker in known_tickers]

    async def fetch_all_articles(self) -> List[NewsArticle]:
        """Fetch articles from all sources, using Supabase for deduplication/history."""
        tasks = [
            self.fetch_newsapi_articles(),
            self.fetch_rss_feeds()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_articles = []
        for result in results:
            if isinstance(result, list):
                all_articles.extend(result)
            else:
                logger.error(f"Error in data ingestion: {result}")
        
        # Remove duplicates based on URL (in-memory)
        seen_urls = set()
        unique_articles = []
        for article in all_articles:
            if article.url not in seen_urls:
                seen_urls.add(article.url)
                unique_articles.append(article)
        
        logger.info(f"Fetched {len(unique_articles)} unique articles")
        
        # --- Supabase persistent cache: filter out already-processed articles ---
        new_articles = []
        for article in unique_articles:
            article_hash = hash_article(article.url, article.title, article.published_at)
            if not get_article_by_hash(article_hash):
                # Insert into Supabase
                upsert_article({
                    "url": article.url,
                    "title": article.title,
                    "published_at": article.published_at,
                    "source": article.source,
                    "industry": article.industry,
                    "article_hash": article_hash
                })
                new_articles.append(article)
            else:
                logger.info(f"Article already in Supabase: {article.url}")
        
        logger.info(f"{len(new_articles)} new articles to process (not in Supabase)")
        return new_articles

    def clean_text(self, text: str) -> str:
        """Clean and standardize text"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s\.\,\!\?\-\:\;]', '', text)
        # Standardize to lowercase
        text = text.lower().strip()
        return text 