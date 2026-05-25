import re
import lancedb
import pyarrow as pa
import json
from app.config import settings

_SAFE_ID_RE = re.compile(r"^[a-zA-Z0-9_\-:.]+$")


def _sanitize_id(value: str) -> str:
    if not _SAFE_ID_RE.match(value):
        raise ValueError(f"Unsafe ID value: {value!r}")
    return value


class LanceDBManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.db = lancedb.connect(settings.lancedb_path)
            cls._instance._ensure_tables()
        return cls._instance

    def _ensure_tables(self):
        tables = self.db.list_tables()
        if "market_vectors" not in tables:
            schema = pa.schema([
                pa.field("id", pa.string()),
                pa.field("market_id", pa.string()),
                pa.field("platform", pa.string()),
                pa.field("embedding", pa.list_(pa.float32(), 384)),
                pa.field("text", pa.string()),
                pa.field("metadata", pa.string()),
            ])
            table = self.db.create_table("market_vectors", schema=schema)
            table.create_index(metric="cosine", num_partitions=256, num_sub_vectors=96, vector_column_name="embedding")
        else:
            table = self.db.open_table("market_vectors")
            existing = [i for i in (table.list_indices() or [])]
            if not existing:
                try:
                    table.create_index(metric="cosine", num_partitions=256, num_sub_vectors=96, vector_column_name="embedding")
                except Exception:
                    pass

    def search_markets(self, query_vector: list[float], filter_ids: list[str] | None = None, top_k: int = 20) -> list[dict]:
        table = self.db.open_table("market_vectors")
        query = table.search(query_vector)
        if filter_ids:
            safe_ids = [_sanitize_id(f) for f in filter_ids]
            ids_str = ",".join(f"'{f}'" for f in safe_ids)
            query = query.where(f"market_id IN ({ids_str})")
        return query.limit(top_k).to_list()

    def upsert_market_vector(self, id: str, market_id: str, platform: str, embedding: list[float], text: str, metadata: dict | None = None):
        table = self.db.open_table("market_vectors")
        table.merge_insert(["id"]).when_matched_update_all().when_not_matched_insert_all().execute([{
            "id": id,
            "market_id": market_id,
            "platform": platform,
            "embedding": embedding,
            "text": text,
            "metadata": json.dumps(metadata or {}),
        }])

    def delete_market_vector(self, id: str):
        table = self.db.open_table("market_vectors")
        table.delete(f"id = '{_sanitize_id(id)}'")
