from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class SourceReference(BaseModel):
    url: str
    source: str
    timestamp: str

class IndustrySummary(BaseModel):
    summary_text: str
    sources: List[SourceReference]
    generated_at: str

class LongTermStock(BaseModel):
    ticker: str
    company_name: str
    reason: str
    source_references: List[SourceReference]

class ShortTermOption(BaseModel):
    ticker: str
    option_type: str  # "call" or "put"
    strike_price: float
    expiration_date: str
    direction: str  # "bullish" or "bearish"
    reason: str
    source_references: List[SourceReference]

class SummariesResponse(BaseModel):
    defense_summary: IndustrySummary
    semiconductor_summary: IndustrySummary

class InvestmentIdeasResponse(BaseModel):
    long_term_stocks: List[LongTermStock]
    short_term_options: List[ShortTermOption]
    generated_at: str

class NewsArticle(BaseModel):
    title: str
    content: str
    url: str
    source: str
    published_at: str
    ticker_symbols: List[str] = []
    industry: str  # "defense" or "semiconductor"

class ProcessedChunk(BaseModel):
    content: str
    metadata: dict
    embedding: Optional[List[float]] = None 