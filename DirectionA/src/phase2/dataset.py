from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import torch
from torch.utils.data import Dataset

EVENT_TYPE_MAP = {
    "M1": 0,
    "M2": 1,
    "M3": 2,
    "M4": 3,
    "M5": 4,
    "M6": 5,
    "C1": 6,
    "C2": 7,
    "C3": 8,
    "C4": 9,
    "C5": 10,
    "C6": 11,
    "C7": 12,
    "C8": 13,
    "K1": 14,
    "K2": 15,
    "K3": 16,
    "K4": 17,
    "G1": 18,
    "G2": 19,
}


class FastEventDataset(Dataset):
    def __init__(
        self,
        emb_path: str | Path,
        meta_path: str | Path,
        price_dir: str | Path,
        seq_len: int = 32,
        label_threshold: float = 0.0,
    ):
        self.emb = torch.load(Path(emb_path), map_location="cpu").float()
        self.meta = json.loads(Path(meta_path).read_text(encoding="utf-8"))
        self.seq_len = int(seq_len)
        self.label_threshold = float(label_threshold)
        self.price_data = self._load_prices(Path(price_dir))
        self.examples = self._build_examples()

    @staticmethod
    def _parse_time(value: str) -> pd.Timestamp:
        return pd.to_datetime(value, utc=True).tz_convert(None)

    @staticmethod
    def _load_prices(price_dir: Path) -> dict[str, pd.DataFrame]:
        tables = {}
        for path in price_dir.glob("*.csv"):
            df = pd.read_csv(path)
            df.columns = [col.strip().lower().replace("_", " ") for col in df.columns]
            df["date"] = pd.to_datetime(df["date"], utc=True).dt.tz_convert(None)
            df = df.sort_values("date").set_index("date")
            tables[path.stem] = df
        return tables

    def _label_for(self, ticker: str, timestamp: pd.Timestamp) -> int | None:
        table = self.price_data.get(ticker)
        if table is None:
            return None

        dates = table.index[table.index <= timestamp]
        if len(dates) == 0:
            return None
        current_dt = dates[-1]
        loc = table.index.get_loc(current_dt)
        if loc + 1 >= len(table):
            return None

        current_close = float(table.iloc[loc]["close"])
        next_close = float(table.iloc[loc + 1]["close"])
        ret = (next_close - current_close) / current_close
        if ret > self.label_threshold:
            return 1
        if ret < -self.label_threshold:
            return 0
        return None

    def _build_examples(self) -> list[tuple[list[int], int]]:
        by_ticker: dict[str, list[tuple[pd.Timestamp, int]]] = {}
        for idx, row in enumerate(self.meta):
            event_type = row["event_type"]
            ticker = row["ticker"]
            if event_type not in EVENT_TYPE_MAP or ticker not in self.price_data:
                continue
            by_ticker.setdefault(ticker, []).append((self._parse_time(row["timestamp"]), idx))

        examples = []
        for ticker in sorted(by_ticker):
            rows = sorted(by_ticker[ticker], key=lambda x: x[0])
            for end in range(self.seq_len - 1, len(rows)):
                seq = rows[end - self.seq_len + 1 : end + 1]
                target_time, _ = seq[-1]
                label = self._label_for(ticker, target_time)
                if label is None:
                    continue
                examples.append(([idx for _, idx in seq], label))
        return examples

    def __len__(self) -> int:
        return len(self.examples)

    @staticmethod
    def encode_time(value: str) -> float:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S UTC").timestamp()

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        idxs, label = self.examples[idx]
        rows = [self.meta[i] for i in idxs]
        timestamps = torch.tensor([self.encode_time(row["timestamp"]) for row in rows], dtype=torch.float32)
        timestamps = (timestamps - timestamps.min()) / (timestamps.max() - timestamps.min() + 1e-6)

        return {
            "text_emb": self.emb[idxs],
            "event_types": torch.tensor([EVENT_TYPE_MAP[row["event_type"]] for row in rows], dtype=torch.long),
            "timestamps": timestamps,
            "label": torch.tensor(label, dtype=torch.long),
        }
