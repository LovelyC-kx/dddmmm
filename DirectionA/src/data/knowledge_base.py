"""
Financial Knowledge Base (FKB) — Phase 1 of GroundedStock

Four sub-collections:
  1. news_semantic    — 2M+ news docs; FAISS HNSW dense index + BM25 sparse index
  2. event_outcome    — Historical event outcomes with macro regime labels
  3. macro_snapshot   — Daily macroeconomic indicators (VIX, Fed rate, yields, etc.)
  4. fundamental_snapshot — Quarterly fundamental data per ticker

Usage:
    builder = FKBBuilder(config)
    builder.build_from_fnspid(fnspid_path)
    builder.save(output_dir)

    fkb = FKB.load(output_dir)
    results = fkb.search_news("Apple earnings beat", top_k=20)
"""

import json
import math
import os
import pickle
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

# Optional heavy imports — guarded so the file is importable without them
try:
    import faiss
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False

try:
    from rank_bm25 import BM25Okapi
    HAS_BM25 = True
except ImportError:
    HAS_BM25 = False

try:
    from transformers import AutoModel, AutoTokenizer
    import torch
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False


# ──────────────────────────────────────────────────────────────────────────────
# Data classes
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class NewsDoc:
    doc_id: str
    ticker: str
    headline: str
    timestamp: datetime
    source: str = ""
    embedding: Optional[np.ndarray] = None  # shape (768,)


@dataclass
class EventOutcome:
    event_id: str
    ticker: str
    event_type: str          # C1-C8, M1-M6, K1-K4, G1-G2
    headline: str
    timestamp: datetime
    macro_regime: str        # e.g. RATE_HIKE, RATE_CUT, NEUTRAL
    ret_1d: float
    ret_3d: float
    ret_7d: float
    ret_30d: float


@dataclass
class MacroSnapshot:
    date: datetime
    fed_rate: float
    vix: float
    yield_10y: float
    yield_2y: float
    spread_10y_2y: float
    sp500_ret_1m: float
    macro_regime: str        # labeled from the above fields
    regime_description: str


@dataclass
class FundamentalSnapshot:
    ticker: str
    report_date: datetime
    pe_ratio: float
    eps: float
    eps_estimate: float
    revenue: float           # in billions USD
    revenue_growth_yoy: float
    analyst_rating: float    # 1=Strong Buy … 5=Strong Sell
    price_target: float
    market_cap: float        # in billions USD


# ──────────────────────────────────────────────────────────────────────────────
# FinBERT text encoder
# ──────────────────────────────────────────────────────────────────────────────

class FinBERTEncoder:
    """
    Thin wrapper around ProsusAI/finbert (or any HuggingFace sentence encoder).
    Produces L2-normalised 768-dim embeddings suitable for FAISS IP search.
    """

    MODEL_NAME = "ProsusAI/finbert"

    def __init__(self, model_name: str = MODEL_NAME, device: str = "cpu"):
        if not HAS_TRANSFORMERS:
            raise ImportError("transformers + torch required for FinBERTEncoder")
        self.device = device
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name).to(device)
        self.model.eval()

    @torch.no_grad()
    def encode(self, texts: List[str], batch_size: int = 64) -> np.ndarray:
        """
        Returns float32 array of shape (N, 768), L2-normalised.
        """
        all_embs = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            enc = self.tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=128,
                return_tensors="pt",
            ).to(self.device)
            out = self.model(**enc)
            # Mean-pool over token dimension
            emb = out.last_hidden_state.mean(dim=1).cpu().numpy()
            # L2 normalise
            norms = np.linalg.norm(emb, axis=1, keepdims=True)
            emb = emb / np.maximum(norms, 1e-8)
            all_embs.append(emb)
        return np.vstack(all_embs).astype(np.float32)


# ──────────────────────────────────────────────────────────────────────────────
# FAISS index wrapper
# ──────────────────────────────────────────────────────────────────────────────

class FAISSIndex:
    """
    Flat IP index (equivalent to cosine similarity on L2-normalised vectors).
    Use IndexHNSWFlat for large-scale (>500K) datasets.
    """

    def __init__(self, dim: int = 768, use_hnsw: bool = True):
        if not HAS_FAISS:
            raise ImportError("faiss-cpu required for FAISSIndex")
        self.dim = dim
        if use_hnsw:
            self.index = faiss.IndexHNSWFlat(dim, 32)  # 32 neighbours
            self.index.hnsw.efConstruction = 200
        else:
            self.index = faiss.IndexFlatIP(dim)
        self.doc_ids: List[str] = []

    def add(self, embeddings: np.ndarray, doc_ids: List[str]):
        assert embeddings.shape[1] == self.dim
        self.index.add(embeddings.astype(np.float32))
        self.doc_ids.extend(doc_ids)

    def search(self, query: np.ndarray, top_k: int = 50) -> List[Tuple[str, float]]:
        """Returns list of (doc_id, score) sorted by score desc."""
        query = query.reshape(1, -1).astype(np.float32)
        D, I = self.index.search(query, top_k)
        results = []
        for dist, idx in zip(D[0], I[0]):
            if idx < 0:
                continue
            results.append((self.doc_ids[idx], float(dist)))
        return results

    def save(self, path: str):
        faiss.write_index(self.index, path + ".faiss")
        with open(path + ".ids.pkl", "wb") as f:
            pickle.dump(self.doc_ids, f)

    @classmethod
    def load(cls, path: str, dim: int = 768) -> "FAISSIndex":
        obj = cls.__new__(cls)
        obj.dim = dim
        obj.index = faiss.read_index(path + ".faiss")
        with open(path + ".ids.pkl", "rb") as f:
            obj.doc_ids = pickle.load(f)
        return obj


# ──────────────────────────────────────────────────────────────────────────────
# BM25 sparse index
# ──────────────────────────────────────────────────────────────────────────────

class BM25Index:
    """Thin wrapper around rank-bm25 for sparse retrieval."""

    def __init__(self):
        if not HAS_BM25:
            raise ImportError("rank-bm25 required for BM25Index")
        self.bm25: Optional[BM25Okapi] = None
        self.doc_ids: List[str] = []

    def build(self, headlines: List[str], doc_ids: List[str]):
        tokenised = [h.lower().split() for h in headlines]
        self.bm25 = BM25Okapi(tokenised)
        self.doc_ids = doc_ids

    def search(self, query: str, top_k: int = 50) -> List[Tuple[str, float]]:
        tokens = query.lower().split()
        scores = self.bm25.get_scores(tokens)
        top_idx = np.argsort(scores)[::-1][:top_k]
        return [(self.doc_ids[i], float(scores[i])) for i in top_idx]

    def save(self, path: str):
        with open(path + ".bm25.pkl", "wb") as f:
            pickle.dump((self.bm25, self.doc_ids), f)

    @classmethod
    def load(cls, path: str) -> "BM25Index":
        obj = cls.__new__(cls)
        with open(path + ".bm25.pkl", "rb") as f:
            obj.bm25, obj.doc_ids = pickle.load(f)
        return obj


# ──────────────────────────────────────────────────────────────────────────────
# Macro regime labeler
# ──────────────────────────────────────────────────────────────────────────────

def label_macro_regime(fed_rate: float, vix: float,
                       spread_10y_2y: float) -> Tuple[str, str]:
    """
    Simple rule-based regime labelling.
    Returns (regime_label, description).
    """
    if fed_rate >= 4.0:
        regime = "RATE_HIKE"
        desc = ("High-rate environment (Fed ≥4%). Growth stock valuations "
                "under pressure; flight to value.")
    elif fed_rate <= 1.0:
        regime = "RATE_CUT"
        desc = ("Low/zero rate environment (Fed ≤1%). Risk-on; growth "
                "stocks bid up.")
    else:
        regime = "NEUTRAL"
        desc = "Moderate rate environment. Sector rotation driven by earnings."

    if vix >= 30:
        regime += "_VOLATILE"
        desc += " High market fear (VIX≥30); defensive positioning."
    elif vix <= 15:
        regime += "_CALM"
        desc += " Low volatility (VIX≤15); risk appetite elevated."

    if spread_10y_2y < 0:
        desc += " Inverted yield curve — recession signal."

    return regime, desc


# ──────────────────────────────────────────────────────────────────────────────
# SQLite back-end for event_outcome, macro_snapshot, fundamental_snapshot
# ──────────────────────────────────────────────────────────────────────────────

_DDL = """
CREATE TABLE IF NOT EXISTS event_outcome (
    event_id     TEXT PRIMARY KEY,
    ticker       TEXT,
    event_type   TEXT,
    headline     TEXT,
    timestamp    TEXT,
    macro_regime TEXT,
    ret_1d       REAL,
    ret_3d       REAL,
    ret_7d       REAL,
    ret_30d      REAL
);

CREATE TABLE IF NOT EXISTS macro_snapshot (
    date              TEXT PRIMARY KEY,
    fed_rate          REAL,
    vix               REAL,
    yield_10y         REAL,
    yield_2y          REAL,
    spread_10y_2y     REAL,
    sp500_ret_1m      REAL,
    macro_regime      TEXT,
    regime_description TEXT
);

CREATE TABLE IF NOT EXISTS fundamental_snapshot (
    ticker        TEXT,
    report_date   TEXT,
    pe_ratio      REAL,
    eps           REAL,
    eps_estimate  REAL,
    revenue       REAL,
    revenue_growth_yoy REAL,
    analyst_rating REAL,
    price_target  REAL,
    market_cap    REAL,
    PRIMARY KEY (ticker, report_date)
);

CREATE INDEX IF NOT EXISTS idx_eo_ticker_type ON event_outcome(ticker, event_type);
CREATE INDEX IF NOT EXISTS idx_eo_timestamp   ON event_outcome(timestamp);
CREATE INDEX IF NOT EXISTS idx_fs_ticker      ON fundamental_snapshot(ticker);
"""


class FKBDatabase:
    """
    SQLite wrapper for the three structured sub-collections.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.executescript(_DDL)
        self._conn.commit()

    # ── Event outcomes ──────────────────────────────────────────────────────

    def insert_event_outcomes(self, events: List[EventOutcome]):
        rows = [
            (e.event_id, e.ticker, e.event_type, e.headline,
             e.timestamp.isoformat(), e.macro_regime,
             e.ret_1d, e.ret_3d, e.ret_7d, e.ret_30d)
            for e in events
        ]
        self._conn.executemany(
            "INSERT OR REPLACE INTO event_outcome VALUES (?,?,?,?,?,?,?,?,?,?)",
            rows,
        )
        self._conn.commit()

    def query_event_outcomes(
        self,
        event_type: str,
        ticker: str,
        before_timestamp: datetime,
        macro_regime: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict]:
        sql = """
            SELECT * FROM event_outcome
            WHERE event_type = ?
              AND ticker IN (?, 'ALL')
              AND timestamp < ?
            {}
            ORDER BY timestamp DESC
            LIMIT ?
        """.format(
            "AND macro_regime = ?" if macro_regime else ""
        )
        params: list = [event_type, ticker, before_timestamp.isoformat()]
        if macro_regime:
            params.append(macro_regime)
        params.append(limit)
        cur = self._conn.execute(sql, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    # ── Macro snapshots ─────────────────────────────────────────────────────

    def insert_macro_snapshots(self, snapshots: List[MacroSnapshot]):
        rows = [
            (s.date.isoformat(), s.fed_rate, s.vix, s.yield_10y, s.yield_2y,
             s.spread_10y_2y, s.sp500_ret_1m, s.macro_regime,
             s.regime_description)
            for s in snapshots
        ]
        self._conn.executemany(
            "INSERT OR REPLACE INTO macro_snapshot VALUES (?,?,?,?,?,?,?,?,?)",
            rows,
        )
        self._conn.commit()

    def get_macro_snapshot(self, date: datetime) -> Optional[Dict]:
        """Returns the most recent snapshot on or before `date`."""
        cur = self._conn.execute(
            "SELECT * FROM macro_snapshot WHERE date <= ? ORDER BY date DESC LIMIT 1",
            (date.isoformat(),),
        )
        row = cur.fetchone()
        if row is None:
            return None
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))

    # ── Fundamental snapshots ───────────────────────────────────────────────

    def insert_fundamental_snapshots(self, snaps: List[FundamentalSnapshot]):
        rows = [
            (s.ticker, s.report_date.isoformat(), s.pe_ratio, s.eps,
             s.eps_estimate, s.revenue, s.revenue_growth_yoy,
             s.analyst_rating, s.price_target, s.market_cap)
            for s in snaps
        ]
        self._conn.executemany(
            "INSERT OR REPLACE INTO fundamental_snapshot VALUES (?,?,?,?,?,?,?,?,?,?)",
            rows,
        )
        self._conn.commit()

    def get_fundamental_snapshot(
        self, ticker: str, before_date: datetime
    ) -> Optional[Dict]:
        """Most recent quarterly snapshot before `before_date`."""
        cur = self._conn.execute(
            """SELECT * FROM fundamental_snapshot
               WHERE ticker = ? AND report_date <= ?
               ORDER BY report_date DESC LIMIT 1""",
            (ticker, before_date.isoformat()),
        )
        row = cur.fetchone()
        if row is None:
            return None
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))

    def get_historical_pe(
        self, ticker: str, end_date: datetime, years: int = 3
    ) -> Tuple[float, float]:
        """Returns (mean_pe, std_pe) over the past `years` years."""
        start = (end_date - timedelta(days=years * 365)).isoformat()
        cur = self._conn.execute(
            """SELECT pe_ratio FROM fundamental_snapshot
               WHERE ticker = ? AND report_date BETWEEN ? AND ?""",
            (ticker, start, end_date.isoformat()),
        )
        rows = [r[0] for r in cur.fetchall() if r[0] and r[0] > 0]
        if not rows:
            return 20.0, 5.0  # fallback defaults
        arr = np.array(rows)
        return float(arr.mean()), float(arr.std() + 1e-8)

    def close(self):
        self._conn.close()


# ──────────────────────────────────────────────────────────────────────────────
# Main FKB class — ties everything together
# ──────────────────────────────────────────────────────────────────────────────

class FKB:
    """
    Financial Knowledge Base.

    Attributes:
        faiss_idx  — dense FAISS index over news_semantic
        bm25_idx   — sparse BM25 index over news_semantic
        doc_store  — dict mapping doc_id → NewsDoc (in-memory; can be mmap'd)
        db         — FKBDatabase (event_outcome / macro / fundamental)
    """

    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.faiss_idx: Optional[FAISSIndex] = None
        self.bm25_idx: Optional[BM25Index] = None
        self.doc_store: Dict[str, NewsDoc] = {}
        self.db: Optional[FKBDatabase] = None

    # ── Build ────────────────────────────────────────────────────────────────

    def build_news_index(
        self,
        docs: List[NewsDoc],
        encoder: FinBERTEncoder,
        batch_size: int = 256,
    ):
        """Encodes all NewsDoc headlines and builds FAISS + BM25 indices."""
        print(f"Encoding {len(docs):,} documents …")
        headlines = [d.headline for d in docs]
        doc_ids = [d.doc_id for d in docs]

        # Encode in batches
        all_embs = encoder.encode(headlines, batch_size=batch_size)

        # Store embeddings back into docs
        for doc, emb in zip(docs, all_embs):
            doc.embedding = emb
            self.doc_store[doc.doc_id] = doc

        # FAISS index
        self.faiss_idx = FAISSIndex(dim=768, use_hnsw=True)
        self.faiss_idx.add(all_embs, doc_ids)

        # BM25 index
        self.bm25_idx = BM25Index()
        self.bm25_idx.build(headlines, doc_ids)

        print("  FAISS index built:", len(doc_ids), "vectors")
        print("  BM25  index built:", len(doc_ids), "documents")

    def init_db(self):
        self.base_dir.mkdir(parents=True, exist_ok=True)
        db_path = str(self.base_dir / "fkb.sqlite3")
        self.db = FKBDatabase(db_path)

    # ── Search ───────────────────────────────────────────────────────────────

    def hybrid_search(
        self,
        query: str,
        query_emb: np.ndarray,
        before_timestamp: datetime,
        top_k: int = 50,
        rrf_k: int = 60,
    ) -> List[Tuple[str, float]]:
        """
        Reciprocal Rank Fusion over dense + sparse results, filtered by time.
        Returns list of (doc_id, rrf_score) sorted desc.
        """
        dense_results = self.faiss_idx.search(query_emb, top_k=top_k)
        sparse_results = self.bm25_idx.search(query, top_k=top_k)

        # Build rank maps
        dense_rank = {doc_id: rank for rank, (doc_id, _) in enumerate(dense_results)}
        sparse_rank = {doc_id: rank for rank, (doc_id, _) in enumerate(sparse_results)}

        all_ids = set(dense_rank) | set(sparse_rank)
        rrf_scores: Dict[str, float] = {}
        for doc_id in all_ids:
            # Time filter
            doc = self.doc_store.get(doc_id)
            if doc is None or doc.timestamp >= before_timestamp:
                continue
            r_d = dense_rank.get(doc_id, top_k)
            r_s = sparse_rank.get(doc_id, top_k)
            rrf_scores[doc_id] = 1.0 / (rrf_k + r_d) + 1.0 / (rrf_k + r_s)

        return sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

    # ── Persist ──────────────────────────────────────────────────────────────

    def save(self):
        self.base_dir.mkdir(parents=True, exist_ok=True)
        prefix = str(self.base_dir / "news_index")
        if self.faiss_idx:
            self.faiss_idx.save(prefix)
        if self.bm25_idx:
            self.bm25_idx.save(prefix)
        # Save doc_store (without embeddings to save disk)
        meta = {
            doc_id: {
                "ticker": d.ticker,
                "headline": d.headline,
                "timestamp": d.timestamp.isoformat(),
                "source": d.source,
            }
            for doc_id, d in self.doc_store.items()
        }
        with open(str(self.base_dir / "doc_meta.json"), "w") as f:
            json.dump(meta, f)
        print(f"FKB saved to {self.base_dir}")

    @classmethod
    def load(cls, base_dir: str) -> "FKB":
        obj = cls(base_dir)
        prefix = str(Path(base_dir) / "news_index")
        if HAS_FAISS and Path(prefix + ".faiss").exists():
            obj.faiss_idx = FAISSIndex.load(prefix)
        if HAS_BM25 and Path(prefix + ".bm25.pkl").exists():
            obj.bm25_idx = BM25Index.load(prefix)
        meta_path = Path(base_dir) / "doc_meta.json"
        if meta_path.exists():
            with open(meta_path) as f:
                meta = json.load(f)
            obj.doc_store = {
                doc_id: NewsDoc(
                    doc_id=doc_id,
                    ticker=v["ticker"],
                    headline=v["headline"],
                    timestamp=datetime.fromisoformat(v["timestamp"]),
                    source=v.get("source", ""),
                )
                for doc_id, v in meta.items()
            }
        db_path = str(Path(base_dir) / "fkb.sqlite3")
        if Path(db_path).exists():
            obj.db = FKBDatabase(db_path)
        return obj


# ──────────────────────────────────────────────────────────────────────────────
# FKBBuilder — builds FKB from raw data files
# ──────────────────────────────────────────────────────────────────────────────

class FKBBuilder:
    """
    Orchestrates building the full FKB from raw data sources.

    Example:
        builder = FKBBuilder(output_dir="data/fkb/")
        builder.build_from_fnspid("data/raw/fnspid/")
        builder.build_macro_snapshots("data/raw/macro.csv")
        builder.build_fundamental_snapshots("data/raw/fundamentals.csv")
        builder.fkb.save()
    """

    def __init__(self, output_dir: str, encoder_device: str = "cpu"):
        self.fkb = FKB(output_dir)
        self.fkb.init_db()
        self._encoder_device = encoder_device
        self._encoder: Optional[FinBERTEncoder] = None

    @property
    def encoder(self) -> FinBERTEncoder:
        if self._encoder is None:
            self._encoder = FinBERTEncoder(device=self._encoder_device)
        return self._encoder

    def build_from_fnspid(
        self,
        fnspid_dir: str,
        sp100_tickers: Optional[List[str]] = None,
        max_date: Optional[datetime] = None,
    ):
        """
        Load FNSPID parquet/json files and index news documents.
        Filters to sp100_tickers and up to max_date if provided.
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas required to build from FNSPID")

        print("Loading FNSPID …")
        fnspid_path = Path(fnspid_dir)
        files = list(fnspid_path.glob("*.parquet")) + list(fnspid_path.glob("*.csv"))
        if not files:
            raise FileNotFoundError(f"No parquet/csv files in {fnspid_dir}")

        dfs = [pd.read_parquet(f) if str(f).endswith(".parquet")
               else pd.read_csv(f) for f in files]
        df = pd.concat(dfs, ignore_index=True)

        # Normalise column names
        col_map = {c.lower(): c for c in df.columns}
        headline_col = col_map.get("headline") or col_map.get("title")
        ticker_col = col_map.get("ticker") or col_map.get("symbol")
        ts_col = col_map.get("date") or col_map.get("timestamp") or col_map.get("publishedat")

        if sp100_tickers:
            df = df[df[ticker_col].isin(sp100_tickers)]
        if max_date:
            df[ts_col] = pd.to_datetime(df[ts_col])
            df = df[df[ts_col] <= max_date]

        df = df.dropna(subset=[headline_col, ticker_col, ts_col])
        df = df.drop_duplicates(subset=[headline_col])
        print(f"  {len(df):,} documents after filtering")

        docs = []
        for i, row in enumerate(df.itertuples(index=False)):
            doc_id = f"fnspid_{i:08d}"
            ts = getattr(row, ts_col)
            if not isinstance(ts, datetime):
                ts = pd.to_datetime(ts).to_pydatetime()
            docs.append(NewsDoc(
                doc_id=doc_id,
                ticker=str(getattr(row, ticker_col)),
                headline=str(getattr(row, headline_col)),
                timestamp=ts,
            ))

        self.fkb.build_news_index(docs, self.encoder)

    def build_event_outcomes(self, docs: List[NewsDoc],
                              price_df) -> List[EventOutcome]:
        """
        Compute forward returns for each NewsDoc and classify event types.
        `price_df` should be a DataFrame indexed by (ticker, date) with 'close' column.
        """
        outcomes = []
        for doc in docs:
            try:
                ticker = doc.ticker
                t0 = doc.timestamp.date()
                # Get forward prices
                rets = {}
                for horizon, label in [(1, "ret_1d"), (3, "ret_3d"),
                                        (7, "ret_7d"), (30, "ret_30d")]:
                    try:
                        p0 = price_df.loc[(ticker, t0), "close"]
                        th = t0 + timedelta(days=horizon)
                        # find next available trading day
                        for offset in range(horizon, horizon + 5):
                            th_try = t0 + timedelta(days=offset)
                            if (ticker, th_try) in price_df.index:
                                th = th_try
                                break
                        ph = price_df.loc[(ticker, th), "close"]
                        rets[label] = (ph - p0) / p0
                    except KeyError:
                        rets[label] = 0.0

                macro = self.fkb.db.get_macro_snapshot(doc.timestamp)
                regime = macro["macro_regime"] if macro else "NEUTRAL"
                event_type = self._classify_event_type(doc.headline)

                outcomes.append(EventOutcome(
                    event_id=f"eo_{doc.doc_id}",
                    ticker=ticker,
                    event_type=event_type,
                    headline=doc.headline,
                    timestamp=doc.timestamp,
                    macro_regime=regime,
                    **rets,
                ))
            except Exception:
                continue
        return outcomes

    @staticmethod
    def _classify_event_type(headline: str) -> str:
        """
        Simple keyword-based event classifier (replace with FinBERT classifier
        from Phase 1 for production).
        """
        h = headline.lower()
        if any(w in h for w in ["earnings", "eps", "revenue", "quarterly"]):
            return "C1"
        if any(w in h for w in ["acquire", "merger", "takeover", "deal"]):
            return "C3"
        if any(w in h for w in ["fed", "federal reserve", "interest rate", "fomc"]):
            return "M1"
        if any(w in h for w in ["inflation", "cpi", "pce"]):
            return "M4"
        if any(w in h for w in ["layoff", "job", "employment"]):
            return "C5"
        if any(w in h for w in ["product", "launch", "release", "announce"]):
            return "C2"
        return "K1"  # default: market movement

    def build_macro_snapshots(self, macro_csv: str):
        """
        Build macro_snapshot table from a CSV with columns:
        date, fed_rate, vix, yield_10y, yield_2y, sp500_ret_1m
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas required")

        df = pd.read_csv(macro_csv, parse_dates=["date"])
        snapshots = []
        for row in df.itertuples():
            spread = row.yield_10y - row.yield_2y
            regime, desc = label_macro_regime(row.fed_rate, row.vix, spread)
            snapshots.append(MacroSnapshot(
                date=row.date.to_pydatetime(),
                fed_rate=row.fed_rate,
                vix=row.vix,
                yield_10y=row.yield_10y,
                yield_2y=row.yield_2y,
                spread_10y_2y=spread,
                sp500_ret_1m=getattr(row, "sp500_ret_1m", 0.0),
                macro_regime=regime,
                regime_description=desc,
            ))
        self.fkb.db.insert_macro_snapshots(snapshots)
        print(f"  Inserted {len(snapshots)} macro snapshots")

    def build_fundamental_snapshots(self, fund_csv: str):
        """
        Build fundamental_snapshot table from a CSV with columns:
        ticker, report_date, pe_ratio, eps, eps_estimate, revenue,
        revenue_growth_yoy, analyst_rating, price_target, market_cap
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas required")

        df = pd.read_csv(fund_csv, parse_dates=["report_date"])
        snaps = []
        for row in df.itertuples():
            snaps.append(FundamentalSnapshot(
                ticker=row.ticker,
                report_date=row.report_date.to_pydatetime(),
                pe_ratio=float(row.pe_ratio or 0),
                eps=float(row.eps or 0),
                eps_estimate=float(row.eps_estimate or 0),
                revenue=float(row.revenue or 0),
                revenue_growth_yoy=float(row.revenue_growth_yoy or 0),
                analyst_rating=float(row.analyst_rating or 3),
                price_target=float(row.price_target or 0),
                market_cap=float(row.market_cap or 0),
            ))
        self.fkb.db.insert_fundamental_snapshots(snaps)
        print(f"  Inserted {len(snaps)} fundamental snapshots")


# ──────────────────────────────────────────────────────────────────────────────
# Incremental updater
# ──────────────────────────────────────────────────────────────────────────────

class FKBUpdater:
    """
    Incremental daily update for production use.
    Adds new news documents and updates macro/fundamental data.
    """

    def __init__(self, fkb: FKB, encoder: FinBERTEncoder):
        self.fkb = fkb
        self.encoder = encoder

    def add_news(self, new_docs: List[NewsDoc]):
        """Encode and add new documents to FAISS + BM25 + doc_store."""
        if not new_docs:
            return
        headlines = [d.headline for d in new_docs]
        doc_ids = [d.doc_id for d in new_docs]
        embs = self.encoder.encode(headlines)
        for doc, emb in zip(new_docs, embs):
            doc.embedding = emb
            self.fkb.doc_store[doc.doc_id] = doc
        if self.fkb.faiss_idx:
            self.fkb.faiss_idx.add(embs, doc_ids)
        # BM25 requires full rebuild (limitation of rank-bm25)
        all_headlines = [d.headline for d in self.fkb.doc_store.values()]
        all_ids = list(self.fkb.doc_store.keys())
        self.fkb.bm25_idx = BM25Index()
        self.fkb.bm25_idx.build(all_headlines, all_ids)
        print(f"  Added {len(new_docs)} documents; total = {len(self.fkb.doc_store):,}")


if __name__ == "__main__":
    print("FKB module loaded. Use FKBBuilder to construct the knowledge base.")
