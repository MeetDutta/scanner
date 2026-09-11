"""
Logical Consistency & Contradiction Trainer for SpecGuard.
Trains the Siamese LogicalRelationNet to detect cross-document engineering contradictions.
"""

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from typing import List, Dict, Any, Callable, Optional, Tuple
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
import logging

from specguard.models.logical_classifier import LogicalRelationNet
from specguard.models.domain_classifier import SimpleTokenizer
from specguard.training.checkpoints import CheckpointManager
from specguard.training.hardware import HardwareManager

logger = logging.getLogger(__name__)


class StatementPairDataset(Dataset):
    def __init__(self, pairs: List[Tuple[str, str, int]], tokenizer: SimpleTokenizer, max_len: int = 48):
        self.pairs = pairs
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.pairs)

    def __getitem__(self, idx):
        t1, t2, label = self.pairs[idx]
        s1 = torch.tensor(self.tokenizer.encode(t1, max_len=self.max_len), dtype=torch.long)
        s2 = torch.tensor(self.tokenizer.encode(t2, max_len=self.max_len), dtype=torch.long)
        y = torch.tensor(label, dtype=torch.long)
        return s1, s2, y


class LogicalTrainer:
    """Trains and evaluates Siamese neural networks for detecting technical contradictions."""

    def __init__(self, checkpoint_manager: Optional[CheckpointManager] = None):
        self.checkpoint_manager = checkpoint_manager or CheckpointManager()

    def train(
        self,
        samples: List[Dict[str, Any]],
        domain: str = "cross_domain",
        epochs: int = 8,
        batch_size: int = 4,
        learning_rate: float = 0.001,
        device_str: str = "auto",
        progress_callback: Optional[Callable[[int, int, float, float, float, float], None]] = None
    ) -> Dict[str, Any]:
        device = HardwareManager.get_torch_device(device_str)
        logger.info("Starting Logical Contradiction training on %s", device)

        # Build pair dataset
        pairs = []
        all_texts = []
        for s in samples:
            t1 = s.get("text", "")
            t2 = s.get("statement_b", "")
            lbl_str = s.get("logical_label", "CONSISTENT")
            label = 1 if lbl_str == "CONTRADICTORY" else 0
            if t1 and t2:
                pairs.append((t1, t2, label))
                all_texts.extend([t1, t2])

        if not pairs:
            # Create baseline pairs if insufficient
            pairs = [
                ("Maximum temperature = 80 C", "Maximum temperature = 60 C", 1),
                ("Operating voltage is 415 V", "System operates at 415 V", 0),
                ("Tolerance = 0.05 mm", "Tolerance is 0.5 mm", 1),
                ("Supply frequency = 50 Hz", "Frequency rated at 50 Hz", 0)
            ]
            all_texts = [p[0] for p in pairs] + [p[1] for p in pairs]

        tokenizer = SimpleTokenizer(max_vocab=3000)
        tokenizer.fit(all_texts)

        dataset = StatementPairDataset(pairs, tokenizer)
        loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

        model = LogicalRelationNet(vocab_size=len(tokenizer.word2idx)).to(device)
        criterion = nn.CrossEntropyLoss()
        optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate)

        best_f1 = -1.0
        best_metrics = {}
        history = []

        for epoch in range(1, epochs + 1):
            model.train()
            total_loss = 0.0
            all_preds, all_targets = [], []

            for s1, s2, y in loader:
                s1, s2, y = s1.to(device), s2.to(device), y.to(device)
                optimizer.zero_grad()
                logits = model(s1, s2)
                loss = criterion(logits, y)
                loss.backward()
                optimizer.step()
                total_loss += loss.item()
                all_preds.extend(torch.argmax(logits, dim=1).cpu().tolist())
                all_targets.extend(y.cpu().tolist())

            avg_loss = total_loss / max(1, len(loader))
            acc = accuracy_score(all_targets, all_preds)
            _, _, f1, _ = precision_recall_fscore_support(all_targets, all_preds, average='macro', zero_division=0)

            history.append({
                "epoch": epoch,
                "loss": round(avg_loss, 4),
                "accuracy": round(acc, 4),
                "f1_score": round(f1, 4)
            })

            if progress_callback:
                progress_callback(epoch, epochs, avg_loss, avg_loss, acc, f1)

            if f1 > best_f1:
                best_f1 = f1
                best_metrics = {"accuracy": round(acc, 4), "f1_score": round(f1, 4), "epoch": epoch}
                ckpt_path = self.checkpoint_manager.save_checkpoint(
                    model=model,
                    tokenizer=tokenizer,
                    task_name="logical",
                    domain=domain,
                    metrics=best_metrics,
                    hyperparams={"epochs": epochs, "lr": learning_rate}
                )

        return {"best_metrics": best_metrics, "checkpoint_path": ckpt_path, "history": history}


from typing import Tuple
