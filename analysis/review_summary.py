import pandas as pd
import numpy as np
import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Load data
df = pd.read_csv('analysis/hard_examples.csv')
wrong = df[df['correct'] == False].copy()

# Top 10 confused class pairs
pairs = wrong.groupby(['true_label', 'predicted_label']).size().reset_index(name='count')
pairs = pairs.sort_values('count', ascending=False).head(10)
print("=== TOP 10 CONFUSED CLASS PAIRS ===")
for _, row in pairs.iterrows():
    print(f"  {row['true_label']:16s} -> {row['predicted_label']:16s}  ({row['count']} cases)")

# Top 20 highest-confidence mistakes
print("\n=== TOP 20 HIGHEST-CONFIDENCE MISTAKES ===")
top20 = wrong.nlargest(20, 'confidence')
for i, (_, row) in enumerate(top20.iterrows(), 1):
    text = str(row['text'])[:65].encode('ascii', 'replace').decode('ascii')
    print(f"  {i:2d}. [{row['confidence']:.4f}] {row['true_label']:16s} -> {row['predicted_label']:16s} | {row['language']:8s} | {text}")

# Labeling issues - high confidence mistakes that suggest wrong labels
print("\n=== LIKELY LABELING ISSUES (confidence > 0.6, excluding ALREADY_PAID) ===")
labeling = wrong[(wrong['confidence'] > 0.6) & (wrong['true_label'] != 'ALREADY_PAID')]
for _, row in labeling.iterrows():
    text = str(row['text'])[:70].encode('ascii', 'replace').decode('ascii')
    print(f"  [{row['confidence']:.4f}] True={row['true_label']:16s} Pred={row['predicted_label']:16s} | {text}")

# Also check ALREADY_PAID that look like they might be mislabeled
print("\n=== ALREADY_PAID EXAMPLES THAT LOOK LIKE OTHER CLASSES ===")
ap = wrong[wrong['true_label'] == 'ALREADY_PAID'].nlargest(10, 'confidence')
for _, row in ap.iterrows():
    text = str(row['text'])[:70].encode('ascii', 'replace').decode('ascii')
    print(f"  [{row['confidence']:.4f}] Pred={row['predicted_label']:16s} | {text}")
