"""
Domain Classification Trainer for SpecGuard.
Executes genuine local PyTorch training for document domain classification (Mechanical, Chemical, Electrical).
"""

import time
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from typing import List, Dict, Any, Callable, Optional, Tuple
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
import logging

from specguard.models.domain_classifier import DomainClassifierNet, SimpleTokenizer
from specguard.training.checkpoints import CheckpointManager
from specguard.training.hardware import HardwareManager

logger = logging.getLogger(__name__)

DOMAIN_MAP = {"mechanical": 0, "chemical": 1, "electrical": 2, "general": 3}
REV_DOMAIN_MAP = {v: k for k, v in DOMAIN_MAP.items()}


class TextClassificationDataset(Dataset):
    def __init__(self, texts: List[str], labels: List[int], tokenizer: SimpleTokenizer, max_len: int = 64):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        seq = self.tokenizer.encode(self.texts[idx], max_len=self.max_len)
        return torch.tensor(seq, dtype=torch.long), torch.tensor(self.labels[idx], dtype=torch.long)


class DomainClassifierTrainer:
    """Trains, evaluates, and checkpoints local DomainClassifierNet models."""

    def __init__(self, checkpoint_manager: Optional[CheckpointManager] = None):
        self.checkpoint_manager = checkpoint_manager or CheckpointManager()

    def train(
        self,
        train_samples: List[Dict[str, Any]],
        val_samples: List[Dict[str, Any]],
        epochs: int = 10,
        batch_size: int = 4,
        learning_rate: float = 0.001,
        device_str: str = "auto",
        progress_callback: Optional[Callable[[int, int, float, float, float, float], None]] = None
    ) -> Dict[str, Any]:
        """
        Runs real PyTorch training loop on user samples.
        No simulated metrics — calculated strictly from loss and predictions.
        """
        device = HardwareManager.get_torch_device(device_str)
        logger.info("Starting Domain Classifier training on device: %s", device)

        train_texts = [s.get("text", "") for s in train_samples if s.get("text")]
        train_labels = [DOMAIN_MAP.get(s.get("domain", "general").lower(), 3) for s in train_samples if s.get("text")]

        val_texts = [s.get("text", "") for s in val_samples if s.get("text")]
        val_labels = [DOMAIN_MAP.get(s.get("domain", "general").lower(), 3) for s in val_samples if s.get("text")]

        if not train_texts:
            raise ValueError("Insufficient training data: No text samples provided.")

        # Fit tokenizer
        tokenizer = SimpleTokenizer(max_vocab=3000)
        tokenizer.fit(train_texts + val_texts)

        train_dataset = TextClassificationDataset(train_texts, train_labels, tokenizer)
        val_dataset = TextClassificationDataset(val_texts or train_texts, val_labels or train_labels, tokenizer)

        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

        model = DomainClassifierNet(vocab_size=len(tokenizer.word2idx), num_classes=4).to(device)
        criterion = nn.CrossEntropyLoss()
        optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=1e-4)

        best_val_f1 = -1.0
        best_metrics = {}
        history = []

        for epoch in range(1, epochs + 1):
            model.train()
            total_train_loss = 0.0

            for x_batch, y_batch in train_loader:
                x_batch, y_batch = x_batch.to(device), y_batch.to(device)
                optimizer.zero_grad()
                logits = model(x_batch)
                loss = criterion(logits, y_batch)
                loss.backward()
                optimizer.step()
                total_train_loss += loss.item()

            avg_train_loss = total_train_loss / max(1, len(train_loader))

            # Validation step
            model.eval()
            total_val_loss = 0.0
            all_preds, all_targets = [], []

            with torch.no_grad():
                for x_batch, y_batch in val_loader:
                    x_batch, y_batch = x_batch.to(device), y_batch.to(device)
                    logits = model(x_batch)
                    v_loss = criterion(logits, y_batch)
                    total_val_loss += v_loss.item()
                    preds = torch.argmax(logits, dim=1).cpu().tolist()
                    all_preds.extend(preds)
                    all_targets.extend(y_batch.cpu().tolist())

            avg_val_loss = total_val_loss / max(1, len(val_loader))
            acc = accuracy_score(all_targets, all_preds) if all_targets else 0.0
            _, _, f1, _ = precision_recall_fscore_support(all_targets, all_preds, average='macro', zero_division=0)

            history.append({
                "epoch": epoch,
                "train_loss": round(avg_train_loss, 4),
                "val_loss": round(avg_val_loss, 4),
                "val_accuracy": round(acc, 4),
                "val_f1": round(f1, 4)
            })

            if progress_callback:
                progress_callback(epoch, epochs, avg_train_loss, avg_val_loss, acc, f1)

            if f1 > best_val_f1:
                best_val_f1 = f1
                best_metrics = {
                    "accuracy": round(acc, 4),
                    "f1_score": round(f1, 4),
                    "val_loss": round(avg_val_loss, 4),
                    "epoch": epoch
                }
                # Save best checkpoint
                ckpt_path = self.checkpoint_manager.save_checkpoint(
                    model=model,
                    tokenizer=tokenizer,
                    task_name="domain_classifier",
                    domain="cross_domain",
                    metrics=best_metrics,
                    hyperparams={
                        "epochs": epochs,
                        "batch_size": batch_size,
                        "learning_rate": learning_rate,
                        "device": str(device)
                    }
                )

        return {
            "best_metrics": best_metrics,
            "checkpoint_path": ckpt_path,
            "history": history
        }
