"""Document ingestion and chunking for the RAG pipeline.

Loads patch notes and Reddit posts from SQLite, chunks them into
embeddable documents with metadata, and prepares them for the vector store.
Also handles static knowledge base documents from data/knowledge_base/.
"""

import logging
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path

from gw2trading.config import DATA_DIR
from gw2trading.db.database import get_connection

KNOWLEDGE_BASE_DIR = DATA_DIR / "knowledge_base"

logger = logging.getLogger("gw2trading.rag.ingestion")


@dataclass
class Document:
    """A single chunk ready for embedding."""

    text: str
    metadata: dict = field(default_factory=dict)
    # metadata keys: source_type, date, title, source_url


class DocumentIngester:
    """Loads raw data from SQLite and produces chunked Documents."""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 100) -> None:
        self.chunk_size = chunk_size  # approximate token count per chunk
        self.chunk_overlap = chunk_overlap

    def ingest_all(self, since: str | None = None) -> list[Document]:
        """Load and chunk all sources. Returns list of Documents."""
        
        patch_notes = self._load_patch_notes(since)
        reddit_posts = self._load_reddit_posts(since)
        knowledge_docs = self._load_knowledge_base()
        documents = []
        for note in patch_notes:
            documents.extend(self._chunk_patch_note(note))
        for post in reddit_posts:
            documents.extend(self._chunk_reddit_post(post))
        for kb_doc in knowledge_docs:
            documents.extend(self._chunk_knowledge_doc(kb_doc))

        return documents

    def ingest_knowledge_base(self) -> list[Document]:
        """Load and chunk only the static knowledge base documents."""
        knowledge_docs = self._load_knowledge_base()
        documents = []
        for kb_doc in knowledge_docs:
            documents.extend(self._chunk_knowledge_doc(kb_doc))
        return documents
        

    def _load_patch_notes(self, since: str | None = None) -> list[dict]:
        """Load patch notes from the database.

        Returns list of dicts with keys: date, title, full_text, source_url
        """
       
        results = []
        conn = get_connection()
        cursor = conn.cursor()

        query = "SELECT date, title, full_text, source_url FROM patch_notes"
        params = []
        if since:
            query += " WHERE date > ?"
            params.append(since)
        query += " ORDER BY date DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        for row in rows:
            results.append({
                "date": row[0],
                "title": row[1],
                "full_text": row[2],
                "source_url": row[3]
            })
        conn.close()
        return results


    def _load_reddit_posts(self, since: str | None = None) -> list[dict]:
        """Load reddit posts from the database.

        Returns list of dicts with keys: post_id, title, body, timestamp, url
        """
        results = []
        conn = get_connection()
        cursor = conn.cursor()
        query = "SELECT post_id, title, body, timestamp, url FROM reddit_posts"
        params = []
        if since:
            query += " WHERE timestamp > ?"
            params.append(since)
        query += " ORDER BY timestamp DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        for row in rows:
            results.append({
                "post_id": row[0],
                "title": row[1],
                "body": row[2],
                "timestamp": row[3],
                "url": row[4]
            })
        conn.close()
        return results


    def _chunk_patch_note(self, note: dict) -> list[Document]:
        """Chunk a single patch note into Documents."""

        metadata = {
            "source_type": "patch_note",
            "date": note["date"],
            "title": note["title"],
            "source_url": note["source_url"]
        }

        text = note["title"] + "\n\n" + note["full_text"]
        if self._estimate_tokens(text) <= self.chunk_size:
            return [Document(text=text, metadata=metadata)]
        else:
            chunks = self._split_text(text)
            return [Document(text=chunk, metadata=metadata) for chunk in chunks]
        
        

    def _chunk_reddit_post(self, post: dict) -> list[Document]:
        """Chunk a single Reddit post into Documents."""

        metadata = {
            "source_type": "reddit_post",
            "date": post["timestamp"][:10], 
            "title": post["title"],
            "source_url": post["url"]
        }
        body = post["body"] or ""
        text = post["title"] + "\n\n" + body
        if self._estimate_tokens(text) <= self.chunk_size:
            return [Document(text=text, metadata=metadata)]
        else:
            chunks = self._split_text(text)
            return [Document(text=chunk, metadata=metadata) for chunk in chunks]
        
        
        

    def _load_knowledge_base(self) -> list[dict]:
        """Load markdown files from the knowledge_base directory.

        Returns list of dicts with keys: filename, title, content
        """
        results = []
        if not KNOWLEDGE_BASE_DIR.exists():
            logger.warning(f"Knowledge base directory not found: {KNOWLEDGE_BASE_DIR}")
            return results

        for md_file in sorted(KNOWLEDGE_BASE_DIR.glob("*.md")):
            content = md_file.read_text(encoding="utf-8")
            title = content.split("\n", 1)[0].lstrip("# ").strip() if content else md_file.stem
            results.append({
                "filename": md_file.name,
                "title": title,
                "content": content,
            })
            logger.debug(f"Loaded knowledge base file: {md_file.name}")

        return results

    def _chunk_knowledge_doc(self, doc: dict) -> list[Document]:
        """Chunk a knowledge base markdown file into Documents.

        Splits on H2 headers (## ) to keep each section as a coherent chunk.
        """
        metadata = {
            "source_type": "knowledge_base",
            "date": "static",
            "title": doc["title"],
            "source_url": f"local://{doc['filename']}",
        }

        sections = self._split_by_headers(doc["content"])
        documents = []
        for section in sections:
            if self._estimate_tokens(section) <= self.chunk_size:
                documents.append(Document(text=section, metadata=metadata.copy()))
            else:
                chunks = self._split_text(section)
                for chunk in chunks:
                    documents.append(Document(text=chunk, metadata=metadata.copy()))
        return documents

    def _split_by_headers(self, text: str) -> list[str]:
        """Split markdown text by H2 headers (##), keeping the header with its content."""
        lines = text.split("\n")
        sections = []
        current_section = []

        for line in lines:
            if line.startswith("## ") and current_section:
                sections.append("\n".join(current_section).strip())
                current_section = [line]
            else:
                current_section.append(line)

        if current_section:
            sections.append("\n".join(current_section).strip())

        return [s for s in sections if s]

    def _split_text(self, text: str) -> list[str]:
        """Split text into chunks of approximately chunk_size tokens with overlap."""

        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = ""
        for para in paragraphs:
            if self._estimate_tokens(current_chunk + para) <= self.chunk_size:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                overlap_chars = self.chunk_overlap * 4
                overlap_text = current_chunk[-overlap_chars:] if current_chunk else ""
                current_chunk = overlap_text + para + "\n\n"
        if current_chunk:
            chunks.append(current_chunk.strip())
        return chunks

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimate: ~4 characters per token for English text."""
        return len(text) // 4
