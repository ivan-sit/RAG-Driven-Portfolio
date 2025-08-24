import os
import hashlib
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase = None
try:
	from supabase import create_client, Client  # type: ignore
	# Create client at runtime; if it fails, fall back to None
	supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
except Exception as e:
	# Log to console so we can still run the backend without Supabase
	print(f"Warning: Supabase client not initialized: {e}")

# --- Hashing helpers ---
def hash_article(url: str, title: str, published_at: str) -> str:
	# Use the same hash computation as the chunks
	s = f"{url}|{title}|{published_at}"
	return hashlib.sha256(s.encode()).hexdigest()

def hash_chunk(content: str) -> str:
	return hashlib.sha256(content.encode()).hexdigest()

# --- Article helpers ---
def get_article_by_hash(article_hash: str) -> Optional[Dict[str, Any]]:
	if not supabase:
		return None
	res = supabase.table("articles").select("*").eq("article_hash", article_hash).execute()
	if res.data:
		return res.data[0]
	return None

def upsert_article(article: Dict[str, Any]) -> Optional[Dict[str, Any]]:
	if not supabase:
		return None
	res = supabase.table("articles").upsert(article).execute()
	return res.data[0] if res.data else None

# --- Chunk helpers ---
def get_chunk_by_hash(chunk_hash: str) -> Optional[Dict[str, Any]]:
	if not supabase:
		return None
	res = supabase.table("chunks").select("*").eq("chunk_hash", chunk_hash).execute()
	if res.data:
		return res.data[0]
	return None

def upsert_chunk(chunk: Dict[str, Any]) -> Optional[Dict[str, Any]]:
	if not supabase:
		return None
	
	# If only chunk_hash and embedding are provided, do a partial update
	if len(chunk) == 2 and 'chunk_hash' in chunk and 'embedding' in chunk:
		try:
			res = supabase.table("chunks").update({
				"embedding": chunk["embedding"]
			}).eq("chunk_hash", chunk["chunk_hash"]).execute()
			return res.data[0] if res.data else None
		except Exception as e:
			logger.error(f"Error updating chunk embedding: {e}")
			return None
	
	# Otherwise, do a full upsert
	try:
		res = supabase.table("chunks").upsert(chunk).execute()
		return res.data[0] if res.data else None
	except Exception as e:
		logger.error(f"Error upserting chunk: {e}")
		return None

# --- Query helpers for analytics/history ---
def get_chunks_for_ticker(ticker: str, since: str = None) -> List[Dict[str, Any]]:
	if not supabase:
		return []
	query = supabase.table("chunks").select("*")
	if since:
		query = query.gte("inserted_at", since)
	query = query.filter("metadata->>ticker_symbols", "cs", f'{{"{ticker}"}}')
	res = query.execute()
	return res.data or []

def get_articles_for_day(day: str) -> List[Dict[str, Any]]:
    # day: 'YYYY-MM-DD'
    if not supabase:
        return []
    res = supabase.table("articles").select("*").gte("published_at", f"{day}T00:00:00Z").lt("published_at", f"{day}T23:59:59Z").execute()
    return res.data or []

def article_has_chunks(article_id: int) -> bool:
    """Check if an article already has chunks stored"""
    if not supabase:
        return False
    res = supabase.table("chunks").select("id").eq("article_id", article_id).limit(1).execute()
    return bool(res.data)
