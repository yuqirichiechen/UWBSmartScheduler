"""Vector store management for course embeddings."""
import logging
from typing import List, Dict, Optional, Tuple
import json

logger = logging.getLogger(__name__)


class VectorStore:
    """Manages vector embeddings using Pinecone or similar."""
    
    def __init__(self, api_key: Optional[str] = None, environment: Optional[str] = None, 
                 index_name: str = "uwbothell-courses"):
        """Initialize vector store.
        
        Args:
            api_key: Pinecone API key
            environment: Pinecone environment
            index_name: Name of the index
        """
        self.api_key = api_key
        self.environment = environment
        self.index_name = index_name
        self.index = None
        self.mock_embeddings = {}  # In-memory storage for mock/testing
        
        if api_key and environment:
            self._initialize_pinecone()
        else:
            logger.warning("Pinecone credentials not provided, using in-memory mock storage")
    
    def _initialize_pinecone(self):
        """Initialize Pinecone client.

        Supports the modern v3+ client (`from pinecone import Pinecone`) and
        falls back to the legacy v2 `pinecone.init()` API for environments
        still pinned to the older release.
        """
        try:
            # Modern v3+ API
            try:
                from pinecone import Pinecone, ServerlessSpec  # type: ignore

                client = Pinecone(api_key=self.api_key)
                existing = [idx["name"] for idx in client.list_indexes()]
                if self.index_name not in existing:
                    logger.info(f"Creating Pinecone index: {self.index_name}")
                    client.create_index(
                        name=self.index_name,
                        dimension=1536,
                        metric="cosine",
                        spec=ServerlessSpec(
                            cloud="aws",
                            region=self.environment or "us-east-1",
                        ),
                    )
                self.index = client.Index(self.index_name)
                logger.info(f"Connected to Pinecone (v3) index: {self.index_name}")
                return
            except ImportError:
                pass  # fall through to legacy
            except AttributeError:
                pass  # fall through to legacy

            # Legacy v2 API
            import pinecone  # type: ignore
            pinecone.init(api_key=self.api_key, environment=self.environment)
            if self.index_name not in pinecone.list_indexes():
                logger.info(f"Creating Pinecone (legacy) index: {self.index_name}")
                pinecone.create_index(
                    name=self.index_name,
                    dimension=1536,
                    metric="cosine",
                )
            self.index = pinecone.Index(self.index_name)
            logger.info(f"Connected to Pinecone (legacy) index: {self.index_name}")
        except ImportError:
            logger.warning("Pinecone not installed, using in-memory storage")
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone: {e}")
            logger.info("Falling back to in-memory storage")

    @property
    def is_mock(self) -> bool:
        """Returns True if the store is using the in-memory mock."""
        return self.index is None
    
    def upsert_embeddings(self, vectors: List[Tuple[str, List[float], Dict]]) -> bool:
        """Store or update embeddings.
        
        Args:
            vectors: List of (id, embedding_vector, metadata) tuples
            
        Returns:
            True if successful
        """
        if not vectors:
            logger.warning("No vectors to upsert")
            return False
        
        try:
            if self.index:
                # Use Pinecone
                formatted_vectors = [
                    (id_str, embedding, metadata)
                    for id_str, embedding, metadata in vectors
                ]
                self.index.upsert(vectors=formatted_vectors)
                logger.info(f"Upserted {len(vectors)} vectors to Pinecone")
            else:
                # Use mock storage
                for id_str, embedding, metadata in vectors:
                    self.mock_embeddings[id_str] = {
                        'vector': embedding,
                        'metadata': metadata
                    }
                logger.info(f"Stored {len(vectors)} vectors in mock storage")
            
            return True
        except Exception as e:
            logger.error(f"Failed to upsert embeddings: {e}")
            return False
    
    def query(self, query_vector: List[float], top_k: int = 5, 
              filter_metadata: Optional[Dict] = None) -> List[Dict]:
        """Query vector store for similar courses.
        
        Args:
            query_vector: Query embedding vector
            top_k: Number of top results to return
            filter_metadata: Optional metadata filter
            
        Returns:
            List of matching courses with scores
        """
        if not query_vector:
            logger.warning("Empty query vector")
            return []
        
        try:
            if self.index:
                # Use Pinecone — response shape differs between v2 (dict) and
                # v3 (QueryResponse object); normalize both.
                results = self.index.query(
                    vector=query_vector,
                    top_k=top_k,
                    include_metadata=True
                )
                raw_matches = (
                    results.get('matches', []) if isinstance(results, dict)
                    else getattr(results, 'matches', []) or []
                )

                matches = []
                for match in raw_matches:
                    md = match.get('metadata', {}) if isinstance(match, dict) else (getattr(match, 'metadata', {}) or {})
                    mid = match['id'] if isinstance(match, dict) else getattr(match, 'id', None)
                    score = match['score'] if isinstance(match, dict) else getattr(match, 'score', 0.0)
                    matches.append({
                        'id': mid,
                        'score': score,
                        'course_code': md.get('course_code'),
                        'course_title': md.get('course_title'),
                        'section': md.get('section'),
                        'metadata': md,
                    })

                logger.info(f"Query returned {len(matches)} results from Pinecone")
                return matches
            else:
                # Use mock storage
                return self._mock_query(query_vector, top_k, filter_metadata)
        
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return []
    
    def _mock_query(self, query_vector: List[float], top_k: int, 
                   filter_metadata: Optional[Dict] = None) -> List[Dict]:
        """Mock query using in-memory storage (similarity search).
        
        Args:
            query_vector: Query vector
            top_k: Number of results
            filter_metadata: Optional metadata filter
            
        Returns:
            List of matching results
        """
        try:
            import numpy as np
            
            query_vec = np.array(query_vector)
            results = []
            
            for id_str, data in self.mock_embeddings.items():
                stored_vec = np.array(data['vector'])
                # Cosine similarity
                norm_query = np.linalg.norm(query_vec)
                norm_stored = np.linalg.norm(stored_vec)
                
                if norm_query > 0 and norm_stored > 0:
                    similarity = np.dot(query_vec, stored_vec) / (norm_query * norm_stored)
                    
                    metadata = data['metadata']
                    
                    # Apply metadata filter if provided
                    if filter_metadata:
                        if not self._matches_filter(metadata, filter_metadata):
                            continue
                    
                    results.append({
                        'id': id_str,
                        'score': float(similarity),
                        'course_code': metadata.get('course_code'),
                        'course_title': metadata.get('course_title'),
                        'section': metadata.get('section'),
                        'metadata': metadata
                    })
            
            # Sort by score descending and return top_k
            results = sorted(results, key=lambda x: x['score'], reverse=True)[:top_k]
            logger.info(f"Mock query returned {len(results)} results")
            return results
        
        except ImportError:
            logger.error("NumPy required for mock similarity search")
            return []
    
    def _matches_filter(self, metadata: Dict, filter_metadata: Dict) -> bool:
        """Check if metadata matches filter criteria.
        
        Args:
            metadata: Metadata to check
            filter_metadata: Filter criteria
            
        Returns:
            True if matches
        """
        for key, value in filter_metadata.items():
            if metadata.get(key) != value:
                return False
        return True
    
    def delete_embedding(self, vector_id: str) -> bool:
        """Delete a single embedding.
        
        Args:
            vector_id: ID of vector to delete
            
        Returns:
            True if successful
        """
        try:
            if self.index:
                self.index.delete(ids=[vector_id])
            else:
                if vector_id in self.mock_embeddings:
                    del self.mock_embeddings[vector_id]
            
            logger.info(f"Deleted embedding: {vector_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete embedding: {e}")
            return False
    
    def clear_index(self) -> bool:
        """Clear all embeddings from index.
        
        Args:
            
        Returns:
            True if successful
        """
        try:
            if self.index:
                self.index.delete(delete_all=True)
            else:
                self.mock_embeddings.clear()
            
            logger.info("Cleared all embeddings")
            return True
        except Exception as e:
            logger.error(f"Failed to clear index: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """Get index statistics.
        
        Returns:
            Statistics dictionary
        """
        try:
            if self.index:
                stats = self.index.describe_index_stats()
                # v2 returns dict, v3 returns IndexDescription
                if isinstance(stats, dict):
                    vc = stats.get('total_vector_count', 0)
                    dim = stats.get('dimension', 1536)
                else:
                    vc = getattr(stats, 'total_vector_count', 0)
                    dim = getattr(stats, 'dimension', 1536)
                return {
                    'index_name': self.index_name,
                    'vector_count': vc,
                    'dimension': dim,
                    'storage_backend': 'pinecone',
                }
            else:
                return {
                    'index_name': self.index_name,
                    'vector_count': len(self.mock_embeddings),
                    'dimension': 1536,
                    'storage_backend': 'mock'
                }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}
