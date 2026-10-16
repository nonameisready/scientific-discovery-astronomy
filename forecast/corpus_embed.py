"""Embed every subfield-classified paper (title + abstract) once.

Writes ``data/raw/embeddings/{year}.npz`` with ``ids`` and float16 unit
vectors (text-embedding-3-small, 1536-d). Not committed (large); rebuilt
deterministically from the corpus. Resumable per year.

Usage:
    python -m forecast.corpus_embed
"""

from __future__ import annotations

import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from forecast.common import ROOT

from pipeline import corpus  # noqa: E402

OUT = ROOT / "data" / "raw" / "embeddings"
MODEL = "text-embedding-3-small"
BATCH = 200
MAX_CHARS = 2000


def _embed_batch(texts: list[str]) -> np.ndarray:
    from openai import OpenAI

    client = OpenAI()
    for attempt in range(8):
        try:
            resp = client.embeddings.create(model=MODEL, input=texts)
            return np.array([d.embedding for d in resp.data], dtype=np.float32)
        except Exception:  # noqa: BLE001
            import time

            time.sleep(2 ** attempt)
    raise RuntimeError("embedding batch failed")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    by_year: dict[int, list[tuple[str, str]]] = defaultdict(list)
    for rec in corpus.iter_processed():
        if rec["subfields"]:
            by_year[rec["year"]].append((rec["id"], f"{rec['title']}. {rec['abstract']}"[:MAX_CHARS]))
    for year in sorted(by_year):
        path = OUT / f"{year}.npz"
        if path.exists():
            continue
        items = by_year[year]
        batches = [items[i : i + BATCH] for i in range(0, len(items), BATCH)]
        with ThreadPoolExecutor(max_workers=8) as pool:
            vecs = list(pool.map(lambda b: _embed_batch([t for _, t in b]), batches))
        X = np.vstack(vecs)
        X /= np.linalg.norm(X, axis=1, keepdims=True)
        np.savez(path, ids=np.array([i for i, _ in items]), X=X.astype(np.float16))
        print(f"[embed] {year}: {len(items)} papers", flush=True)
    (OUT / "manifest.json").write_text(json.dumps(
        {"model": MODEL, "max_chars": MAX_CHARS, "years": {y: len(v) for y, v in sorted(by_year.items())}}, indent=2))


if __name__ == "__main__":
    main()
