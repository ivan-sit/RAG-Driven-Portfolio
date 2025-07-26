import os
import chromadb
from chromadb.config import Settings
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from typing import List, Dict, Any, Optional
import logging
from .models import ProcessedChunk
from .config_manager import config_manager

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self, persist_directory: str = None):
        # Load configuration
        self.rag_config = config_manager.get_rag_config().get('rag', {})
        self.api_config = config_manager.get_api_config().get('api', {})
        
        # Use config values or fall back to parameters
        vector_store_config = self.rag_config.get('vector_store', {})
        self.persist_directory = persist_directory or vector_store_config.get('persist_directory', './chroma_db')
        self.embedding_model = vector_store_config.get('embedding_model', 'text-embedding-ada-002')
        self.distance_metric = vector_store_config.get('distance_metric', 'cosine')
        
        self.embeddings = OpenAIEmbeddings(
            model=self.embedding_model,
            openai_api_key=os.getenv('OPENAI_API_KEY')
        )
        
        # Initialize Chroma client
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(
                anonymized_telemetry=False
            )
        )
        
        # Create collections for each industry
        self.defense_collection = self.client.get_or_create_collection(
            name="defense_news",
            metadata={"hnsw:space": self.distance_metric}
        )
        
        self.semiconductor_collection = self.client.get_or_create_collection(
            name="semiconductor_news",
            metadata={"hnsw:space": self.distance_metric}
        )
        
        logger.info("Vector store initialized")

    def add_chunks(self, chunks: List[ProcessedChunk]) -> None:
        """Add chunks to the vector store"""
        defense_chunks = []
        semiconductor_chunks = []
        
        # Separate chunks by industry
        for chunk in chunks:
            if chunk.metadata.get('industry') == 'defense':
                defense_chunks.append(chunk)
            elif chunk.metadata.get('industry') == 'semiconductor':
                semiconductor_chunks.append(chunk)
        
        # Add to respective collections
        if defense_chunks:
            self._add_to_collection(self.defense_collection, defense_chunks)
        
        if semiconductor_chunks:
            self._add_to_collection(self.semiconductor_collection, semiconductor_chunks)
        
        logger.info(f"Added {len(defense_chunks)} defense chunks and {len(semiconductor_chunks)} semiconductor chunks")

    def _add_to_collection(self, collection, chunks: List[ProcessedChunk]) -> None:
        """Add chunks to a specific collection"""
        documents = []
        metadatas = []
        ids = []
        
        for i, chunk in enumerate(chunks):
            # Create unique ID
            chunk_id = f"{chunk.metadata['url']}_{chunk.metadata['chunk_index']}"
            
            documents.append(chunk.content)
            metadatas.append(chunk.metadata)
            ids.append(chunk_id)
        
        # Add to collection
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

    def search_similar(self, query: str, industry: str, top_k: int = None) -> List[Dict[str, Any]]:
        """Search for similar chunks"""
        # Use config default or provided top_k
        if top_k is None:
            top_k = self.api_config.get('search', {}).get('default_top_k', 10)
        
        if industry == 'defense':
            collection = self.defense_collection
        elif industry == 'semiconductor':
            collection = self.semiconductor_collection
        else:
            raise ValueError(f"Unknown industry: {industry}")
        
        # Search in collection
        results = collection.query(
            query_texts=[query],
            n_results=top_k,
            include=['documents', 'metadatas', 'distances']
        )
        
        # Format results
        formatted_results = []
        if results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                formatted_results.append({
                    'content': doc,
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if results['distances'] else None
                })
        
        return formatted_results

    def search_by_ticker(self, ticker: str, industry: str, top_k: int = None) -> List[Dict[str, Any]]:
        """Search for chunks containing specific ticker symbols"""
        # Use config default or provided top_k
        if top_k is None:
            top_k = self.api_config.get('search', {}).get('default_top_k', 10)
        
        if industry == 'defense':
            collection = self.defense_collection
        elif industry == 'semiconductor':
            collection = self.semiconductor_collection
        else:
            raise ValueError(f"Unknown industry: {industry}")
        
        # Search for ticker in metadata
        results = collection.query(
            query_texts=[ticker],
            n_results=top_k,
            where={"ticker_symbols": {"$contains": ticker}},
            include=['documents', 'metadatas', 'distances']
        )
        
        # Format results
        formatted_results = []
        if results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                formatted_results.append({
                    'content': doc,
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if results['distances'] else None
                })
        
        return formatted_results

    def search_recent_news(self, industry: str, hours: int = None, top_k: int = None) -> List[Dict[str, Any]]:
        """Search for recent news in the last N hours"""
        from datetime import datetime, timedelta
        
        # Use config defaults or provided values
        if hours is None:
            hours = self.api_config.get('search', {}).get('recent_hours', 24)
        if top_k is None:
            top_k = self.api_config.get('search', {}).get('default_top_k', 10)
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        if industry == 'defense':
            collection = self.defense_collection
        elif industry == 'semiconductor':
            collection = self.semiconductor_collection
        else:
            raise ValueError(f"Unknown industry: {industry}")
        
        # Get all documents and filter by time
        results = collection.get(
            include=['documents', 'metadatas']
        )
        
        # Filter by time
        recent_results = []
        for i, metadata in enumerate(results['metadatas']):
            try:
                published_time = datetime.fromisoformat(metadata['published_at'].replace('Z', '+00:00'))
                if published_time >= cutoff_time:
                    recent_results.append({
                        'content': results['documents'][i],
                        'metadata': metadata
                    })
            except Exception as e:
                logger.error(f"Error parsing date: {e}")
                # Include if date parsing fails
                recent_results.append({
                    'content': results['documents'][i],
                    'metadata': metadata
                })
        
        # Sort by recency and return top_k
        recent_results.sort(
            key=lambda x: x['metadata']['published_at'],
            reverse=True
        )
        
        return recent_results[:top_k]

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collections"""
        defense_count = self.defense_collection.count()
        semiconductor_count = self.semiconductor_collection.count()
        
        return {
            'defense_chunks': defense_count,
            'semiconductor_chunks': semiconductor_count,
            'total_chunks': defense_count + semiconductor_count,
            'persist_directory': self.persist_directory,
            'embedding_model': self.embedding_model,
            'distance_metric': self.distance_metric
        }

    def clear_collections(self) -> None:
        """Clear all collections (use with caution)"""
        self.client.delete_collection("defense_news")
        self.client.delete_collection("semiconductor_news")
        
        # Recreate collections
        self.defense_collection = self.client.create_collection(
            name="defense_news",
            metadata={"hnsw:space": self.distance_metric}
        )
        
        self.semiconductor_collection = self.client.create_collection(
            name="semiconductor_news",
            metadata={"hnsw:space": self.distance_metric}
        )
        
        logger.info("Collections cleared and recreated") 