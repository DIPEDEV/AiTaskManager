from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path


class EmbeddingsIndex:
    """Simple TF-IDF based embedding index for semantic search.

    Uses sklearn-free TF-IDF with cosine similarity.
    For production, could swap to sqlite-vec or OpenAI embeddings.
    """

    def __init__(self, root: Path):
        self.root = root
        self.index_path = root / ".tasks" / "embeddings.json"

    def build_index(self, tasks: list) -> dict:
        """Build embeddings for all tasks."""
        documents = []
        for task in tasks:
            text = f"{task.title} {task.spec} {task.tags} {task.section}"
            documents.append({"id": task.id, "agent": task.agent_type, "text": text})

        if not documents:
            return {}

        corpus = [d["text"] for d in documents]
        vectors = self._tfidf(corpus)

        index = {}
        for doc, vec in zip(documents, vectors):
            index[f"{doc['agent']}:{doc['id']}"] = vec

        return index

    def save_index(self, index: dict) -> None:
        import json
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.index_path, "w") as f:
            json.dump(index, f)

    def load_index(self) -> dict:
        import json
        if not self.index_path.exists():
            return {}
        with open(self.index_path) as f:
            return json.load(f)

    def search(self, query: str, index: dict, top_k: int = 5) -> list[tuple[str, float]]:
        """Search index for query. Returns list of (task_key, score)."""
        if not index:
            return []
        query_vec = self._tfidf([query])[0]
        scores = []
        for key, vec in index.items():
            sim = self._cosine(query_vec, vec)
            scores.append((key, sim))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def _tfidf(self, documents: list[str]) -> list[list[float]]:
        """Simple TF-IDF implementation."""
        docs = [self._tokenize(d) for d in documents]
        vocab = list(set(word for d in docs for word in d))
        idf = self._idf(docs, vocab)

        vectors = []
        for doc_words in docs:
            tf = Counter(doc_words)
            vec = []
            for word in vocab:
                tf_val = tf.get(word, 0)
                vec.append(tf_val * idf.get(word, 0))
            vectors.append(vec)
        return [self._normalize(v) for v in vectors]

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"\w+", text.lower())

    def _idf(self, docs: list[list[str]], vocab: list[str]) -> dict[str, float]:
        N = len(docs)
        idf = {}
        for word in vocab:
            df = sum(1 for d in docs if word in d)
            idf[word] = math.log(N / (df + 1)) + 1
        return idf

    def _normalize(self, vec: list[float]) -> list[float]:
        norm = math.sqrt(sum(x * x for x in vec))
        if norm == 0:
            return vec
        return [x / norm for x in vec]

    def _cosine(self, a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        return dot


__all__ = ["EmbeddingsIndex"]