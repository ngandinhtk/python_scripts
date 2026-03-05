"""
Retrieval service for vector database operations.
"""
import chromadb
import hashlib
from app.core.config import settings
from app.core.logging import logger
from typing import List, Dict, Optional
from fastapi.concurrency import run_in_threadpool


class RetrievalService:
    def __init__(self):
        # Use PersistentClient to save data across restarts
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.collection = None
        self._init_collection()
    
    def _init_collection(self):
        """Initialize or get Chroma collection."""
        try:
            self.collection = self.client.get_or_create_collection(
                name=settings.CHROMA_COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("retrieval.collection_initialized", name=settings.CHROMA_COLLECTION_NAME)
        except Exception as e:
            logger.error("retrieval.init_error", error=str(e))
    
    async def add_documents(self, documents: List[str], metadatas: List[Dict]):
        """Add documents to vector database."""
        try:
            if not self.collection:
                self._init_collection()
            
            # Use content hash for stable, idempotent IDs
            ids = [hashlib.md5(doc.encode()).hexdigest() for doc in documents]
            
            await run_in_threadpool(
                self.collection.add,
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            logger.info("retrieval.documents_added", count=len(documents))
        except Exception as e:
            logger.error("retrieval.add_error", error=str(e))
    
    async def search(
        self, query: str, n_results: int = 5, where: Optional[Dict] = None
    ) -> List[str]:
        """
        Tìm kiếm các tài liệu tương tự trong vector database.
        Trả về một danh sách nội dung các tài liệu.
        """
        try:
            if not self.collection:
                self._init_collection()
            
            # Run blocking I/O in a thread pool
            results = await run_in_threadpool(
                self.collection.query,
                query_texts=[query],
                n_results=n_results,
                where=where or {},
            )
            
            # Trích xuất và chỉ trả về phần văn bản của tài liệu
            return results["documents"][0] if results and results.get("documents") else []
        except Exception as e:
            logger.error("retrieval.search_error", error=str(e))
            return []
    
    async def clear(self):
        """Clear all documents."""
        try:
            if self.collection:
                # Run blocking I/O in a thread pool
                existing_docs = await run_in_threadpool(self.collection.get)
                ids = existing_docs["ids"]
                if ids:
                    await run_in_threadpool(self.collection.delete, ids=ids)
                    logger.info("retrieval.cleared")
        except Exception as e:
            logger.error("retrieval.clear_error", error=str(e))


retrieval_service = RetrievalService()
