"""Vector store wrapper for ChromaDB.

Stores document embeddings with metadata for semantic retrieval.
Uses Ollama's embedding model for local embeddings.
"""

import logging
from pathlib import Path

import hashlib
import chromadb
import ollama

from gw2trading.config import DATA_DIR
from gw2trading.rag.ingestion import Document

logger = logging.getLogger("gw2trading.rag.vectorstore")

COLLECTION_NAME = "gw2_documents"
EMBEDDING_MODEL = "nomic-embed-text"  # Local embedding model via Ollama
CHROMA_PATH = DATA_DIR / "chromadb"


class VectorStore:
    """ChromaDB wrapper for storing and querying document embeddings."""

    def __init__(self) -> None:
        self._client: chromadb.PersistentClient | None = None
        self._collection: chromadb.Collection | None = None

    def _get_collection(self) -> chromadb.Collection:
        """Get or create the ChromaDB collection.

        Uses persistent storage at data/chromadb/
        """
        
        path=str(CHROMA_PATH)
        if self._collection is None:
            self._client = chromadb.PersistentClient(path=path)
            self._collection = self._client.get_or_create_collection(name=COLLECTION_NAME)
        return self._collection

    def add_documents(self, documents: list[Document]) -> int:
        """Embed and store documents in ChromaDB.
        Skips documents that already exist (by ID).
        Returns the number of new documents added.
        """
        collection = self._get_collection()
        added = 0
        for doc in documents:
            doc_id = self._generate_doc_id(doc)
            existing = collection.get(ids=[doc_id])
            if existing["ids"]:
                logger.debug(f"Document with ID {doc_id} already exists, skipping")
                continue
            embedding = self._embed_texts([doc.text])[0]
            collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[doc.text],
                metadatas=[doc.metadata]
            )
            added += 1
        return added

    def query(
        self,
        query_text: str,
        n_results: int = 5,
        source_type: str | None = None,
        since_date: str | None = None,
    ) -> list[dict]:
        """Query the vector store for relevant documents.

        Args:
            query_text: The search query
            n_results: Number of results to return
            source_type: Filter by "patch_note" or "reddit_post" (optional)
            since_date: Only return docs newer than this date YYYY-MM-DD (optional)

        Returns list of dicts with keys: text, metadata, distance
        """
        
        embedded = self._embed_texts([query_text])
        where_filter = None
        if source_type and since_date:
            where_filter = {"$and": [{"source_type": source_type}, {"date": {"$gte": since_date}}]}
        elif source_type:
            where_filter = {"source_type": source_type}
        elif since_date:
            where_filter = {"date": {"$gte": since_date}}

        collection = self._get_collection()
        kwargs = {"query_embeddings": embedded, "n_results": n_results}
        if where_filter:
            kwargs["where"] = where_filter
        results = collection.query(**kwargs)
        parsed_results = []
        for text, metadata, distance in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
            parsed_results.append({
                "text": text,
                "metadata": metadata,
                "distance": distance
            })
        
        sorted_results = sorted(parsed_results, key=lambda x: x["distance"])
        return sorted_results
    

    def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings using Ollama's local embedding model. """
        
        embeddings = []
        for text in texts:
            response = ollama.embed(model=EMBEDDING_MODEL, input=text)
            embeddings.append(response["embeddings"][0])
        return embeddings

    def _generate_doc_id(self, doc: Document) -> str:
        """Generate a unique ID for a document based on content + metadata. """

        context = doc.metadata.get("source_type", "") + doc.metadata.get("date", "") + doc.text
        return hashlib.sha256(context.encode()).hexdigest()[:16]


    def get_stats(self) -> dict:
        """Return stats about the vector store.

        Returns dict with: total_documents, source_counts
        """
        # TODO:
        # collection = self._get_collection()
        # total = collection.count()
        # Return {"total_documents": total}
        
        collection = self._get_collection()
        total = collection.count()
        source_counts = {}
        for doc in collection.get(include=["metadatas"])["metadatas"]:
            source_type = doc.get("source_type", "unknown")
            source_counts[source_type] = source_counts.get(source_type, 0) + 1
        return {
            "total_documents": total,
            "source_counts": source_counts
        }



    def clear(self) -> None:
        """Delete all documents from the collection. Use with caution."""

        if self._client:
            self._client.delete_collection(name=COLLECTION_NAME)
            self._collection = None

