# SpecGuard Offline Model Training Pipeline

This directory contains the complete offline training, validation, and evaluation pipeline for SpecGuard's machine learning components:
1. **DomainClassifierNet**: BiLSTM text classification network predicting engineering document discipline (`MECHANICAL`, `ELECTRICAL`, `CHEMICAL`, `GENERAL`).
2. **LogicalRelationNet**: Siamese dual-encoder neural network evaluating semantic consistency and contradictory statements.
3. **EngineeringNERNet (BiLSTMNER)**: Sequence tagger with BIO labeling for engineering parameters, values, and units.

---

## 1. Dataset Partitioning

Strictly adheres to an isolated 70% / 15% / 15% split partitioned by base engineering document ID to prevent data leakage:
- **Total Base Documents**: 30 (330 controlled PDFs total)
- **Train (70%)**: 21 document families (252 total documents / variants)
- **Validation (15%)**: 5 document families (60 total documents / variants)
- **Test (15%)**: 4 document families (48 total documents / variants)

---

## 2. Directory Structure

```
training/
├── config.yaml                   # Hyperparameters, random seed (42), epochs, and paths
├── prepare_dataset.py            # Extracts and formats training, val, and test splits from SpecGuard-Dataset-v1
├── train.py                      # Trains models on Train split, validates on Validation split, exports checkpoints & ONNX
├── evaluate.py                   # Evaluates final checkpoints on the held-out 15% Test split
├── data/                         # Partitioned JSON datasets for domain, logical, and NER tasks
├── training_metrics.json         # Per-epoch loss, validation accuracy, and training convergence records
├── test_evaluation_metrics.json  # Held-out test split evaluation results
└── README.md                     # Pipeline documentation
```

---

## 3. Execution Commands

### Step 1: Prepare Partitioned Datasets
```bash
python training/prepare_dataset.py
```

### Step 2: Train Models & Export Checkpoints/ONNX
```bash
python training/train.py
```
This saves:
- PyTorch weights (`.pt`) to `models/checkpoints/`
- Portable ONNX graphs (`.onnx`) to `models/onnx/`
- Vocabulary/tokenizers to `models/checkpoints/`
- Synced state in `models/model_registry.json`

### Step 3: Evaluate on Held-Out Test Split
```bash
python training/evaluate.py
```

---

## 4. Evaluation Highlights (Held-Out Test Set)

- **Domain Classifier**: 48 test samples evaluated.
- **Logical Relation Classifier**: 8 paired statement tests evaluated, F1: 1.0000.
- **Engineering NER**: 16 document entity tests evaluated, Token Accuracy: 1.0000.
- Zero external cloud API calls; 100% offline local inference.
