import chromadb
from app.config import settings


class ChromaDBManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.client = chromadb.PersistentClient(path=settings.chromadb_path)
            cls._instance._ensure_collections()
        return cls._instance

    def _ensure_collections(self):
        for name in ["agent_memory", "strategy_templates", "alchemy_memory", "alchemy_cache"]:
            try:
                self.client.get_collection(name)
            except (ValueError, chromadb.errors.NotFoundError):
                self.client.create_collection(name)

    def store_memory(self, collection: str, memory_id: str, text: str, metadata: dict | None = None):
        col = self.client.get_collection(collection)
        col.add(documents=[text], ids=[memory_id], metadatas=[metadata or {}])

    def recall_similar(self, collection: str, query: str, n_results: int = 5) -> list[dict]:
        col = self.client.get_collection(collection)
        results = col.query(query_texts=[query], n_results=n_results)
        if not results["ids"][0]:
            return []
        return [
            {"id": results["ids"][0][i], "text": results["documents"][0][i], "metadata": results["metadatas"][0][i]}
            for i in range(len(results["ids"][0]))
        ]

    def delete_memory(self, collection: str, memory_id: str):
        col = self.client.get_collection(collection)
        col.delete(ids=[memory_id])
