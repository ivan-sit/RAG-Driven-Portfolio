import os
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Qdrant
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
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
		self.persist_directory = persist_directory or vector_store_config.get('persist_directory', './qdrant_db')
		self.embedding_model = vector_store_config.get('embedding_model', 'text-embedding-ada-002')
		self.distance_metric = vector_store_config.get('distance_metric', 'cosine')
		
		# Initialize LangChain OpenAI embeddings
		try:
			api_key = os.getenv('OPENAI_API_KEY')
			if not api_key:
				raise ValueError("OPENAI_API_KEY not found in environment variables")
			
			self.embeddings = OpenAIEmbeddings(
				model=self.embedding_model,
				openai_api_key=api_key
			)
			logger.info(f"Using LangChain OpenAI embedding model: {self.embedding_model}")
		except Exception as e:
			logger.error(f"Failed to initialize LangChain OpenAI embeddings: {e}")
			self.embeddings = None
			logger.warning("OpenAI embeddings not available")
		
		# Initialize Qdrant client
		try:
			self.client = QdrantClient(path=self.persist_directory)
			logger.info(f"Qdrant client initialized with path: {self.persist_directory}")
		except Exception as e:
			logger.error(f"Failed to initialize Qdrant client: {e}")
			self.client = None
		
		# Create Qdrant collections if they don't exist
		if self.client and self.embeddings:
			try:
				vector_size = 1536  # OpenAI text-embedding-ada-002 dimension
				
				# Create defense collection
				try:
					self.client.get_collection("defense_news")
					logger.info("Defense collection already exists")
				except:
					self.client.create_collection(
						collection_name="defense_news",
						vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
					)
					logger.info("Created defense_news collection")
				
				# Create semiconductor collection
				try:
					self.client.get_collection("semiconductor_news")
					logger.info("Semiconductor collection already exists")
				except:
					self.client.create_collection(
						collection_name="semiconductor_news",
						vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
					)
					logger.info("Created semiconductor_news collection")
					
			except Exception as e:
				logger.error(f"Failed to create Qdrant collections: {e}")
		
		# Initialize LangChain Qdrant vector stores
		try:
			logger.info(f"Client available: {self.client is not None}")
			logger.info(f"Embeddings available: {self.embeddings is not None}")
			
			if self.client and self.embeddings:
				logger.info("Creating defense vector store...")
				self.defense_vectorstore = Qdrant(
					client=self.client,
					collection_name="defense_news",
					embeddings=self.embeddings
				)
				logger.info("Defense vector store created successfully")
				
				logger.info("Creating semiconductor vector store...")
				self.semiconductor_vectorstore = Qdrant(
					client=self.client,
					collection_name="semiconductor_news",
					embeddings=self.embeddings
				)
				logger.info("Semiconductor vector store created successfully")
				logger.info("LangChain Qdrant vector stores initialized")
			else:
				self.defense_vectorstore = None
				self.semiconductor_vectorstore = None
				logger.warning("Qdrant vector stores not initialized due to missing client or embeddings")
		except Exception as e:
			logger.error(f"Failed to initialize LangChain Qdrant vector stores: {e}")
			self.defense_vectorstore = None
			self.semiconductor_vectorstore = None
		
		logger.info("Vector store initialized")
		
		# Generate embeddings for existing chunks that don't have them
		self._generate_embeddings_for_existing_chunks()

	def _generate_embeddings_for_existing_chunks(self) -> None:
		"""Generate embeddings for chunks that don't have them yet"""
		if not self.embeddings:
			logger.warning("Embeddings not available, skipping existing chunks")
			return
		
		try:
			from .supabase_client import supabase
			
			if not supabase:
				logger.warning("Supabase not available, skipping existing chunks")
				return
			
			# Get chunks without embeddings
			response = supabase.table("chunks").select("chunk_hash, content").is_("embedding", "null").limit(50).execute()
			
			if not response.data:
				logger.info("No chunks without embeddings found")
				return
			
			logger.info(f"Found {len(response.data)} chunks without embeddings, generating...")
			
			# Generate embeddings for these chunks
			documents = [chunk['content'] for chunk in response.data]
			embeddings = self.embeddings.embed_documents(documents)
			
			# Save embeddings
			success_count = 0
			for i, chunk in enumerate(response.data):
				if i < len(embeddings):
					try:
						result = supabase.table("chunks").update({
							"embedding": embeddings[i]
						}).eq("chunk_hash", chunk['chunk_hash']).execute()
						
						if result.data:
							success_count += 1
							logger.debug(f"Generated embedding for chunk {chunk['chunk_hash']}")
					except Exception as e:
						logger.error(f"Error saving embedding for chunk {chunk['chunk_hash']}: {e}")
			
			logger.info(f"Generated embeddings for {success_count}/{len(response.data)} existing chunks")
			
		except Exception as e:
			logger.error(f"Error generating embeddings for existing chunks: {e}")

	def add_chunks(self, chunks: List[ProcessedChunk]) -> None:
		"""Add chunks to the vector store"""
		if not chunks:
			logger.warning("No chunks to add")
			return
		
		# Generate embeddings directly and save to Supabase
		self._generate_and_save_embeddings(chunks)
		
		# Also try to add to vector stores if they're available
		defense_chunks = []
		semiconductor_chunks = []
		
		# Separate chunks by industry
		for chunk in chunks:
			if chunk.metadata.get('industry') == 'defense':
				defense_chunks.append(chunk)
			elif chunk.metadata.get('industry') == 'semiconductor':
				semiconductor_chunks.append(chunk)
		
		# Add to respective collections if vector stores are available
		if defense_chunks and self.defense_vectorstore:
			self._add_to_collection(self.defense_vectorstore, defense_chunks)
		
		if semiconductor_chunks and self.semiconductor_vectorstore:
			self._add_to_collection(self.semiconductor_vectorstore, semiconductor_chunks)
		
		logger.info(f"Added {len(defense_chunks)} defense chunks and {len(semiconductor_chunks)} semiconductor chunks")

	def _generate_and_save_embeddings(self, chunks: List[ProcessedChunk]) -> None:
		"""Generate embeddings directly and save to Supabase"""
		if not self.embeddings:
			logger.error("Embeddings not available")
			return
		
		try:
			from .supabase_client import upsert_chunk
			
			# Extract documents for embedding generation
			documents = [chunk.content for chunk in chunks]
			
			# Generate embeddings
			logger.info(f"Generating embeddings for {len(documents)} chunks...")
			embeddings = self.embeddings.embed_documents(documents)
			logger.info(f"Generated {len(embeddings)} embeddings")
			
			# Save embeddings to Supabase
			success_count = 0
			for i, chunk in enumerate(chunks):
				if i < len(embeddings):
					chunk_hash = chunk.metadata.get('chunk_hash')
					if chunk_hash:
						try:
							result = upsert_chunk({
								"chunk_hash": chunk_hash,
								"embedding": embeddings[i]
							})
							if result:
								success_count += 1
								logger.debug(f"Saved embedding for chunk {chunk_hash}")
							else:
								logger.warning(f"Failed to save embedding for chunk {chunk_hash}")
						except Exception as e:
							logger.error(f"Error saving embedding for chunk {chunk_hash}: {e}")
			
			logger.info(f"Successfully saved {success_count}/{len(chunks)} embeddings to Supabase")
			
		except Exception as e:
			logger.error(f"Error generating and saving embeddings: {e}")

	def _add_to_collection(self, vectorstore, chunks: List[ProcessedChunk]) -> None:
		"""Add chunks to a specific collection using LangChain"""
		if not vectorstore:
			logger.error("Vector store not initialized")
			return
		
		documents = []
		metadatas = []
		
		for chunk in chunks:
			documents.append(chunk.content)
			metadatas.append(chunk.metadata)
		
		# Add to LangChain vector store (this will generate embeddings)
		try:
			vectorstore.add_texts(
				texts=documents,
				metadatas=metadatas
			)
			logger.info(f"Added {len(documents)} documents to vector store")
		except Exception as e:
			logger.error(f"Error adding documents to vector store: {e}")
			return
		
		# Get the embeddings that were generated and store them back to Supabase
		try:
			from .supabase_client import upsert_chunk
			
			# Get embeddings for the documents we just added
			if self.embeddings:
				embeddings = self.embeddings.embed_documents(documents)
				
				# Update each chunk in Supabase with its embedding
				for i, chunk in enumerate(chunks):
					chunk_hash = chunk.metadata.get('chunk_hash')
					if chunk_hash and i < len(embeddings):
						upsert_chunk({
							"chunk_hash": chunk_hash,
							"embedding": embeddings[i]
						})
						logger.debug(f"Updated embedding for chunk {chunk_hash}")
		except Exception as e:
			logger.error(f"Error updating embeddings in Supabase: {e}")

	def search_similar(self, query: str, industry: str, top_k: int = None) -> List[Dict[str, Any]]:
		"""Search for similar chunks"""
		# Use config default or provided top_k
		if top_k is None:
			top_k = self.api_config.get('search', {}).get('default_top_k', 10)
		
		if industry == 'defense':
			vectorstore = self.defense_vectorstore
		elif industry == 'semiconductor':
			vectorstore = self.semiconductor_vectorstore
		else:
			raise ValueError(f"Unknown industry: {industry}")
		
		if not vectorstore:
			logger.error(f"Vector store not initialized for industry: {industry}")
			return []
		
		try:
			# Search in collection
			results = vectorstore.similarity_search(
				query,
				k=top_k
			)
			
			# Format results
			formatted_results = []
			for doc in results:
				formatted_results.append({
					'content': doc.page_content,
					'metadata': doc.metadata,
					'distance': None  # Chroma similarity_search doesn't return distances directly
				})
			
			return formatted_results
			
		except Exception as e:
			logger.error(f"Error searching similar: {e}")
			return []

	def search_by_ticker(self, ticker: str, industry: str, top_k: int = None) -> List[Dict[str, Any]]:
		"""Search for chunks containing specific ticker symbols"""
		# Use config default or provided top_k
		if top_k is None:
			top_k = self.api_config.get('search', {}).get('default_top_k', 10)
		
		if industry == 'defense':
			vectorstore = self.defense_vectorstore
		elif industry == 'semiconductor':
			vectorstore = self.semiconductor_vectorstore
		else:
			raise ValueError(f"Unknown industry: {industry}")
		
		if not vectorstore:
			logger.error(f"Vector store not initialized for industry: {industry}")
			return []
		
		try:
			# Search for ticker in the vector store
			results = vectorstore.similarity_search(
				ticker,
				k=top_k
			)
			
			# Filter results to only include those with the ticker in metadata
			formatted_results = []
			for doc in results:
				ticker_symbols = doc.metadata.get('ticker_symbols', '')
				chunk_tickers = doc.metadata.get('chunk_tickers', '')
				all_tickers = f"{ticker_symbols},{chunk_tickers}".lower()
				
				if ticker.lower() in all_tickers:
					formatted_results.append({
						'content': doc.page_content,
						'metadata': doc.metadata,
						'distance': None
					})
			
			return formatted_results
			
		except Exception as e:
			logger.error(f"Error searching by ticker: {e}")
			return []

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
			vectorstore = self.defense_vectorstore
		elif industry == 'semiconductor':
			vectorstore = self.semiconductor_vectorstore
		else:
			raise ValueError(f"Unknown industry: {industry}")
		
		if not vectorstore:
			logger.error(f"Vector store not initialized for industry: {industry}")
			return []
		
		try:
			# Get all documents from the vector store
			results = vectorstore.similarity_search(
				"",  # Empty query to get all documents
				k=top_k * 2  # Get more to filter by time
			)
			
			# Filter by time
			recent_results = []
			for doc in results:
				try:
					published_time = datetime.fromisoformat(doc.metadata['published_at'].replace('Z', '+00:00'))
					if published_time >= cutoff_time:
						recent_results.append({
							'content': doc.page_content,
							'metadata': doc.metadata,
							'distance': None
						})
				except Exception as e:
					logger.error(f"Error parsing date for document: {e}")
					# Include documents with date parsing errors
					recent_results.append({
						'content': doc.page_content,
						'metadata': doc.metadata,
						'distance': None
					})
			
			# Return top_k most recent results
			return recent_results[:top_k]
			
		except Exception as e:
			logger.error(f"Error searching recent news: {e}")
			return []

	def get_collection_stats(self) -> Dict[str, Any]:
		"""Get statistics about the collections"""
		if not self.client:
			return {
				'defense_chunks': 0,
				'semiconductor_chunks': 0,
				'total_chunks': 0,
				'persist_directory': self.persist_directory,
				'embedding_model': self.embedding_model,
				'distance_metric': self.distance_metric
			}
		
		try:
			# Get collection info from Qdrant
			defense_info = self.client.get_collection("defense_news")
			semiconductor_info = self.client.get_collection("semiconductor_news")
			
			defense_count = defense_info.points_count if defense_info else 0
			semiconductor_count = semiconductor_info.points_count if semiconductor_info else 0
			
			return {
				'defense_chunks': defense_count,
				'semiconductor_chunks': semiconductor_count,
				'total_chunks': defense_count + semiconductor_count,
				'persist_directory': self.persist_directory,
				'embedding_model': self.embedding_model,
				'distance_metric': self.distance_metric
			}
		except Exception as e:
			logger.error(f"Error getting collection stats: {e}")
			return {
				'defense_chunks': 0,
				'semiconductor_chunks': 0,
				'total_chunks': 0,
				'persist_directory': self.persist_directory,
				'embedding_model': self.embedding_model,
				'distance_metric': self.distance_metric
			}

	def clear_collections(self) -> None:
		"""Clear all collections (use with caution)"""
		if not self.client:
			logger.error("Qdrant client not initialized")
			return
		
		try:
			# Delete existing collections
			self.client.delete_collection("defense_news")
			self.client.delete_collection("semiconductor_news")
			
			# Recreate collections with proper vector configuration
			if self.embeddings:
				vector_size = 1536  # OpenAI text-embedding-ada-002 dimension
				
				self.client.create_collection(
					name="defense_news",
					vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
				)
				
				self.client.create_collection(
					name="semiconductor_news",
					vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
				)
				
				# Re-initialize LangChain vector stores
				self.defense_vectorstore = Qdrant(
					client=self.client,
					collection_name="defense_news",
					embeddings=self.embeddings
				)
				
				self.semiconductor_vectorstore = Qdrant(
					client=self.client,
					collection_name="semiconductor_news",
					embeddings=self.embeddings
				)
				
				logger.info("Collections cleared and recreated, LangChain Qdrant vector stores re-initialized")
			else:
				logger.error("Cannot recreate collections without embeddings")
		except Exception as e:
			logger.error(f"Failed to clear and recreate collections: {e}")
			self.defense_vectorstore = None
			self.semiconductor_vectorstore = None 