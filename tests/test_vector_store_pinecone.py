import types

import pytest

import backend.services.vector_store as vector_store_module


class DummySession:
    pass


class FakePineconeIndex:
    def __init__(self):
        self.upsert_calls = []
        self.query_calls = []

    def upsert(self, vectors):
        self.upsert_calls.append(vectors)

    def query(self, vector, top_k=5, include_metadata=True):
        self.query_calls.append({"vector": vector, "top_k": top_k, "include_metadata": include_metadata})
        return {
            "matches": [{"id": "vec-123", "score": 0.92, "metadata": {"text": "hello", "source": "demo"}}]
        }


class FakePinecone:
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.index = FakePineconeIndex()

    def Index(self, name):
        return self.index


@pytest.mark.asyncio
async def test_vector_store_uses_pinecone_when_enabled(monkeypatch):
    monkeypatch.setattr(vector_store_module.settings, "VECTOR_BACKEND", "pinecone", raising=False)
    monkeypatch.setattr(vector_store_module.settings, "PINECONE_API_KEY", "test-key", raising=False)
    monkeypatch.setattr(vector_store_module.settings, "PINECONE_INDEX_NAME", "scam-detector", raising=False)
    monkeypatch.setattr(vector_store_module, "Pinecone", FakePinecone, raising=False)

    store = vector_store_module.VectorStore(DummySession())

    doc = await store.add_document("hello", metadata={"source": "demo"})
    await store.add_embedding(doc.id, [0.1, 0.2])
    matches = await store.search([0.1, 0.2], limit=2)

    assert doc.id == "vec-123" or doc.id is not None
    assert store.pinecone_index is not None
    assert matches[0].metadata["source"] == "demo"
    assert matches[0].text == "hello"
