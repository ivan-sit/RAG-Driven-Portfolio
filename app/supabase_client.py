import os
import hashlib
# from supabase import create_client, Client
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Temporarily comment out to avoid dependency issues
# supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
supabase = None

# --- Hashing helpers ---
def hash_article(url: str, title: str, published_at: str) -> str:
    s = f"{url}|{title}|{published_at}"
    return hashlib.sha256(s.encode()).hexdigest()

def hash_chunk(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()

# --- Article helpers ---
def get_article_by_hash(article_hash: str) -> Optional[Dict[str, Any]]:
    if supabase is None:
        logger.warning("Supabase client not initialized, skipping database operation")
        return None
    try:
        res = supabase.table("articles").select("*").eq("article_hash", article_hash).execute()
        if res.data:
            return res.data[0]
    except Exception as e:
        logger.error(f"Error getting article by hash: {e}")
    return None

def upsert_article(article: Dict[str, Any]) -> Dict[str, Any]:
    if supabase is None:
        logger.warning("Supabase client not initialized, skipping database operation")
        return article
    try:
        res = supabase.table("articles").upsert(article).execute()
        return res.data[0] if res.data else article
    except Exception as e:
        logger.error(f"Error upserting article: {e}")
        return article

# --- Chunk helpers ---
def get_chunk_by_hash(chunk_hash: str) -> Optional[Dict[str, Any]]:
    if supabase is None:
        logger.warning("Supabase client not initialized, skipping database operation")
        return None
    try:
        res = supabase.table("chunks").select("*").eq("chunk_hash", chunk_hash).execute()
        if res.data:
            return res.data[0]
    except Exception as e:
        logger.error(f"Error getting chunk by hash: {e}")
    return None

def upsert_chunk(chunk: Dict[str, Any]) -> Dict[str, Any]:
    if supabase is None:
        logger.warning("Supabase client not initialized, skipping database operation")
        return chunk
    try:
        res = supabase.table("chunks").upsert(chunk).execute()
        return res.data[0] if res.data else chunk
    except Exception as e:
        logger.error(f"Error upserting chunk: {e}")
        return chunk

# --- Query helpers for analytics/history ---
def get_chunks_for_ticker(ticker: str, since: str = None) -> List[Dict[str, Any]]:
    if supabase is None:
        logger.warning("Supabase client not initialized, skipping database operation")
        return []
    try:
        query = supabase.table("chunks").select("*")
        if since:
            query = query.gte("inserted_at", since)
        query = query.filter("metadata->>ticker_symbols", "cs", f'{{"{ticker}"}}')
        res = query.execute()
        return res.data or []
    except Exception as e:
        logger.error(f"Error getting chunks for ticker: {e}")
        return []

def get_articles_for_day(day: str) -> List[Dict[str, Any]]:
    # day: 'YYYY-MM-DD'
    if supabase is None:
        logger.warning("Supabase client not initialized, skipping database operation")
        return []
    try:
        res = supabase.table("articles").select("*").gte("published_at", f"{day}T00:00:00Z").lt("published_at", f"{day}T23:59:59Z").execute()
        return res.data or []
    except Exception as e:
        logger.error(f"Error getting articles for day: {e}")
        return [] 