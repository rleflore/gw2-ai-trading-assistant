"""Ingest the static knowledge base into the vector store.

Usage:
    python scripts/ingest_knowledge_base.py
"""

import logging
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent / "src"))

from gw2trading.rag.ingestion import DocumentIngester
from gw2trading.rag.vectorstore import VectorStore
from gw2trading.utils.logging import setup_logging

logger = logging.getLogger("gw2trading")


def main() -> None:
    setup_logging()

    logger.info("Ingesting knowledge base documents...")
    ingester = DocumentIngester()
    documents = ingester.ingest_knowledge_base()
    logger.info(f"Chunked knowledge base into {len(documents)} documents")

    if not documents:
        logger.warning("No knowledge base documents found. Check data/knowledge_base/")
        return

    store = VectorStore()
    added = store.add_documents(documents)
    logger.info(f"Added {added} new documents to vector store")

    stats = store.get_stats()
    logger.info(f"Vector store stats: {stats}")


if __name__ == "__main__":
    main()
