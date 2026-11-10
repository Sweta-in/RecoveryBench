#!/usr/bin/env python3
"""
RecoveryBench — Merge & Re-Split (Phase B, Step 1)

Merges newly generated ALREADY_PAID examples into the existing dataset
and re-runs 70/15/15 stratified split.

Backs up originals as train_v1.csv, val_v1.csv, test_v1.csv.
"""

import sys
import shutil
import logging
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

RANDOM_SEED = 42


def main():
    data_dir = Path(__file__).parent

    # ── Load existing splits ──
    train_path = data_dir / "train.csv"
    val_path = data_dir / "val.csv"
    test_path = data_dir / "test.csv"
    new_path = data_dir / "already_paid_generated.csv"

    if not new_path.exists():
        logger.error(f"Generated data not found: {new_path}")
        logger.error("Run generate_already_paid.py first.")
        sys.exit(1)

    # ── Backup originals ──
    for path, backup_name in [(train_path, "train_v1.csv"),
                               (val_path, "val_v1.csv"),
                               (test_path, "test_v1.csv")]:
        backup = data_dir / backup_name
        if not backup.exists():
            shutil.copy2(path, backup)
            logger.info(f"Backed up: {path.name} → {backup_name}")
        else:
            logger.info(f"Backup already exists: {backup_name}")

    # ── Load all data ──
    train_df = pd.read_csv(train_path)
    val_df = pd.read_csv(val_path)
    test_df = pd.read_csv(test_path)
    new_df = pd.read_csv(new_path)

    logger.info(f"\nExisting dataset:")
    logger.info(f"  Train: {len(train_df)}, Val: {len(val_df)}, Test: {len(test_df)}")
    logger.info(f"  Total: {len(train_df) + len(val_df) + len(test_df)}")
    logger.info(f"\nNew ALREADY_PAID data: {len(new_df)}")
    logger.info(f"  Label distribution:")
    logger.info(new_df['label'].value_counts().to_string())

    # ── Combine ──
    combined = pd.concat([train_df, val_df, test_df, new_df], ignore_index=True)

    # Drop the old 'split' column if it exists
    if 'split' in combined.columns:
        combined = combined.drop(columns=['split'])

    # Remove exact duplicates on text
    before_dedup = len(combined)
    combined = combined.drop_duplicates(subset=['text'], keep='first')
    logger.info(f"\nCombined: {before_dedup} → {len(combined)} after dedup")

    logger.info(f"\nCombined label distribution:")
    logger.info(combined['label'].value_counts().to_string())

    logger.info(f"\nCombined language distribution:")
    logger.info(combined['language'].value_counts().to_string())

    # ── Stratified split 70/15/15 ──
    # Stratify on label (not label+language — some combos may be too small)
    train_new, temp = train_test_split(
        combined,
        test_size=0.30,
        stratify=combined['label'],
        random_state=RANDOM_SEED,
    )
    val_new, test_new = train_test_split(
        temp,
        test_size=0.50,
        stratify=temp['label'],
        random_state=RANDOM_SEED,
    )

    # Add split column
    train_new = train_new.copy()
    val_new = val_new.copy()
    test_new = test_new.copy()
    train_new['split'] = 'train'
    val_new['split'] = 'val'
    test_new['split'] = 'test'

    logger.info(f"\nNew splits:")
    logger.info(f"  Train: {len(train_new)}")
    logger.info(f"  Val:   {len(val_new)}")
    logger.info(f"  Test:  {len(test_new)}")

    # Per-class per-split stats
    for split_name, df in [("Train", train_new), ("Val", val_new), ("Test", test_new)]:
        logger.info(f"\n{split_name} label distribution:")
        logger.info(df['label'].value_counts().to_string())

    # Check ALREADY_PAID per-language in test set
    ap_test = test_new[test_new['label'] == 'ALREADY_PAID']
    logger.info(f"\nALREADY_PAID in test by language:")
    logger.info(ap_test['language'].value_counts().to_string())

    # ── Save ──
    train_new.to_csv(train_path, index=False)
    val_new.to_csv(val_path, index=False)
    test_new.to_csv(test_path, index=False)

    logger.info(f"\nSaved: {train_path.name}, {val_path.name}, {test_path.name}")
    logger.info("Done!")


if __name__ == "__main__":
    main()
