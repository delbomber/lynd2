from typing import List
from sqlalchemy.orm import Session
from src.db.models import IRBKnowledgeEntry


class KnowledgeBase:
    def __init__(self, db_session: Session, api_key: str = ""):
        self.db = db_session
        self.api_key = api_key

    def _embed(self, text: str) -> List[float]:
        # Placeholder — replace with real embedding provider (Voyage AI, OpenAI, etc.)
        raise NotImplementedError("Implement with your embedding provider")

    def _store(self, entry: IRBKnowledgeEntry):
        self.db.add(entry)
        self.db.commit()

    def add_entry(self, key: str, content: str, tags: List[str], study_id: str = ""):
        embedding = self._embed(content)
        entry = IRBKnowledgeEntry(
            key=key,
            content=content,
            tags=tags,
            embedding=embedding,
            study_id=study_id,
        )
        self._store(entry)
