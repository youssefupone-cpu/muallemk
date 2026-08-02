"""محرك RAG — فهرسة واسترجاع عبر LanceDB + LlamaIndex/المكوّنات.

التدفق: مستند → تقطيع عربي → تطبيع → تضمين (bge-m3 عبر Ollama) → LanceDB.
استعلام: تطبيع → تضمين → بحث متجهي → نتائج مرتبة بالمسافة (م6).
إعادة الترتيب (Rerank) اختيارية وتُطبَّق خارج هذا المحرّك بلا فشل — انظر
app/rag/reranker.py. المحرّك نفسه متوافق مع بحث متجهي فقط.
"""

from __future__ import annotations

import logging
from pathlib import Path

import lancedb
import pyarrow as pa

from app.rag.chunker import chunk_index_text
from app.rag.embeddings import BaseEmbedder, OllamaEmbedder
from app.rag.normalize import normalize_arabic

logger = logging.getLogger(__name__)


def _schema(dim: int) -> pa.Schema:
    """مخطط LanceDB بعمود متجه FixedSizeList بالبعد الفعلي."""
    return pa.schema(
        [
            pa.field("id", pa.int64()),
            pa.field("document_id", pa.int64()),
            pa.field("filename", pa.string()),
            pa.field("heading", pa.string()),
            pa.field("text", pa.string()),
            pa.field("vector", pa.list_(pa.float32(), list_size=dim)),
        ]
    )


class RAGEngine:
    def __init__(
        self,
        uri: str | Path,
        table_name: str = "documents",
        embedder: BaseEmbedder | None = None,
        top_k: int = 8,
    ):
        self.uri = str(uri)
        self.table_name = table_name
        self.embedder = embedder
        self.top_k = top_k
        self._db: lancedb.DBConnection | None = None
        self._next_id = 1
        self._dim: int | None = None

    @property
    def db(self) -> lancedb.DBConnection:
        if self._db is None:
            self._db = lancedb.connect(self.uri)
        return self._db

    def _table(self):
        return self.db.open_table(self.table_name)

    def _ensure_embedder(self) -> BaseEmbedder:
        if self.embedder is None:
            self.embedder = OllamaEmbedder()
        return self.embedder

    def _ensure_table(self):
        if self._dim is None:
            raise ValueError("البعد غير محدد — استدعِ index قبل إنشاء الجدول")
        tables = list(self.db.list_tables().tables)
        if self.table_name in tables:
            return
        self.db.create_table(self.table_name, schema=_schema(self._dim))

    async def index_document(self, document_id: int, filename: str, content: str) -> dict:
        """يرى المستند ويbuilt chunks ويخزن التضمينات في LanceDB."""
        await self._remove_document(document_id)
        chunks = chunk_index_text(content)
        if not chunks:
            return {"document_id": document_id, "indexed": 0}

        embedder = self._ensure_embedder()
        embeds = await embedder.embed(chunks)
        self._dim = embedder.dim or len(embeds[0])

        rows = []
        for i, (text, vec) in enumerate(zip(chunks, embeds, strict=True)):
            heading = text.splitlines()[0][2:] if text.startswith("# ") else ""
            rows.append(
                {
                    "id": self._next_id + i,
                    "document_id": document_id,
                    "filename": filename,
                    "heading": heading,
                    "text": text,
                    "vector": vec,
                }
            )
        self._next_id += len(rows)

        self._ensure_table()
        self._table().add(rows)
        return {"document_id": document_id, "indexed": len(rows), "dim": self._dim}

    @staticmethod
    def _has_table(db) -> bool:
        return "documents" in db.list_tables().tables

    async def _remove_document(self, document_id: int) -> None:
        if not self._has_table(self.db):
            return
        tbl = self.db.open_table(self.table_name)
        tbl.delete(f"document_id = {document_id}")

    async def remove_document(self, document_id: int) -> None:
        await self._remove_document(document_id)

    async def query(self, question: str, top_k: int | None = None) -> list[dict]:
        """يبحث في المتجهات ويُرجع أجزاء مرتبة في المسافة."""
        if not self._has_table(self.db):
            return []

        embedder = self._ensure_embedder()
        q_norm = normalize_arabic(question)
        (q_vec,) = await embedder.embed([q_norm])
        k = top_k or self.top_k

        tbl = self._table()
        result = (
            tbl.search(q_vec)
            .limit(k * 2)
            .select(["id", "document_id", "filename", "heading", "text"])
            .to_list()
        )
        return [
            {
                "document_id": r["document_id"],
                "filename": r["filename"],
                "heading": r["heading"],
                "text": r["text"],
                "score": float(r.get("_distance", 1e9)),
            }
            for r in result[:k]
        ]


def build_engine(
    data_dir: str | Path,
    embedder: BaseEmbedder | None = None,
    top_k: int = 8,
) -> RAGEngine:
    """يبني محرك RAG بالترتيب الافتراضي (bge-m3 عبر Ollama محلياً)."""
    return RAGEngine(
        uri=Path(data_dir) / "lancedb",
        embedder=embedder or OllamaEmbedder(),
        top_k=top_k,
    )
