import os
import hashlib
from supabase import create_client, Client
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# --- Hashing helpers ---
def hash_article(url: str, title: str, published_at: str) -> str:
    s = f"{url}|{title}|{published_at}"
    return hashlib.sha256(s.encode()).hexdigest()

def hash_chunk(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()

# --- Article helpers ---
def get_article_by_hash(article_hash: str) -> Optional[Dict[str, Any]]:
    res = supabase.table("articles").select("*").eq("article_hash", article_hash).execute()
    if res.data:
        return res.data[0]
    return None

def upsert_article(article: Dict[str, Any]) -> Dict[str, Any]:
    res = supabase.table("articles").upsert(article).execute()
    return res.data[0] if res.data else None

def article_has_chunks(article_id: int) -> bool:
    """Check if any chunks exist for the given article ID."""
    res = supabase.table("chunks").select("id").eq("article_id", article_id).limit(1).execute()
    return bool(res.data)

# --- Chunk helpers ---
def get_chunk_by_hash(chunk_hash: str) -> Optional[Dict[str, Any]]:
    res = supabase.table("chunks").select("*").eq("chunk_hash", chunk_hash).execute()
    if res.data:
        return res.data[0]
    return None

def upsert_chunk(chunk: Dict[str, Any]) -> Dict[str, Any]:
    res = supabase.table("chunks").upsert(chunk).execute()
    return res.data[0] if res.data else None

# --- Query helpers for analytics/history ---
def get_chunks_for_ticker(ticker: str, since: str = None) -> List[Dict[str, Any]]:
    query = supabase.table("chunks").select("*")
    if since:
        query = query.gte("inserted_at", since)
    query = query.filter("metadata->>ticker_symbols", "cs", f'{{"{ticker}"}}')
    res = query.execute()
    return res.data or []

def get_articles_for_day(day: str) -> List[Dict[str, Any]]:
    # day: 'YYYY-MM-DD'
    res = supabase.table("articles").select("*").gte("published_at", f"{day}T00:00:00Z").lt("published_at", f"{day}T23:59:59Z").execute()
    return res.data or [] 