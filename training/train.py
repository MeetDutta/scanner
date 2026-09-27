"""
SpecGuard Offline Machine Learning Model Training Pipeline.
Trains Domain Classifier, Logical Contradiction Net, and Engineering NER
strictly on the 70% Train split and evaluates on the 15% Validation split.
Exports PyTorch weights (.pt) and portable ONNX graphs (.onnx) into models/.
"""

import json
import time
import random
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from typing import Dict, List, Any, Tuple

import yaml
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import logging

from specguard.models.domain_classifier import DomainClassifierNet, SimpleTokenizer
from specguard.models.logical_classifier import LogicalRelationNet
from specguard.models.engineering_ner import (
    BiLSTMNER, RegexOffsetTokenizer, LABEL2ID, ID2LABEL, PAD_ID, O_ID, NER_LABELS
)
from specguard.models.registry import ModelRegistry

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SpecGuard.Train")


def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


class DomainDataset(Dataset):
    def __init__(self, data: List[Dict[str, Any]], tokenizer: SimpleTokenizer, max_len: int = 64):
        self.data = data
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        item = self.data[idx]
        ids = self.tokenizer.encode(item["text"], max_len=self.max_len)
        return torch.tensor(ids, dtype=torch.long), torch.tensor(item["label"], dtype=torch.long)


class LogicalDataset(Dataset):
    def __init__(self, data: List[Dict[str, Any]], tokenizer: SimpleTokenizer, max_len: int = 48):
        self.data = data
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        item = self.data[idx]
        ids_a = self.tokenizer.encode(item["text_a"], max_len=self.max_len)
        ids_b = self.tokenizer.encode(item["text_b"], max_len=self.max_len)
        return (
            torch.tensor(ids_a, dtype=torch.long),
            torch.tensor(ids_b, dtype=torch.long),
            torch.tensor(item["label"], dtype=torch.long)
        )


def train_domain_classifier(
    train_data: List[Dict[str, Any]],
    val_data: List[Dict[str, Any]],
    cfg: Dict[str, Any],
    checkpoints_dir: Path,
    onnx_dir: Path
) -> Dict[str, Any]:
    logger.info("--- Starting Domain Classifier Training ---")
    d_cfg = cfg["domain_classifier"]

    tokenizer = SimpleTokenizer(max_vocab=d_cfg.get("vocab_size", 5000))
    tokenizer.fit([d["text"] for d in train_data])

    train_ds = DomainDataset(train_data, tokenizer, max_len=64)
    val_ds = DomainDataset(val_data, tokenizer, max_len=64)

    train_loader = DataLoader(train_ds, batch_size=d_cfg.get("batch_size", 8), shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=d_cfg.get("batch_size", 8), shuffle=False)

    model = DomainClassifierNet(
        vocab_size=len(tokenizer.word2idx) + 1,
        embed_dim=d_cfg.get("embed_dim", 64),
        hidden_dim=d_cfg.get("hidden_dim", 64),
        num_classes=d_cfg.get("num_classes", 4)
    )

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=d_cfg.get("learning_rate", 0.003))

    best_val_acc = 0.0
    best_weights = None
    epochs = d_cfg.get("epochs", 15)

    history = []

    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        correct = 0
        total = 0

        for x, y in train_loader:
            optimizer.zero_grad()
            logits = model(x)
            loss = criterion(logits, y)
            loss.backward()
            optimizer.step()

            total_loss += loss.item() * len(y)
            preds = torch.argmax(logits, dim=1)
            correct += (preds == y).sum().item()
            total += len(y)

        train_acc = correct / total if total > 0 else 0.0
        train_loss = total_loss / total if total > 0 else 0.0

        # Evaluate on validation
        model.eval()
        v_loss = 0.0
        v_correct = 0
        v_total = 0
        with torch.no_grad():
            for vx, vy in val_loader:
                v_logits = model(vx)
                loss = criterion(v_logits, vy)
                v_loss += loss.item() * len(vy)
                preds = torch.argmax(v_logits, dim=1)
                v_correct += (preds == vy).sum().item()
                v_total += len(vy)

        val_acc = v_correct / v_total if v_total > 0 else 0.0
        val_loss = v_loss / v_total if v_total > 0 else 0.0

        history.append({
            "epoch": epoch,
            "train_loss": round(train_loss, 4),
            "train_acc": round(train_acc, 4),
            "val_loss": round(val_loss, 4),
            "val_acc": round(val_acc, 4)
        })

        if val_acc >= best_val_acc:
            best_val_acc = val_acc
            best_weights = model.state_dict().copy()

    logger.info("Domain Classifier Training Complete. Best Validation Accuracy: %.4f", best_val_acc)

    # Save best PyTorch weights
    pt_path = checkpoints_dir / "domain_classifier.pt"
    torch.save(best_weights or model.state_dict(), pt_path)

    # Save tokenizer
    tok_path = checkpoints_dir / "domain_tokenizer.json"
    with open(tok_path, "w", encoding="utf-8") as f:
        json.dump(tokenizer.to_dict(), f, indent=2)

    # Export ONNX
    onnx_path = onnx_dir / "domain_classifier.onnx"
    try:
        model.load_state_dict(best_weights or model.state_dict())
        model.eval()
        dummy_in = torch.zeros((1, 64), dtype=torch.long)
        torch.onnx.export(
            model,
            dummy_in,
            str(onnx_path),
            input_names=["input_ids"],
            output_names=["logits"],
            dynamic_axes={"input_ids": {0: "batch_size"}, "logits": {0: "batch_size"}},
            opset_version=14
        )
        logger.info("Exported Domain Classifier ONNX graph to %s", onnx_path)
    except Exception as e:
        logger.warning("ONNX export skipped: %s", e)

    return {
        "model": "DomainClassifierNet",
        "best_val_acc": round(best_val_acc, 4),
        "history": history,
        "weights_path": str(pt_path),
        "onnx_path": str(onnx_path) if onnx_path.exists() else None
    }


def train_logical_classifier(
    train_data: List[Dict[str, Any]],
    val_data: List[Dict[str, Any]],
    cfg: Dict[str, Any],
    checkpoints_dir: Path,
    onnx_dir: Path
) -> Dict[str, Any]:
    logger.info("--- Starting Logical Contradiction Classifier Training ---")
    l_cfg = cfg["logical_classifier"]

    tokenizer = SimpleTokenizer(max_vocab=l_cfg.get("vocab_size", 5000))
    all_texts = []
    for d in train_data:
        all_texts.append(d["text_a"])
        all_texts.append(d["text_b"])
    tokenizer.fit(all_texts)

    train_ds = LogicalDataset(train_data, tokenizer, max_len=48)
    val_ds = LogicalDataset(val_data, tokenizer, max_len=48)

    train_loader = DataLoader(train_ds, batch_size=l_cfg.get("batch_size", 8), shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=l_cfg.get("batch_size", 8), shuffle=False)

    model = LogicalRelationNet(
        vocab_size=len(tokenizer.word2idx) + 1,
        embed_dim=l_cfg.get("embed_dim", 64),
        hidden_dim=l_cfg.get("hidden_dim", 64)
    )

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=l_cfg.get("learning_rate", 0.003))

    best_val_acc = 0.0
    best_weights = None
    epochs = l_cfg.get("epochs", 15)
    history = []

    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        correct = 0
        total = 0

        for xa, xb, y in train_loader:
            optimizer.zero_grad()
            logits = model(xa, xb)
            loss = criterion(logits, y)
            loss.backward()
            optimizer.step()

            total_loss += loss.item() * len(y)
            preds = torch.argmax(logits, dim=1)
            correct += (preds == y).sum().item()
            total += len(y)

        train_acc = correct / total if total > 0 else 0.0
        train_loss = total_loss / total if total > 0 else 0.0

        model.eval()
        v_loss = 0.0
        v_correct = 0
        v_total = 0
        with torch.no_grad():
            for vxa, vxb, vy in val_loader:
                v_logits = model(vxa, vxb)
                loss = criterion(v_logits, vy)
                v_loss += loss.item() * len(vy)
                preds = torch.argmax(v_logits, dim=1)
                v_correct += (preds == vy).sum().item()
                v_total += len(vy)

        val_acc = v_correct / v_total if v_total > 0 else 0.0
        val_loss = v_loss / v_total if v_total > 0 else 0.0

        history.append({
            "epoch": epoch,
            "train_loss": round(train_loss, 4),
            "train_acc": round(train_acc, 4),
            "val_loss": round(val_loss, 4),
            "val_acc": round(val_acc, 4)
        })

        if val_acc >= best_val_acc:
            best_val_acc = val_acc
            best_weights = model.state_dict().copy()

    logger.info("Logical Classifier Training Complete. Best Validation Accuracy: %.4f", best_val_acc)

    pt_path = checkpoints_dir / "logical_classifier.pt"
    torch.save(best_weights or model.state_dict(), pt_path)

    tok_path = checkpoints_dir / "logical_tokenizer.json"
    with open(tok_path, "w", encoding="utf-8") as f:
        json.dump(tokenizer.to_dict(), f, indent=2)

    onnx_path = onnx_dir / "logical_classifier.onnx"
    try:
        model.load_state_dict(best_weights or model.state_dict())
        model.eval()
        d_a = torch.zeros((1, 48), dtype=torch.long)
        d_b = torch.zeros((1, 48), dtype=torch.long)
        torch.onnx.export(
            model,
            (d_a, d_b),
            str(onnx_path),
            input_names=["statement_a", "statement_b"],
            output_names=["logits"],
            dynamic_axes={"statement_a": {0: "batch_size"}, "statement_b": {0: "batch_size"}},
            opset_version=14
        )
        logger.info("Exported Logical Classifier ONNX graph to %s", onnx_path)
    except Exception as e:
        logger.warning("ONNX export skipped: %s", e)

    return {
        "model": "LogicalRelationNet",
        "best_val_acc": round(best_val_acc, 4),
        "history": history,
        "weights_path": str(pt_path),
        "onnx_path": str(onnx_path) if onnx_path.exists() else None
    }


def train_engineering_ner(
    train_data: List[Dict[str, Any]],
    val_data: List[Dict[str, Any]],
    cfg: Dict[str, Any],
    checkpoints_dir: Path
) -> Dict[str, Any]:
    logger.info("--- Starting Engineering Parameter NER Training ---")
    n_cfg = cfg["engineering_ner"]

    # Build vocabulary from training tokens
    words_vocab = {"<PAD>": 0, "<UNK>": 1}
    for item in train_data:
        tokens = RegexOffsetTokenizer.tokenize_with_offsets(item["text"])
        for t in tokens:
            w = t.token.lower()
            if w not in words_vocab and len(words_vocab) < 5000:
                words_vocab[w] = len(words_vocab)

    model = BiLSTMNER(
        vocab_size=len(words_vocab) + 1,
        embed_dim=n_cfg.get("embed_dim", 64),
        hidden_dim=n_cfg.get("hidden_dim", 64),
        num_labels=len(NER_LABELS),
        dropout=n_cfg.get("dropout", 0.3)
    )


    criterion = nn.CrossEntropyLoss(ignore_index=PAD_ID)
    optimizer = torch.optim.Adam(model.parameters(), lr=n_cfg.get("learning_rate", 0.003))

    epochs = n_cfg.get("epochs", 15)
    best_loss = float("inf")
    best_weights = None

    for epoch in range(1, epochs + 1):
        model.train()
        epoch_loss = 0.0
        n_batches = 0

        for item in train_data:
            tokens = RegexOffsetTokenizer.tokenize_with_offsets(item["text"])
            bio_labels = RegexOffsetTokenizer.align_entities_to_bio(tokens, item.get("entities", []), LABEL2ID)

            x_ids = [words_vocab.get(t.token.lower(), 1) for t in tokens[:64]]
            y_ids = bio_labels[:64]

            if not x_ids:
                continue

            x_t = torch.tensor([x_ids], dtype=torch.long)
            y_t = torch.tensor([y_ids], dtype=torch.long)

            optimizer.zero_grad()
            logits = model(x_t)  # (1, seq_len, tagset_size)
            loss = criterion(logits.view(-1, len(NER_LABELS)), y_t.view(-1))
            loss.backward()
            optimizer.step()

            epoch_loss += loss.item()
            n_batches += 1

        avg_loss = epoch_loss / n_batches if n_batches > 0 else 0.0
        if avg_loss < best_loss:
            best_loss = avg_loss
            best_weights = model.state_dict().copy()

    logger.info("Engineering NER Training Complete. Final Training Loss: %.4f", best_loss)

    pt_path = checkpoints_dir / "engineering_ner.pt"
    torch.save(best_weights or model.state_dict(), pt_path)

    tok_path = checkpoints_dir / "ner_vocab.json"
    with open(tok_path, "w", encoding="utf-8") as f:
        json.dump(words_vocab, f, indent=2)

    return {
        "model": "BiLSTMNER",
        "best_loss": round(best_loss, 4),
        "weights_path": str(pt_path)
    }


def main():
    root = Path(__file__).resolve().parent.parent
    with open(root / "training" / "config.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    set_seed(cfg.get("seed", 42))

    data_dir = root / "training" / "data"
    checkpoints_dir = root / cfg["artifacts"]["checkpoints_dir"]
    onnx_dir = root / cfg["artifacts"]["onnx_dir"]
    checkpoints_dir.mkdir(parents=True, exist_ok=True)
    onnx_dir.mkdir(parents=True, exist_ok=True)

    with open(data_dir / "train_domain.json") as f:
        train_domain = json.load(f)
    with open(data_dir / "validation_domain.json") as f:
        val_domain = json.load(f)

    with open(data_dir / "train_logical.json") as f:
        train_logical = json.load(f)
    with open(data_dir / "validation_logical.json") as f:
        val_logical = json.load(f)

    with open(data_dir / "train_ner.json") as f:
        train_ner = json.load(f)
    with open(data_dir / "validation_ner.json") as f:
        val_ner = json.load(f)

    # 1. Train Domain Classifier
    res_domain = train_domain_classifier(train_domain, val_domain, cfg, checkpoints_dir, onnx_dir)

    # 2. Train Logical Contradiction Classifier
    res_logical = train_logical_classifier(train_logical, val_logical, cfg, checkpoints_dir, onnx_dir)

    # 3. Train Engineering NER
    res_ner = train_engineering_ner(train_ner, val_ner, cfg, checkpoints_dir)

    # 4. Sync into SpecGuard Model Registry
    registry = ModelRegistry()
    registry.scan_and_sync_artifacts()

    # 5. Save all training metrics
    all_metrics = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "domain_classifier": res_domain,
        "logical_classifier": res_logical,
        "engineering_ner": res_ner
    }
    metrics_path = root / cfg["artifacts"]["metrics_file"]
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(all_metrics, f, indent=2)

    logger.info("All models trained and synced to registry. Metrics saved to %s", metrics_path)


if __name__ == "__main__":
    main()
