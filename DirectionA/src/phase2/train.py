from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader, Subset
from tqdm import tqdm

from causal_discovery import CausalRegularizationLoss
from dataset import FastEventDataset
from model_wrapper import FastModel


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def safe_device(device: str) -> torch.device:
    if device == "cuda" and not torch.cuda.is_available():
        return torch.device("cpu")
    return torch.device(device)


def chronological_split(n: int, train_ratio: float) -> tuple[list[int], list[int]]:
    n_train = int(n * train_ratio)
    return list(range(n_train)), list(range(n_train, n))


def class_weights(dataset: FastEventDataset, indices: list[int], device: torch.device) -> torch.Tensor:
    labels = torch.tensor([int(dataset.examples[i][1]) for i in indices], dtype=torch.long)
    counts = torch.bincount(labels, minlength=2).float()
    weights = counts.sum() / counts.clamp_min(1.0)
    return (weights / weights.mean()).to(device)


def graph_payload(model: FastModel, epoch: int, metrics: dict[str, float]) -> dict[str, object]:
    layer = model.stacd.layers[0]
    causal_matrix = layer.causal_matrix.detach().cpu()
    lag_matrix = layer.lag_matrix.detach().cpu()
    return {
        "epoch": int(epoch),
        "metrics": metrics,
        "causal_matrix": causal_matrix,
        "lag_matrix": lag_matrix,
        "adjacency_raw": causal_matrix,
    }


def summarize_graph(model: FastModel) -> dict[str, float]:
    A = model.stacd.layers[0].causal_matrix.detach().cpu()
    off = A[~torch.eye(A.shape[0], dtype=torch.bool)]
    return {
        "causal_mean": float(A.mean()),
        "causal_std": float(A.std()),
        "causal_offdiag_mean": float(off.mean()),
        "causal_offdiag_std": float(off.std()),
        "causal_min": float(A.min()),
        "causal_max": float(A.max()),
    }


def run_epoch(
    model: FastModel,
    loader: DataLoader,
    *,
    device: torch.device,
    criterion: torch.nn.Module,
    reg_fn: CausalRegularizationLoss,
    optimizer: torch.optim.Optimizer | None,
    reg_weight: float,
    desc: str,
) -> dict[str, float]:
    train = optimizer is not None
    model.train(mode=train)
    total = 0.0
    cls_total = 0.0
    reg_total = 0.0
    correct = 0
    n = 0
    context = torch.enable_grad() if train else torch.no_grad()
    with context:
        for batch in tqdm(loader, desc=desc, leave=False):
            emb = batch["text_emb"].to(device)
            types = batch["event_types"].to(device)
            ts = batch["timestamps"].to(device)
            y = batch["label"].to(device)

            logits, causal_info = model(emb, types, ts)
            cls_loss = criterion(logits, y)
            reg_loss = reg_fn(causal_info)["total_reg"]
            loss = cls_loss + float(reg_weight) * reg_loss

            if train:
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()

            bs = int(y.shape[0])
            total += float(loss.detach().cpu()) * bs
            cls_total += float(cls_loss.detach().cpu()) * bs
            reg_total += float(reg_loss.detach().cpu()) * bs
            correct += int((logits.argmax(dim=1) == y).sum().item())
            n += bs

    return {
        "loss": total / n,
        "cls_loss": cls_total / n,
        "reg_loss": reg_total / n,
        "accuracy": correct / n,
    }


def write_row(path: Path, row: dict[str, object]) -> None:
    fields = [
        "epoch",
        "train_loss",
        "val_loss",
        "train_cls_loss",
        "val_cls_loss",
        "train_reg_loss",
        "val_reg_loss",
        "train_accuracy",
        "val_accuracy",
        "causal_mean",
        "causal_std",
        "causal_offdiag_mean",
        "causal_offdiag_std",
        "causal_min",
        "causal_max",
    ]
    write_header = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if write_header:
            writer.writeheader()
        writer.writerow({key: row[key] for key in fields})


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrain repaired Direction A Phase 2 STACD")
    project_root = Path(__file__).resolve().parents[2]
    parser.add_argument("--embeddings", default=str(project_root / "data/embeddings/emb.pt"))
    parser.add_argument("--meta", default=str(project_root / "data/embeddings/meta.json"))
    parser.add_argument("--price-dir", default=str(project_root / "data/sp100_prices"))
    parser.add_argument("--output-dir", default=str(project_root / "data/stage2_repaired"))
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=3e-5)
    parser.add_argument("--weight-decay", type=float, default=0.02)
    parser.add_argument("--seq-len", type=int, default=32)
    parser.add_argument("--label-threshold", type=float, default=0.0)
    parser.add_argument("--train-ratio", type=float, default=0.8)
    parser.add_argument("--reg-weight", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()

    set_seed(args.seed)
    device = safe_device(args.device)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    metrics_csv = out_dir / "metrics.csv"
    metrics_csv.unlink(missing_ok=True)

    dataset = FastEventDataset(
        args.embeddings,
        args.meta,
        args.price_dir,
        seq_len=args.seq_len,
        label_threshold=args.label_threshold,
    )
    train_idx, val_idx = chronological_split(len(dataset), args.train_ratio)
    train_set = Subset(dataset, train_idx)
    val_set = Subset(dataset, val_idx)
    train_loader = DataLoader(train_set, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_set, batch_size=args.batch_size, shuffle=False)

    model = FastModel().to(device)
    criterion = torch.nn.CrossEntropyLoss(weight=class_weights(dataset, train_idx, device))
    reg_fn = CausalRegularizationLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)

    best_acc = None
    best_epoch = 0
    best_metrics = None
    for epoch in tqdm(range(1, args.epochs + 1), desc="stage2 training"):
        train = run_epoch(
            model,
            train_loader,
            device=device,
            criterion=criterion,
            reg_fn=reg_fn,
            optimizer=optimizer,
            reg_weight=args.reg_weight,
            desc=f"epoch {epoch:03d} train",
        )
        val = run_epoch(
            model,
            val_loader,
            device=device,
            criterion=criterion,
            reg_fn=reg_fn,
            optimizer=None,
            reg_weight=args.reg_weight,
            desc=f"epoch {epoch:03d} val",
        )
        row = {
            "epoch": epoch,
            "train_loss": train["loss"],
            "val_loss": val["loss"],
            "train_cls_loss": train["cls_loss"],
            "val_cls_loss": val["cls_loss"],
            "train_reg_loss": train["reg_loss"],
            "val_reg_loss": val["reg_loss"],
            "train_accuracy": train["accuracy"],
            "val_accuracy": val["accuracy"],
            **summarize_graph(model),
        }
        write_row(metrics_csv, row)
        torch.save(graph_payload(model, epoch, val), out_dir / f"causal_epoch_{epoch}.pt")
        torch.save(model.state_dict(), out_dir / "last_model.pt")
        if best_acc is None or val["accuracy"] > best_acc:
            best_acc = val["accuracy"]
            best_epoch = epoch
            best_metrics = val
            torch.save(model.state_dict(), out_dir / "best_model.pt")
            torch.save(graph_payload(model, epoch, val), out_dir / "best_graph.pt")
        tqdm.write(
            f"epoch={epoch:03d} train_acc={train['accuracy']:.4f} "
            f"val_acc={val['accuracy']:.4f} A_std={row['causal_std']:.4f}"
        )

    meta = {
        "args": vars(args),
        "n_examples": len(dataset),
        "n_train": len(train_set),
        "n_val": len(val_set),
        "best_epoch": best_epoch,
        "best_val_accuracy": best_acc,
        "best_metrics": best_metrics,
        "graph": summarize_graph(model),
    }
    (out_dir / "run_meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
