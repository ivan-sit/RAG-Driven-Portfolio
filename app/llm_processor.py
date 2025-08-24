import os
from typing import List, Dict, Any
from openai import OpenAI
from datetime import datetime
import logging
from .models import (
    IndustrySummary, LongTermStock, ShortTermOption, 
    SourceReference, InvestmentIdeasResponse
)
from .config_manager import config_manager

logger = logging.getLogger(__name__)

class LLMProcessor:
    def __init__(self):
        # Load configuration
        self.rag_config = config_manager.get_rag_config().get('rag', {})
        self.api_config = config_manager.get_api_config().get('api', {})
        
        # Initialize OpenAI client with error handling
        try:
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment variables")
            
            self.client = OpenAI(api_key=api_key)
            logger.info("OpenAI client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            self.client = None
        
        self.model = self.rag_config.get('model', 'gpt-4-turbo-preview')
        self.max_tokens = self.rag_config.get('max_tokens', 300)
        self.temperature = self.rag_config.get('temperature', 0.7)
        
        # Response settings
        response_config = self.api_config.get('response', {})
        self.max_summary_length = response_config.get('max_summary_length', 300)
        self.max_reason_length = response_config.get('max_reason_length', 500)

    def _create_source_references(self, chunks: List[Dict[str, Any]]) -> List[SourceReference]:
        """Create source references from chunks"""
        sources = []
        seen_urls = set()
        
        for chunk in chunks:
            metadata = chunk['metadata']
            url = metadata.get('url', '')
            
            if url and url not in seen_urls:
                sources.append(SourceReference(
                    url=url,
                    source=metadata.get('source', 'Unknown'),
                    timestamp=metadata.get('published_at', '')
                ))
                seen_urls.add(url)
        
        return sources

    def generate_industry_summary(self, chunks: List[Dict[str, Any]], industry: str) -> IndustrySummary:
        """Generate a summary for a specific industry"""
        # print(f"Generating summary for {industry} : {chunks}")
        if not chunks:
            return IndustrySummary(
                summary_text="No recent news available for this industry.",
                sources=[],
                generated_at=datetime.now().isoformat()
            )
        
        # Combine chunk contents
        combined_content = "\n\n".join([chunk['content'] for chunk in chunks])
        
        # Create prompt
        if industry == 'defense':
            prompt = f"""You are a financial analyst specializing in the defense industry. Based on the following recent news articles, provide a concise summary (maximum {self.max_summary_length} words) of the most important developments and trends in the defense sector.

Focus on:
- Major contract announcements
- Government spending and budget changes
- Technology developments
- Company performance and earnings
- Geopolitical factors affecting the industry

News content:
{combined_content}

Provide a clear, professional summary that would be useful for investors:"""
        else:  # semiconductor
            prompt = f"""You are a financial analyst specializing in the semiconductor industry. Based on the following recent news articles, provide a concise summary (maximum {self.max_summary_length} words) of the most important developments and trends in the semiconductor sector.

Focus on:
- Chip demand and supply dynamics
- Technology advancements and new products
- Company earnings and performance
- Supply chain developments
- Market trends and competition

News content:
{combined_content}

Provide a clear, professional summary that would be useful for investors:"""
        
        try:
            if not self.client:
                raise ValueError("OpenAI client not initialized")
                
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            summary_text = response.choices[0].message.content.strip()
            sources = self._create_source_references(chunks)
            
            return IndustrySummary(
                summary_text=summary_text,
                sources=sources,
                generated_at=datetime.now().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Error generating summary for {industry}: {e}")
            return IndustrySummary(
                summary_text=f"Error generating summary for {industry} industry.",
                sources=[],
                generated_at=datetime.now().isoformat()
            )

    def generate_investment_ideas(self, chunks: List[Dict[str, Any]]) -> InvestmentIdeasResponse:
        """Generate investment ideas based on recent news"""
        if not chunks:
            return InvestmentIdeasResponse(
                long_term_stocks=[],
                short_term_options=[],
                generated_at=datetime.now().isoformat()
            )
        
        # Separate chunks by industry
        defense_chunks = [c for c in chunks if c['metadata'].get('industry') == 'defense']
        semiconductor_chunks = [c for c in chunks if c['metadata'].get('industry') == 'semiconductor']
        
        # Generate ideas for each industry
        long_term_stocks = []
        short_term_options = []
        
        # Defense industry ideas
        if defense_chunks:
            defense_ideas = self._generate_industry_investment_ideas(defense_chunks, 'defense')
            long_term_stocks.extend(defense_ideas['long_term'])
            short_term_options.extend(defense_ideas['short_term'])
        
        # Semiconductor industry ideas
        if semiconductor_chunks:
            semiconductor_ideas = self._generate_industry_investment_ideas(semiconductor_chunks, 'semiconductor')
            long_term_stocks.extend(semiconductor_ideas['long_term'])
            short_term_options.extend(semiconductor_ideas['short_term'])
        
        return InvestmentIdeasResponse(
            long_term_stocks=long_term_stocks,
            short_term_options=short_term_options,
            generated_at=datetime.now().isoformat()
        )

    def _generate_industry_investment_ideas(self, chunks: List[Dict[str, Any]], industry: str) -> Dict[str, List]:
        """Generate investment ideas for a specific industry"""
        combined_content = "\n\n".join([chunk['content'] for chunk in chunks])
        
        if industry == 'defense':
            prompt = f"""You are a financial analyst specializing in the defense industry. Based on the following recent news, provide investment recommendations.

News content:
{combined_content}

Please provide:

1. LONG-TERM STOCK PICKS (1-3 stocks):
- Company ticker symbol
- Company name
- Detailed reasoning based on fundamentals, contracts, and industry trends (maximum {self.max_reason_length} words)
- Reference specific news articles

2. SHORT-TERM OPTION PLAYS (1-3 plays):
- Ticker symbol
- Option type (call/put)
- Strike price
- Expiration date (within 2 weeks)
- Direction (bullish/bearish)
- Brief rationale (maximum {self.max_reason_length} words)
- Reference specific news articles

Format your response as JSON:
{{
    "long_term_stocks": [
        {{
            "ticker": "LMT",
            "company_name": "Lockheed Martin",
            "reason": "Detailed reasoning here...",
            "source_references": [{{"url": "...", "source": "...", "timestamp": "..."}}]
        }}
    ],
    "short_term_options": [
        {{
            "ticker": "RTX",
            "option_type": "call",
            "strike_price": 85.0,
            "expiration_date": "2025-08-08",
            "direction": "bullish",
            "reason": "Brief rationale here...",
            "source_references": [{{"url": "...", "source": "...", "timestamp": "..."}}]
        }}
    ]
}}"""
        else:  # semiconductor
            prompt = f"""You are a financial analyst specializing in the semiconductor industry. Based on the following recent news, provide investment recommendations.

News content:
{combined_content}

Please provide:

1. LONG-TERM STOCK PICKS (1-3 stocks):
- Company ticker symbol
- Company name
- Detailed reasoning based on fundamentals, chip demand, and industry trends (maximum {self.max_reason_length} words)
- Reference specific news articles

2. SHORT-TERM OPTION PLAYS (1-3 plays):
- Ticker symbol
- Option type (call/put)
- Strike price
- Expiration date (within 2 weeks)
- Direction (bullish/bearish)
- Brief rationale (maximum {self.max_reason_length} words)
- Reference specific news articles

Format your response as JSON:
{{
    "long_term_stocks": [
        {{
            "ticker": "NVDA",
            "company_name": "NVIDIA Corporation",
            "reason": "Detailed reasoning here...",
            "source_references": [{{"url": "...", "source": "...", "timestamp": "..."}}]
        }}
    ],
    "short_term_options": [
        {{
            "ticker": "AMD",
            "option_type": "call",
            "strike_price": 125.0,
            "expiration_date": "2025-08-08",
            "direction": "bullish",
            "reason": "Brief rationale here...",
            "source_references": [{{"url": "...", "source": "...", "timestamp": "..."}}]
        }}
    ]
}}"""
        
        try:
            if not self.client:
                raise ValueError("OpenAI client not initialized")
                
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=self.temperature
            )
            
            # Parse JSON response
            import json
            response_text = response.choices[0].message.content.strip()
            
            # Try to extract JSON from response
            try:
                # Find JSON in the response
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                json_str = response_text[start_idx:end_idx]
                
                ideas = json.loads(json_str)
                
                # Convert to our models
                long_term_stocks = []
                for stock in ideas.get('long_term_stocks', []):
                    sources = []
                    for ref in stock.get('source_references', []):
                        sources.append(SourceReference(
                            url=ref.get('url', ''),
                            source=ref.get('source', ''),
                            timestamp=ref.get('timestamp', '')
                        ))
                    
                    long_term_stocks.append(LongTermStock(
                        ticker=stock.get('ticker', ''),
                        company_name=stock.get('company_name', ''),
                        reason=stock.get('reason', ''),
                        source_references=sources
                    ))
                
                short_term_options = []
                for option in ideas.get('short_term_options', []):
                    sources = []
                    for ref in option.get('source_references', []):
                        sources.append(SourceReference(
                            url=ref.get('url', ''),
                            source=ref.get('source', ''),
                            timestamp=ref.get('timestamp', '')
                        ))
                    
                    short_term_options.append(ShortTermOption(
                        ticker=option.get('ticker', ''),
                        option_type=option.get('option_type', ''),
                        strike_price=float(option.get('strike_price', 0)),
                        expiration_date=option.get('expiration_date', ''),
                        direction=option.get('direction', ''),
                        reason=option.get('reason', ''),
                        source_references=sources
                    ))
                
                return {
                    'long_term': long_term_stocks,
                    'short_term': short_term_options
                }
                
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing JSON response: {e}")
                logger.error(f"Response text: {response_text}")
                return {'long_term': [], 'short_term': []}
                
        except Exception as e:
            logger.error(f"Error generating investment ideas for {industry}: {e}")
            return {'long_term': [], 'short_term': []} 