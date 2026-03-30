"""Semantic memory system using ChromaDB for vectorized situation matching.

Replaces BM25 lexical matching with semantic embeddings:
- Understands that "Powell speaks hawkish" ≈ "Fed signals higher rates"
- Stores metadata for hybrid filtering (ticker, regime, pnl_outcome)
- Persists memory across process restarts via local ChromaDB
"""

import chromadb
from chromadb.config import Settings
from typing import List, Tuple, Dict, Any, Optional
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class VectorizedMemory:
    """Semantic memory system using ChromaDB for financial situation retrieval."""

    def __init__(
        self,
        name: str,
        db_path: str = "./trade_memory/chromadb",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    ):
        """Initialize vectorized memory with persistent ChromaDB.

        Args:
            name: Memory instance name (e.g., 'bull_researcher_memory')
            db_path: Path to persistent ChromaDB storage
            embedding_model: HuggingFace sentence-transformers model for embeddings
        """
        self.name = name
        self.db_path = db_path
        
        # Create persistent ChromaDB client
        Path(db_path).mkdir(parents=True, exist_ok=True)
        
        # Use persistent client for local file storage
        self.client = chromadb.PersistentClient(path=db_path)
        
        # Get or create collection for this memory instance
        # Collection name must be valid: lowercase, 3-63 chars, alphanumeric + underscore/hyphen
        collection_name = f"{name}_situations".replace("_", "_").lower()[:63]
        
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={
                "model": embedding_model,
                "created_at": datetime.utcnow().isoformat(),
            },
        )

        logger.info(f"Initialized VectorizedMemory '{name}' with ChromaDB at {db_path}")

    def add_situations(self, situations_and_advice: List[Tuple[str, str]], metadata_list: Optional[List[Dict[str, Any]]] = None) -> None:
        """Add situations with semantic embeddings and optional metadata.

        Args:
            situations_and_advice: List of (situation_text, recommendation_text) tuples
            metadata_list: Optional list of dicts with ticker, market_regime, pnl_result, etc.
                          If None, defaults are created.
        """
        if not situations_and_advice:
            return

        ids = []
        documents = []
        metadatas = []
        
        for idx, (situation, recommendation) in enumerate(situations_and_advice):
            # Combine situation + recommendation into single document for retrieval
            combined_doc = f"Situation: {situation}\n\nRecommendation: {recommendation}"
            documents.append(combined_doc)
            
            # Use provided metadata or create defaults
            if metadata_list and idx < len(metadata_list):
                meta = metadata_list[idx].copy()
            else:
                meta = {}
            
            # Ensure timestamp is present
            if "timestamp" not in meta:
                meta["timestamp"] = datetime.utcnow().isoformat()
            
            metadatas.append(meta)
            
            # Generate unique ID based on timestamp + index
            doc_id = f"{meta['timestamp']}_{idx}"
            ids.append(doc_id)

        try:
            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
            )
            logger.info(f"Added {len(situations_and_advice)} situations to {self.name} memory")
        except Exception as e:
            logger.error(f"Error adding situations to {self.name}: {e}")

    def get_memories(
        self,
        current_situation: str,
        n_matches: int = 3,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve semantically similar past situations.

        Args:
            current_situation: Current market/portfolio context to match against
            n_matches: Number of top matches to return
            filter_metadata: Optional dict for filtering (e.g., {"ticker": "BTC", "pnl_result": "loss"})

        Returns:
            List of dicts with 'situation', 'recommendation', 'distance', 'metadata'
        """
        if self.collection.count() == 0:
            return []

        try:
            # Query with embedding (ChromaDB handles this automatically)
            results = self.collection.query(
                query_texts=[current_situation],
                n_results=n_matches,
                where=filter_metadata if filter_metadata else None,
            )

            matches = []
            if results and results.get("documents") and len(results["documents"]) > 0:
                for doc, metadata, distance in zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0],
                ):
                    # Parse out situation and recommendation from combined doc
                    parts = doc.split("\n\nRecommendation:")
                    situation = parts[0].replace("Situation: ", "")
                    recommendation = parts[1].strip() if len(parts) > 1 else ""

                    # ChromaDB returns distance (0=perfect match, larger=dissimilar)
                    # Convert to similarity score (0-1, 1=perfect)
                    similarity = 1.0 / (1.0 + distance) if distance >= 0 else 0.0

                    matches.append({
                        "situation": situation,
                        "recommendation": recommendation,
                        "similarity_score": round(similarity, 3),
                        "distance": round(distance, 3),
                        "metadata": metadata,
                    })

            logger.debug(f"Retrieved {len(matches)} matches for {self.name}")
            return matches

        except Exception as e:
            logger.error(f"Error querying {self.name} memory: {e}")
            return []

    def delete_situations(self, where_metadata: Dict[str, Any]) -> None:
        """Delete situations matching metadata filter.

        Args:
            where_metadata: Metadata filter (e.g., {"ticker": "BTC"})
        """
        try:
            self.collection.delete(where=where_metadata)
            logger.info(f"Deleted situations from {self.name} with filter {where_metadata}")
        except Exception as e:
            logger.error(f"Error deleting situations from {self.name}: {e}")

    def list_all_situations(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List all stored situations (for inspection/audit).

        Args:
            limit: Maximum number to return

        Returns:
            List of dicts with situation, recommendation, metadata
        """
        if self.collection.count() == 0:
            return []

        try:
            # Get all documents without query (ChromaDB limitation: need to use get())
            results = self.collection.get(limit=limit)
            
            situations = []
            if results and results.get("documents"):
                for doc, metadata in zip(results["documents"], results["metadatas"]):
                    parts = doc.split("\n\nRecommendation:")
                    situation = parts[0].replace("Situation: ", "")
                    recommendation = parts[1].strip() if len(parts) > 1 else ""

                    situations.append({
                        "situation": situation,
                        "recommendation": recommendation,
                        "metadata": metadata,
                    })

            return situations
        except Exception as e:
            logger.error(f"Error listing situations from {self.name}: {e}")
            return []

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics.

        Returns:
            Dict with count, model info, creation timestamp
        """
        try:
            count = self.collection.count()
            metadata = self.collection.metadata
            
            return {
                "name": self.name,
                "count": count,
                "embedding_model": metadata.get("model", "unknown"),
                "created_at": metadata.get("created_at", "unknown"),
            }
        except Exception as e:
            logger.error(f"Error getting stats for {self.name}: {e}")
            return {}


# Backward compatibility: FinancialSituationMemory as alias
class FinancialSituationMemory(VectorizedMemory):
    """Backward-compatible alias for VectorizedMemory.
    
    This maintains API compatibility with existing code that uses
    FinancialSituationMemory while leveraging ChromaDB backend.
    """
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """Backward-compatible initializer.

        Historical call sites pass a config dict as the second argument.
        We accept it and optionally read an override path from config.
        """
        db_path = "./trade_memory/chromadb"
        if isinstance(config, dict):
            db_path = (
                config.get("memory_db_path")
                or config.get("trade_memory_path")
                or db_path
            )
        super().__init__(name=name, db_path=db_path)
