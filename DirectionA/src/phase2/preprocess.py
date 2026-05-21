import json
import torch
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModel
from pathlib import Path

MODEL_NAME = "ProsusAI/finbert"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
BATCH_SIZE = 32

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModel.from_pretrained(MODEL_NAME).to(DEVICE)
model.eval()

def process(json_path, save_path, limit=None):
    data = []
    with open(json_path, encoding="utf-8") as f:
        for line in f:
            try:
                data.append(json.loads(line))
            except json.JSONDecodeError:
                continue
            if limit is not None and len(data) >= limit:
                break

    embeddings = []
    meta = []

    with torch.no_grad():
        for start in tqdm(range(0, len(data), BATCH_SIZE)):
            batch = data[start:start + BATCH_SIZE]
            texts = [x["headline"] for x in batch]

            enc = tokenizer(
                texts,
                truncation=True,
                padding="max_length",
                max_length=128,
                return_tensors="pt"
            ).to(DEVICE)

            out = model(**enc)
            cls = out.last_hidden_state[:, 0].cpu()  # (B, 768)

            embeddings.extend(cls)
            for x in batch:
                meta.append({
                    "event_type": x["event_type"],
                    "timestamp": x["source_date"],
                    "ticker": x["source_ticker"]
                })

    embeddings = torch.stack(embeddings)  # (N, 768)

    save_path.mkdir(parents=True, exist_ok=True)
    torch.save(embeddings, save_path / "emb.pt")

    with open(save_path / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Embed Phase 2/3 labeled event headlines with FinBERT")
    parser.add_argument("--labels", default="data/labels/silver_labels_test_upgraded.jsonl")
    parser.add_argument("--output-dir", default="data/embeddings")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    print(torch.version.cuda)
    print(f"device={DEVICE}")
    process(Path(args.labels), Path(args.output_dir), limit=args.limit)
