"""Build the Phase 3 tensor dataset from labeled events, embeddings, prices, and Stage 2 graphs."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import pandas as pd
import torch
from tqdm import tqdm

if __package__ in (None, ""):
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from src.phase1.event_types import EVENT_TYPE_TO_ID


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def load_price_tables(price_dir: Path) -> dict[str, pd.DataFrame]:
    tables = {}
    for path in price_dir.glob("*.csv"):
        df = pd.read_csv(path)
        df.columns = [col.strip().lower().replace("_", " ") for col in df.columns]
        df["date"] = pd.to_datetime(df["date"], utc=True).dt.tz_convert(None)
        df = df.sort_values("date").set_index("date")
        tables[path.stem] = df
    return tables


def latest_causal_snapshot(stage2_dir: Path) -> Path:
    paths = list(stage2_dir.glob("causal_epoch_*.pt"))
    keyed = []
    for path in paths:
        match = re.search(r"causal_epoch_(\d+)\.pt$", path.name)
        if match:
            keyed.append((int(match.group(1)), path))
    if not keyed:
        raise FileNotFoundError(f"No causal_epoch_*.pt files found in {stage2_dir}")
    return max(keyed, key=lambda x: x[0])[1]


def extract_graph(payload: dict) -> tuple[torch.Tensor, torch.Tensor]:
    if "causal_matrix" in payload and "lag_matrix" in payload:
        return payload["causal_matrix"].float(), payload["lag_matrix"].float()
    if "causal_info" in payload:
        info = payload["causal_info"]
        return info["causal_matrix"].float(), info["lag_matrix"].float()
    if "adjacency_raw" in payload and "lag_matrix" in payload:
        return torch.as_tensor(payload["adjacency_raw"]).float(), torch.as_tensor(payload["lag_matrix"]).float()
    if "stacd.layers.0.causal_raw" in payload and "stacd.layers.0.lag_raw" in payload:
        causal_matrix = torch.sigmoid(payload["stacd.layers.0.causal_raw"]).float()
        lag_matrix = torch.nn.functional.softplus(payload["stacd.layers.0.lag_raw"]).float()
        return causal_matrix, lag_matrix
    if "causal_raw" in payload and "lag_raw" in payload:
        causal_matrix = torch.sigmoid(payload["causal_raw"]).float()
        lag_matrix = torch.nn.functional.softplus(payload["lag_raw"]).float()
        return causal_matrix, lag_matrix
    if "T" in payload:
        lag_matrix = payload["T"].float()
        causal_matrix = torch.ones_like(lag_matrix)
        causal_matrix.fill_diagonal_(0.0)
        return causal_matrix, lag_matrix
    raise KeyError("Causal snapshot needs causal_matrix/lag_matrix or causal_info with both tensors.")


def load_stage2_graph(stage2_dir: Path, graph_path: Path | None) -> tuple[torch.Tensor, torch.Tensor, Path]:
    best_graph = stage2_dir / "best_graph.pt"
    best_model = stage2_dir / "best_model.pt"
    candidates = [graph_path] if graph_path is not None else [best_graph, latest_causal_snapshot(stage2_dir), best_model]
    last_error: Exception | None = None
    for path in candidates:
        if path is None or not path.exists():
            continue
        payload = torch.load(path, map_location="cpu")
        if not isinstance(payload, dict):
            continue
        try:
            causal_matrix, lag_matrix = extract_graph(payload)
            return causal_matrix, lag_matrix, path
        except KeyError as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    raise KeyError("No usable Stage 2 causal graph found.")


def event_magnitude(row: dict) -> float:
    magnitude = row["magnitude"]
    if magnitude is None:
        return 0.0
    polarity = row["polarity"]
    sign = -1.0 if polarity == "negative" else 1.0
    return sign * float(magnitude)


def price_window_and_label(
    table: pd.DataFrame,
    event_time: pd.Timestamp,
    price_window: int,
    label_threshold: float,
) -> tuple[torch.Tensor, int, float]:
    dates = table.index[table.index <= event_time]
    if len(dates) < price_window:
        raise IndexError("Not enough price history before event timestamp")
    current_dt = dates[-1]
    loc = table.index.get_loc(current_dt)
    if loc + 1 >= len(table):
        raise IndexError("No next trading day for label")
    window = table.iloc[loc - price_window + 1 : loc + 1][["open", "high", "low", "close", "volume"]].astype("float32")
    current_close = float(table.iloc[loc]["close"])
    next_close = float(table.iloc[loc + 1]["close"])
    ret = (next_close - current_close) / current_close
    if ret > label_threshold:
        direction = 0
    elif ret < -label_threshold:
        direction = 1
    else:
        direction = 2
    return torch.tensor(window.to_numpy(), dtype=torch.float32), direction, float(ret)


def build_examples(
    labels: list[dict],
    embeddings: torch.Tensor,
    prices: dict[str, pd.DataFrame],
    seq_len: int,
    price_window: int,
    label_threshold: float,
    context_mode: str,
) -> dict[str, torch.Tensor]:
    valid = [
        (i, row)
        for i, row in enumerate(labels)
        if row["event_type"] in EVENT_TYPE_TO_ID and row["affected_tickers"]
    ]
    valid.sort(key=lambda item: pd.to_datetime(item[1]["source_date"], utc=True).tz_convert(None))

    if context_mode == "global":
        targets = []
        for end in range(seq_len - 1, len(valid)):
            seq = valid[end - seq_len + 1 : end + 1]
            ticker = seq[-1][1]["affected_tickers"][0]
            targets.append((ticker, seq))
    elif context_mode == "ticker":
        by_ticker: dict[str, list[tuple[int, dict]]] = {}
        for item in valid:
            _, row = item
            for ticker in row["affected_tickers"]:
                by_ticker.setdefault(ticker, []).append(item)
        targets = []
        for ticker in sorted(by_ticker):
            rows = by_ticker[ticker]
            for end in range(seq_len - 1, len(rows)):
                targets.append((ticker, rows[end - seq_len + 1 : end + 1]))
        targets.sort(key=lambda item: pd.to_datetime(item[1][-1][1]["source_date"], utc=True).tz_convert(None))
    else:
        raise ValueError("context_mode must be 'global' or 'ticker'")

    stock_tickers = sorted({ticker for ticker, _ in targets if ticker in prices})
    stock_to_id = {ticker: i for i, ticker in enumerate(stock_tickers)}

    text_embeddings = []
    event_types = []
    timestamps = []
    magnitudes = []
    price_history = []
    direction_labels = []
    magnitude_labels = []
    prediction_timestamps = []
    tickers = []
    target_stock_ids = []
    label_row_indices = []

    for ticker, seq in tqdm(targets, desc=f"building phase3 dataset ({context_mode})"):
        idxs = [idx for idx, _ in seq]
        rows = [row for _, row in seq]
        target = rows[-1]
        if ticker not in prices:
            continue

        event_time = pd.to_datetime(target["source_date"], utc=True).tz_convert(None)
        try:
            px, direction, ret = price_window_and_label(
                prices[ticker],
                event_time,
                price_window,
                label_threshold,
            )
        except IndexError:
            continue

        ts = torch.tensor([pd.to_datetime(row["source_date"], utc=True).timestamp() for row in rows], dtype=torch.float32)
        ts = (ts - ts.min()) / (ts.max() - ts.min() + 1e-6)
        text_embeddings.append(embeddings[idxs].float())
        event_types.append(torch.tensor([EVENT_TYPE_TO_ID[row["event_type"]] for row in rows], dtype=torch.long))
        timestamps.append(ts)
        magnitudes.append(torch.tensor([event_magnitude(row) for row in rows], dtype=torch.float32))
        price_history.append(px)
        direction_labels.append(direction)
        magnitude_labels.append(ret)
        prediction_timestamps.append(event_time.timestamp())
        tickers.append(ticker)
        target_stock_ids.append(stock_to_id[ticker])
        label_row_indices.append(idxs[-1])

    if not text_embeddings:
        raise RuntimeError("No Phase 3 examples were built. Check label dates, tickers, prices, and embeddings.")

    return {
        "text_embeddings": torch.stack(text_embeddings),
        "event_types": torch.stack(event_types),
        "timestamps": torch.stack(timestamps),
        "magnitudes": torch.stack(magnitudes),
        "price_history": torch.stack(price_history),
        "direction_labels": torch.tensor(direction_labels, dtype=torch.long),
        "magnitude_labels": torch.tensor(magnitude_labels, dtype=torch.float32),
        "prediction_timestamps": torch.tensor(prediction_timestamps, dtype=torch.float64),
        "tickers": tickers,
        "target_stock_ids": torch.tensor(target_stock_ids, dtype=torch.long),
        "stock_tickers": stock_tickers,
        "label_row_indices": torch.tensor(label_row_indices, dtype=torch.long),
        "context_mode": context_mode,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Direction A Phase 3 dataset")
    parser.add_argument("--labels", default="data/labels/silver_labels_test_upgraded.jsonl")
    parser.add_argument("--embeddings", default="data/embeddings/emb.pt")
    parser.add_argument("--price-dir", default="data/sp100_prices")
    parser.add_argument("--stage2-dir", default="data/stage2")
    parser.add_argument("--graph", default=None)
    parser.add_argument("--output", default="data/stage3/phase3_dataset.pt")
    parser.add_argument("--seq-len", type=int, default=32)
    parser.add_argument("--price-window", type=int, default=30)
    parser.add_argument("--label-threshold", type=float, default=0.005)
    parser.add_argument("--context-mode", choices=["ticker", "global"], default="ticker")
    args = parser.parse_args()

    labels = load_jsonl(Path(args.labels))
    embeddings = torch.load(args.embeddings, map_location="cpu")
    prices = load_price_tables(Path(args.price_dir))
    causal_matrix, lag_matrix, graph_path = load_stage2_graph(Path(args.stage2_dir), Path(args.graph) if args.graph else None)

    data = build_examples(
        labels,
        embeddings,
        prices,
        seq_len=args.seq_len,
        price_window=args.price_window,
        label_threshold=args.label_threshold,
        context_mode=args.context_mode,
    )
    data["causal_matrix"] = causal_matrix
    data["lag_matrix"] = lag_matrix
    data["stage2_graph_path"] = str(graph_path)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    torch.save(data, output)
    print(f"wrote {output}")
    print(f"n={data['direction_labels'].shape[0]} graph={graph_path}")
    print(f"context_mode={data['context_mode']} n_stocks={len(data['stock_tickers'])}")


if __name__ == "__main__":
    main()
