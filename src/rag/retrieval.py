import logging
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


class IRBRetriever:
    def __init__(self, db_session: Session, api_key: str = ""):
        self.db = db_session
        self.api_key = api_key

    def _embed(self, text_input: str) -> List[float]:
        raise NotImplementedError("Implement with your embedding provider")

    def _search(self, query_embedding: List[float], top_k: int) -> List[dict]:
        result = self.db.execute(
            text("""
                SELECT key, content, tags,
                       1 - (embedding <=> cast(:embedding AS vector)) as score
                FROM irb_knowledge
                ORDER BY embedding <=> cast(:embedding AS vector)
                LIMIT :top_k
            """),
            {"embedding": str(query_embedding), "top_k": top_k},
        )
        return [{"content": row.content, "score": row.score} for row in result]

    def search(self, query: str, top_k: int = 3) -> List[dict]:
        try:
            embedding = self._embed(query)
            return self._search(embedding, top_k)
        except Exception:
            logger.error("RAG search failed", exc_info=True)
            return []
