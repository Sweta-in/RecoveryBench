#!/usr/bin/env python3
"""
RecoveryBench — Intent Classifier Training Entry Point

Usage:
    python models/train_intent_classifier.py

Trains the TF-IDF + Logistic Regression intent classifier on the
prepared dataset and saves model artifacts + evaluation outputs.
"""

import sys
from pathlib import Path

# Ensure project root is on path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from models.intent_classifier.train import main as train_main


if __name__ == "__main__":
    status, metrics = train_main()
    print(f"\n{'='*60}")
    print(f"Final Status: {status}")
    print(f"Test Macro F1: {metrics['test_f1']:.4f}")
    print(f"Test Accuracy: {metrics['test_accuracy']:.4f}")
    print(f"{'='*60}")

    # Exit with non-zero if FAIL
    if status == "FAIL":
        sys.exit(1)
