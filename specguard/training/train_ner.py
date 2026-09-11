"""
Engineering Named Entity Recognition (NER) Trainer for SpecGuard.
Implements offset-aligned token sequences, attention masking, separate PAD/O token IDs,
leakage-free train-only tokenizer fitting, and held-out test set evaluation.
"""

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from typing import List, Dict, Any, Callable, Optional, Tuple
from collections import defaultdict
from pathlib import Path
import logging
from sklearn.metrics import precision_recall_fscore_support, accuracy_score, confusion_matrix

from specguard.models.engineering_ner import (
    EngineeringNERNet, RegexOffsetTokenizer, NER_LABELS, LABEL2ID, ID2LABEL, PAD_ID, O_ID
)
from specguard.models.domain_classifier import SimpleTokenizer
from specguard.training.checkpoints import CheckpointManager
from specguard.training.hardware import HardwareManager

logger = logging.getLogger(__name__)


class NERDataset(Dataset):
    """
    Dataset for token classification with exact character offset alignment and attention masks.
    """
    def __init__(self, samples: List[Dict[str, Any]], tokenizer: SimpleTokenizer, max_len: int = 64):
        self.tokenizer = tokenizer
        self.max_len = max_len
        self.token_seqs: List[List[int]] = []
        self.label_seqs: List[List[int]] = []
        self.mask_seqs: List[List[int]] = []
        self.raw_tokens: List[List[str]] = []
        self._prepare(samples)

    def _prepare(self, samples: List[Dict[str, Any]]):
        for s in samples:
            text = s.get("text", "")
            if not text.strip():
                continue

            # 1. Extract tokens with exact character boundaries
            token_offsets = RegexOffsetTokenizer.tokenize_with_offsets(text)[:self.max_len]
            if not token_offsets:
                continue

            # 2. Align ground-truth entities to BIO labels
            entities = s.get("entities", [])
            tag_ids = RegexOffsetTokenizer.align_entities_to_bio(token_offsets, entities, LABEL2ID)

            # 3. Convert tokens to vocabulary indices
            tok_words = [t.token for t in token_offsets]
            word_ids = [self.tokenizer.word2idx.get(w.lower(), 1) for w in tok_words]
            mask = [1] * len(word_ids)

            # 4. Pad sequence up to max_len
            if len(word_ids) < self.max_len:
                pad_len = self.max_len - len(word_ids)
                word_ids += [PAD_ID] * pad_len
                tag_ids += [PAD_ID] * pad_len
                mask += [0] * pad_len

            self.token_seqs.append(word_ids)
            self.label_seqs.append(tag_ids)
            self.mask_seqs.append(mask)
            self.raw_tokens.append(tok_words)

    def __len__(self):
        return len(self.token_seqs)

    def __getitem__(self, idx):
        return (
            torch.tensor(self.token_seqs[idx], dtype=torch.long),
            torch.tensor(self.label_seqs[idx], dtype=torch.long),
            torch.tensor(self.mask_seqs[idx], dtype=torch.long)
        )


class EngineeringNERTrainer:
    """Trains and evaluates local EngineeringNERNet sequence tagging models with zero data leakage."""

    def __init__(self, checkpoint_manager: Optional[CheckpointManager] = None):
        self.checkpoint_manager = checkpoint_manager or CheckpointManager()

    def train(
        self,
        train_samples: List[Dict[str, Any]],
        val_samples: List[Dict[str, Any]],
        test_samples: Optional[List[Dict[str, Any]]] = None,
        domain: str = "mechanical",
        epochs: int = 8,
        batch_size: int = 4,
        learning_rate: float = 0.001,
        device_str: str = "auto",
        progress_callback: Optional[Callable[[int, int, float, float, float, float], None]] = None
    ) -> Dict[str, Any]:
        device = HardwareManager.get_torch_device(device_str)
        logger.info("Starting Engineering NER training for domain '%s' on %s", domain, device)

        # STRICT DATA LEAKAGE PREVENTION: Fit tokenizer ONLY on training samples
        train_texts = [s.get("text", "") for s in train_samples if s.get("text")]
        if not train_texts:
            raise ValueError("Insufficient training data: Training split contains no text samples.")

        tokenizer = SimpleTokenizer(max_vocab=3000)
        tokenizer.fit(train_texts)

        train_ds = NERDataset(train_samples, tokenizer)
        val_ds = NERDataset(val_samples or train_samples, tokenizer)
        test_ds = NERDataset(test_samples, tokenizer) if test_samples else None

        train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)
        test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False) if test_ds else None

        model = EngineeringNERNet(
            vocab_size=len(tokenizer.word2idx),
            num_labels=len(NER_LABELS)
        ).to(device)

        # Ignore PAD_ID (0) in cross-entropy loss, ensuring O_ID (1) is genuinely learned
        criterion = nn.CrossEntropyLoss(ignore_index=PAD_ID)
        optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=1e-4)

        best_val_f1 = -1.0
        best_metrics: Dict[str, Any] = {}
        best_state = None
        history: List[Dict[str, Any]] = []

        for epoch in range(1, epochs + 1):
            model.train()
            total_loss = 0.0

            for x_batch, y_batch, mask_batch in train_loader:
                x_batch, y_batch, mask_batch = x_batch.to(device), y_batch.to(device), mask_batch.to(device)
                optimizer.zero_grad()

                logits = model(x_batch, attention_mask=mask_batch)  # (batch, seq, num_labels)
                loss = criterion(logits.view(-1, len(NER_LABELS)), y_batch.view(-1))
                loss.backward()
                optimizer.step()
                total_loss += loss.item()

            avg_train_loss = total_loss / max(1, len(train_loader))

            # Validation step (Model selection)
            val_metrics = self._evaluate_dataset(model, val_loader, device)
            val_loss = val_metrics["loss"]
            val_acc = val_metrics["accuracy"]
            val_f1 = val_metrics["f1_macro"]

            history.append({
                "epoch": epoch,
                "train_loss": round(avg_train_loss, 4),
                "val_loss": round(val_loss, 4),
                "val_accuracy": round(val_acc, 4),
                "val_f1": round(val_f1, 4)
            })

            if progress_callback:
                progress_callback(epoch, epochs, avg_train_loss, val_loss, val_acc, val_f1)

            if val_f1 >= best_val_f1:
                best_val_f1 = val_f1
                best_metrics = val_metrics
                best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}

        # Load best model for saving and held-out test evaluation
        if best_state is not None:
            model.load_state_dict(best_state)

        # Held-out Test Set Evaluation (Unbiased final research report)
        test_metrics: Dict[str, Any] = {}
        if test_loader is not None and len(test_loader) > 0:
            test_metrics = self._evaluate_dataset(model, test_loader, device)
            logger.info("Final Held-Out Test Evaluation: Accuracy=%.4f, Macro F1=%.4f",
                        test_metrics.get("accuracy", 0.0), test_metrics.get("f1_macro", 0.0))

        # Save versioned checkpoint
        ckpt_path = self.checkpoint_manager.save_checkpoint(
            model=model,
            tokenizer=tokenizer,
            task_name="ner",
            domain=domain,
            metrics={
                "validation": best_metrics,
                "test": test_metrics
            },
            hyperparams={
                "epochs": epochs,
                "batch_size": batch_size,
                "learning_rate": learning_rate,
                "device": str(device)
            }
        )

        return {
            "model_id": Path(ckpt_path).stem,
            "model": model,
            "validation_metrics": best_metrics,
            "test_metrics": test_metrics,
            "metrics": test_metrics or best_metrics,
            "best_metrics": test_metrics or best_metrics,
            "checkpoint_path": ckpt_path,
            "history": history
        }

    def _evaluate_dataset(
        self,
        model: nn.Module,
        loader: DataLoader,
        device: torch.device
    ) -> Dict[str, Any]:
        """Calculates token-level and entity-level metrics strictly excluding padded positions."""
        model.eval()
        criterion = nn.CrossEntropyLoss(ignore_index=PAD_ID)
        total_loss = 0.0

        all_preds: List[int] = []
        all_targets: List[int] = []

        with torch.no_grad():
            for x_batch, y_batch, mask_batch in loader:
                x_batch, y_batch, mask_batch = x_batch.to(device), y_batch.to(device), mask_batch.to(device)
                logits = model(x_batch, attention_mask=mask_batch)
                loss = criterion(logits.view(-1, len(NER_LABELS)), y_batch.view(-1))
                total_loss += loss.item()

                preds = torch.argmax(logits, dim=-1)  # (batch, seq)

                # Filter out padding positions using attention_mask
                for p_seq, t_seq, m_seq in zip(preds, y_batch, mask_batch):
                    for p, t, m in zip(p_seq.tolist(), t_seq.tolist(), m_seq.tolist()):
                        if m == 1:  # Non-padded token
                            all_preds.append(p)
                            all_targets.append(t)

        avg_loss = total_loss / max(1, len(loader))
        if not all_targets:
            return {"loss": avg_loss, "accuracy": 0.0, "f1_macro": 0.0, "f1_weighted": 0.0}

        acc = float(accuracy_score(all_targets, all_preds))
        p_mac, r_mac, f1_mac, _ = precision_recall_fscore_support(
            all_targets, all_preds, average="macro", zero_division=0
        )
        p_wgt, r_wgt, f1_wgt, _ = precision_recall_fscore_support(
            all_targets, all_preds, average="weighted", zero_division=0
        )

        # Per-class metrics
        per_class_p, per_class_r, per_class_f1, _ = precision_recall_fscore_support(
            all_targets, all_preds, labels=list(range(len(NER_LABELS))), zero_division=0
        )
        per_class_metrics: Dict[str, Dict[str, float]] = {}
        for idx, lbl in enumerate(NER_LABELS):
            if idx == PAD_ID:
                continue
            per_class_metrics[lbl] = {
                "precision": round(float(per_class_p[idx]), 4),
                "recall": round(float(per_class_r[idx]), 4),
                "f1": round(float(per_class_f1[idx]), 4),
            }

        return {
            "loss": round(avg_loss, 4),
            "accuracy": round(acc, 4),
            "precision_macro": round(float(p_mac), 4),
            "recall_macro": round(float(r_mac), 4),
            "f1_macro": round(float(f1_mac), 4),
            "precision_weighted": round(float(p_wgt), 4),
            "recall_weighted": round(float(r_wgt), 4),
            "f1_weighted": round(float(f1_wgt), 4),
            "per_class": per_class_metrics
        }
