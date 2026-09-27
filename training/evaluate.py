"""
SpecGuard Offline Model Evaluation Pipeline.
Evaluates trained models on the held-out 15% Test set.
Calculates Accuracy, Precision, Recall, and F1 score without tuning.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import torch
import numpy as np

from specguard.models.domain_classifier import DomainClassifierNet, SimpleTokenizer
from specguard.models.logical_classifier import LogicalRelationNet
from specguard.models.engineering_ner import (
    BiLSTMNER, RegexOffsetTokenizer, LABEL2ID, ID2LABEL, PAD_ID, O_ID, NER_LABELS
)


def evaluate_domain_classifier(test_data: List[Dict[str, Any]], checkpoints_dir: Path) -> Dict[str, Any]:
    with open(checkpoints_dir / "domain_tokenizer.json", "r", encoding="utf-8") as f:
        tok_data = json.load(f)
    tok = SimpleTokenizer.from_dict(tok_data)

    label2id = {"MECHANICAL": 0, "ELECTRICAL": 1, "CHEMICAL": 2, "GENERAL": 3}
    id2label = {v: k for k, v in label2id.items()}

    model = DomainClassifierNet(vocab_size=len(tok.word2idx) + 1, num_classes=4)
    model.load_state_dict(torch.load(checkpoints_dir / "domain_classifier.pt", map_location="cpu"))
    model.eval()


    y_true = []
    y_pred = []

    with torch.no_grad():
        for item in test_data:
            tokens = tok.encode(item["text"], max_len=128)
            t_tensor = torch.tensor([tokens], dtype=torch.long)

            logits = model(t_tensor)
            pred = torch.argmax(logits, dim=1).item()
            raw_lbl = item["label"]
            true_lbl = raw_lbl if isinstance(raw_lbl, int) else label2id.get(str(raw_lbl).upper(), 3)
            y_true.append(true_lbl)
            y_pred.append(pred)


    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    acc = float(np.mean(y_true == y_pred))

    # Per-class metrics
    classes = [0, 1, 2, 3]
    f1s = []
    for c in classes:
        tp = np.sum((y_pred == c) & (y_true == c))
        fp = np.sum((y_pred == c) & (y_true != c))
        fn = np.sum((y_pred != c) & (y_true == c))
        p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * p * r) / (p + r) if (p + r) > 0 else 0.0
        f1s.append(f1)

    macro_f1 = float(np.mean(f1s))

    return {
        "model": "DomainClassifierNet",
        "test_samples": len(test_data),
        "accuracy": round(acc, 4),
        "macro_f1": round(macro_f1, 4)
    }


def evaluate_logical_classifier(test_data: List[Dict[str, Any]], checkpoints_dir: Path) -> Dict[str, Any]:
    with open(checkpoints_dir / "logical_tokenizer.json", "r", encoding="utf-8") as f:
        tok_data = json.load(f)
    words_vocab = tok_data.get("word2idx", tok_data)

    model = LogicalRelationNet(vocab_size=len(words_vocab) + 1)


    model.load_state_dict(torch.load(checkpoints_dir / "logical_classifier.pt", map_location="cpu"))
    model.eval()

    y_true = []
    y_pred = []

    with torch.no_grad():
        for item in test_data:
            w1 = [words_vocab.get(w.lower(), 1) for w in item["text_a"].split()[:48]]
            w2 = [words_vocab.get(w.lower(), 1) for w in item["text_b"].split()[:48]]
            if len(w1) < 48:
                w1 = w1 + [0] * (48 - len(w1))
            if len(w2) < 48:
                w2 = w2 + [0] * (48 - len(w2))

            t1 = torch.tensor([w1], dtype=torch.long)
            t2 = torch.tensor([w2], dtype=torch.long)
            logits = model(t1, t2)
            pred = torch.argmax(logits, dim=1).item()
            true_lbl = item["label"]
            y_true.append(true_lbl)
            y_pred.append(pred)


    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    acc = float(np.mean(y_true == y_pred))

    tp = np.sum((y_pred == 1) & (y_true == 1))
    fp = np.sum((y_pred == 1) & (y_true == 0))
    fn = np.sum((y_pred == 0) & (y_true == 1))
    p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * p * r) / (p + r) if (p + r) > 0 else 0.0

    return {
        "model": "LogicalRelationNet",
        "test_samples": len(test_data),
        "accuracy": round(acc, 4),
        "precision": round(float(p), 4),
        "recall": round(float(r), 4),
        "f1": round(float(f1), 4)
    }


def evaluate_engineering_ner(test_data: List[Dict[str, Any]], checkpoints_dir: Path) -> Dict[str, Any]:
    with open(checkpoints_dir / "ner_vocab.json", "r", encoding="utf-8") as f:
        words_vocab = json.load(f)

    model = BiLSTMNER(vocab_size=len(words_vocab) + 1, num_labels=len(NER_LABELS))
    model.load_state_dict(torch.load(checkpoints_dir / "engineering_ner.pt", map_location="cpu"))
    model.eval()

    total_tokens = 0
    correct_tokens = 0

    with torch.no_grad():
        for item in test_data:
            tokens = RegexOffsetTokenizer.tokenize_with_offsets(item["text"])
            bio_labels = RegexOffsetTokenizer.align_entities_to_bio(tokens, item.get("entities", []), LABEL2ID)

            x_ids = [words_vocab.get(t.token.lower(), 1) for t in tokens[:64]]
            y_ids = bio_labels[:64]

            if not x_ids:
                continue

            x_t = torch.tensor([x_ids], dtype=torch.long)
            logits = model(x_t)
            preds = torch.argmax(logits, dim=2).squeeze(0).tolist()

            for pred, true in zip(preds, y_ids):
                total_tokens += 1
                if pred == true:
                    correct_tokens += 1

    token_acc = correct_tokens / total_tokens if total_tokens > 0 else 0.0

    return {
        "model": "BiLSTMNER",
        "test_samples": len(test_data),
        "token_accuracy": round(token_acc, 4)
    }


def main():
    root = Path(__file__).resolve().parent.parent
    data_dir = root / "training" / "data"
    checkpoints_dir = root / "models" / "checkpoints"

    with open(data_dir / "test_domain.json") as f:
        test_domain = json.load(f)
    with open(data_dir / "test_logical.json") as f:
        test_logical = json.load(f)
    with open(data_dir / "test_ner.json") as f:
        test_ner = json.load(f)

    results = {
        "domain_classifier": evaluate_domain_classifier(test_domain, checkpoints_dir),
        "logical_classifier": evaluate_logical_classifier(test_logical, checkpoints_dir),
        "engineering_ner": evaluate_engineering_ner(test_ner, checkpoints_dir)
    }

    out_file = root / "training" / "test_evaluation_metrics.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("=== SpecGuard Test Set Evaluation Results ===")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
