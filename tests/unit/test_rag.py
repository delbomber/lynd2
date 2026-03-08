from unittest.mock import patch, MagicMock
from src.rag.knowledge_base import KnowledgeBase
from src.rag.retrieval import IRBRetriever


def test_knowledge_base_ingests_content():
    kb = KnowledgeBase(db_session=MagicMock())
    with patch.object(kb, "_embed") as mock_embed, \
         patch.object(kb, "_store") as mock_store:
        mock_embed.return_value = [0.1] * 1536
        kb.add_entry(
            key="age_requirement",
            content="Participants must be between 18 and 70 years old.",
            tags=["eligibility", "age"],
        )
        mock_store.assert_called_once()


def test_retriever_returns_approved_content():
    retriever = IRBRetriever(db_session=MagicMock())
    with patch.object(retriever, "_embed") as mock_embed, \
         patch.object(retriever, "_search") as mock_search:
        mock_embed.return_value = [0.1] * 1536
        mock_search.return_value = [
            {"content": "Participants must be 18-70.", "score": 0.95}
        ]
        results = retriever.search("what is the age requirement?", top_k=1)
        assert len(results) == 1
        assert "18-70" in results[0]["content"]


def test_retriever_returns_empty_for_no_match():
    retriever = IRBRetriever(db_session=MagicMock())
    with patch.object(retriever, "_embed") as mock_embed, \
         patch.object(retriever, "_search") as mock_search:
        mock_embed.return_value = [0.1] * 1536
        mock_search.return_value = []
        results = retriever.search("unrelated query", top_k=1)
        assert results == []
