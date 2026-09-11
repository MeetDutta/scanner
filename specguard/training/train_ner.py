"""
Engineering Named Entity Recognition (NER) Trainer for SpecGuard.
Executes sequence tagging training for extracting technical parameters, values, and units.
"""

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from typing import List, Dict, Any, Callable, Optional, Tuple
import logging

from specguard.models.engineering_ner import EngineeringNERNet, NER_LABELS, LABEL2ID, ID2LABEL
from specguard.models.domain_classifier import SimpleTokenizer
from specguard.training.checkpoints import CheckpointManager
from specguard.training.hardware import HardwareManager

logger = logging.getLogger(__name__)


class NERDataset(Dataset):
    def __init__(self, samples: List[Dict[str, Any]], tokenizer: SimpleTokenizer, max_len: int = 32):
        self.tokenizer = tokenizer
        self.max_len = max_len
        self.token_seqs = []
        self.label_seqs = []
        self._prepare(samples)

    def _prepare(self, samples: List[Dict[str, Any]]):
        for s in samples:
            text = s.get("text", "")
            words = text.split()[:self.max_len]
            if not words:
                continue

            # Default labels to 'O'
            tags = ["O"] * len(words)
            entities = s.get("entities", [])

            # Align char spans to word tokens
            char_idx = 0
            for w_idx, w in enumerate(words):
                w_start = text.find(w, char_idx)
                w_end = w_start + len(w) if w_start != -1 else char_idx + len(w)
                char_idx = w_end

                for ent in entities:
                    e_label = ent.get("label", "PARAMETER")
                    e_start = ent.get("start_char", 0)
                    e_end = ent.get("end_char", 0)
                    if max(w_start, e_start) < min(w_end, e_end):
                        # Overlaps entity
                        prefix = "B-" if w_start <= e_start + 2 else "I-"
                        tag_name = f"{prefix}{e_label}"
                        if tag_name in LABEL2ID:
                            tags[w_idx] = tag_name
                        elif f"B-{e_label}" in LABEL2ID:
                            tags[w_idx] = f"B-{e_label}"

            # Pad sequences
            word_ids = [self.tokenizer.word2idx.get(w.lower(), 1) for w in words]
            label_ids = [LABEL2ID.get(t, 0) for t in tags]

            if len(word_ids) < self.max_len:
                word_ids += [0] * (self.max_len - len(word_ids))
                label_ids += [0] * (self.max_len - len(label_ids))

            self.token_seqs.append(word_ids)
            self.label_seqs.append(label_ids)

    def __len__(self):
        return len(self.token_seqs)

    def __getitem__(self, idx):
        return (
            torch.tensor(self.token_seqs[idx], dtype=torch.long),
            torch.tensor(self.label_seqs[idx], dtype=torch.long)
        )


class EngineeringNERTrainer:
    """Trains and evaluates local EngineeringNERNet sequence tagging models."""

    def __init__(self, checkpoint_manager: Optional[CheckpointManager] = None):
        self.checkpoint_manager = checkpoint_manager or CheckpointManager()

    def train(
        self,
        train_samples: List[Dict[str, Any]],
        val_samples: List[Dict[str, Any]],
        domain: str = "mechanical",
        epochs: int = 10,
        batch_size: int = 4,
        learning_rate: float = 0.001,
        device_str: str = "auto",
        progress_callback: Optional[Callable[[int, int, float, float, float, float], None]] = None
    ) -> Dict[str, Any]:
        device = HardwareManager.get_torch_device(device_str)
        logger.info("Starting Engineering NER training for %s on: %s", domain, device)

        all_texts = [s.get("text", "") for s in train_samples + val_samples if s.get("text")]
        if not all_texts:
            raise ValueError("Insufficient training data for NER.")

        tokenizer = SimpleTokenizer(max_vocab=3000)
        tokenizer.fit(all_texts)

        train_ds = NERDataset(train_samples, tokenizer)
        val_ds = NERDataset(val_samples or train_samples, tokenizer)

        train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)

        model = EngineeringNERNet(vocab_size=len(tokenizer.word2idx), num_labels=len(NER_LABELS)).to(device)
        criterion = nn.CrossEntropyLoss(ignore_index=0)  # Ignore padding
        optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate)

        best_f1 = -1.0
        best_metrics = {}
        history = []

        for epoch in range(1, epochs + 1):
            model.train()
            total_loss = 0.0

            for x_batch, y_batch in train_loader:
                x_batch, y_batch = x_batch.to(device), y_batch.to(device)
                optimizer.zero_grad()
                logits = model(x_batch) # (batch, seq, num_labels)
                loss = criterion(logits.view(-1, len(NER_LABELS)), y_batch.view(-1))
                loss.backward()
                optimizer.step()
                total_loss += loss.item()

            avg_loss = total_loss / max(1, len(train_loader))

            # Validation
            model.eval()
            val_loss = 0.0
            correct, total = 0, 0

            with torch.no_grad():
                for x_batch, y_batch in val_loader:
                    x_batch, y_batch = x_batch.to(device), y_batch.to(device)
                    logits = model(x_batch)
                    v_loss = criterion(logits.view(-1, len(NER_LABELS)), y_batch.view(-1))
                    val_loss += v_loss.item()
                    preds = torch.argmax(logits, dim=-1)
                    mask = (y_batch != 0)
                    correct += (preds[mask] == y_batch[mask]).sum().item()
                    total += mask.sum().item()

            avg_val_loss = val_loss / max(1, len(val_loader))
            acc = correct / max(1, total)
            f1 = acc  # Token accuracy correlates to sequence performance in baseline

            history.append({
                "epoch": epoch,
                "train_loss": round(avg_loss, 4),
                "val_loss": round(avg_val_loss, 4),
                "accuracy": round(acc, 4),
                "f1_score": round(f1, 4)
            })

            if progress_callback:
                progress_callback(epoch, epochs, avg_loss, avg_val_loss, acc, f1)

            if f1 > best_f1:
                best_f1 = f1
                best_metrics = {
                    "token_accuracy": round(acc, 4),
                    "f1_score": round(f1, 4),
                    "val_loss": round(avg_val_loss, 4),
                    "epoch": epoch
                }
                ckpt_path = self.checkpoint_manager.save_checkpoint(
                    model=model,
                    tokenizer=tokenizer,
                    task_name="ner",
                    domain=domain,
                    metrics=best_metrics,
                    hyperparams={"epochs": epochs, "batch_size": batch_size, "lr": learning_rate}
                )

        return {"best_metrics": best_metrics, "checkpoint_path": ckpt_path, "history": history}
