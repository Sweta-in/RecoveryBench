#!/usr/bin/env python3
"""
RecoveryBench — Exploratory Data Analysis

Generates:
    - data/plots/class_distribution.png
    - data/plots/language_distribution.png
    - data/plots/message_length_by_class.png

Reads from data/train.csv, data/val.csv, data/test.csv.
"""

import os
import sys
import logging
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Styling
plt.rcParams.update({
    "figure.facecolor": "#f8f9fa",
    "axes.facecolor": "#ffffff",
    "axes.edgecolor": "#dee2e6",
    "axes.grid": True,
    "grid.alpha": 0.3,
    "font.size": 11,
    "font.family": "sans-serif",
})

# Color palettes
CLASS_COLORS = {
    "LIKELY_PAY": "#2ecc71",
    "NEEDS_REMINDER": "#f39c12",
    "DISPUTE": "#e74c3c",
    "HIGH_RISK": "#9b59b6",
    "VAGUE": "#3498db",
    "ALREADY_PAID": "#1abc9c",
}

LANG_COLORS = {
    "English": "#1abc9c",
    "Hindi": "#e67e22",
    "Bengali": "#e74c3c",
    "Hinglish": "#9b59b6",
}

SPLIT_COLORS = {
    "train": "#3498db",
    "val": "#f39c12",
    "test": "#e74c3c",
}


def load_data(data_dir: Path) -> pd.DataFrame:
    """Load and combine all split CSVs."""
    dfs = []
    for split in ["train", "val", "test"]:
        filepath = data_dir / f"{split}.csv"
        if not filepath.exists():
            logger.error(f"Missing: {filepath}")
            sys.exit(1)
        df = pd.read_csv(filepath)
        dfs.append(df)
    combined = pd.concat(dfs, ignore_index=True)
    combined["text_length"] = combined["text"].astype(str).apply(len)
    logger.info(f"Loaded {len(combined)} total rows across {len(dfs)} splits")
    return combined


def plot_class_distribution(df: pd.DataFrame, output_path: Path):
    """Bar chart of class distribution, stacked by split."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Left: Overall class distribution
    ax1 = axes[0]
    class_counts = df["label"].value_counts().reindex(CLASS_COLORS.keys())
    bars = ax1.bar(
        range(len(class_counts)),
        class_counts.values,
        color=[CLASS_COLORS[c] for c in class_counts.index],
        edgecolor="white",
        linewidth=0.8,
    )
    ax1.set_xticks(range(len(class_counts)))
    ax1.set_xticklabels(class_counts.index, rotation=30, ha="right", fontsize=9)
    ax1.set_ylabel("Count")
    ax1.set_title("Class Distribution (Overall)", fontweight="bold", fontsize=13)

    # Add count labels
    for bar, count in zip(bars, class_counts.values):
        ax1.text(
            bar.get_x() + bar.get_width() / 2, bar.get_height() + 5,
            str(count), ha="center", va="bottom", fontsize=9, fontweight="bold"
        )

    # Right: Class × Split distribution
    ax2 = axes[1]
    classes = list(CLASS_COLORS.keys())
    splits = ["train", "val", "test"]
    x = np.arange(len(classes))
    width = 0.25

    for i, split in enumerate(splits):
        split_df = df[df["split"] == split]
        counts = [len(split_df[split_df["label"] == c]) for c in classes]
        ax2.bar(
            x + i * width, counts, width,
            label=split.capitalize(),
            color=SPLIT_COLORS[split],
            edgecolor="white",
            linewidth=0.5,
        )

    ax2.set_xticks(x + width)
    ax2.set_xticklabels(classes, rotation=30, ha="right", fontsize=9)
    ax2.set_ylabel("Count")
    ax2.set_title("Class Distribution by Split", fontweight="bold", fontsize=13)
    ax2.legend()

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Saved: {output_path}")


def plot_language_distribution(df: pd.DataFrame, output_path: Path):
    """Bar chart of language distribution + language × class heatmap."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Left: Language distribution
    ax1 = axes[0]
    lang_counts = df["language"].value_counts().reindex(LANG_COLORS.keys())
    bars = ax1.bar(
        range(len(lang_counts)),
        lang_counts.values,
        color=[LANG_COLORS[l] for l in lang_counts.index],
        edgecolor="white",
        linewidth=0.8,
    )
    ax1.set_xticks(range(len(lang_counts)))
    ax1.set_xticklabels(lang_counts.index, fontsize=10)
    ax1.set_ylabel("Count")
    ax1.set_title("Language Distribution (Overall)", fontweight="bold", fontsize=13)

    for bar, count in zip(bars, lang_counts.values):
        ax1.text(
            bar.get_x() + bar.get_width() / 2, bar.get_height() + 5,
            str(count), ha="center", va="bottom", fontsize=9, fontweight="bold"
        )

    # Right: Language × Class heatmap
    ax2 = axes[1]
    classes = list(CLASS_COLORS.keys())
    languages = list(LANG_COLORS.keys())
    matrix = np.zeros((len(languages), len(classes)))

    for i, lang in enumerate(languages):
        for j, cls in enumerate(classes):
            matrix[i, j] = len(df[(df["language"] == lang) & (df["label"] == cls)])

    im = ax2.imshow(matrix, cmap="YlOrRd", aspect="auto")
    ax2.set_xticks(range(len(classes)))
    ax2.set_yticks(range(len(languages)))
    ax2.set_xticklabels(classes, rotation=30, ha="right", fontsize=9)
    ax2.set_yticklabels(languages, fontsize=10)
    ax2.set_title("Language × Class Count", fontweight="bold", fontsize=13)

    # Add text annotations
    for i in range(len(languages)):
        for j in range(len(classes)):
            ax2.text(
                j, i, f"{int(matrix[i, j])}",
                ha="center", va="center", fontsize=9, fontweight="bold",
                color="white" if matrix[i, j] > matrix.max() * 0.6 else "black"
            )

    plt.colorbar(im, ax=ax2, shrink=0.8)
    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Saved: {output_path}")


def plot_message_length(df: pd.DataFrame, output_path: Path):
    """Box plot + histogram of message length by class."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    classes = list(CLASS_COLORS.keys())

    # Left: Box plot
    ax1 = axes[0]
    data_by_class = [df[df["label"] == cls]["text_length"].values for cls in classes]
    bp = ax1.boxplot(
        data_by_class,
        labels=classes,
        patch_artist=True,
        medianprops=dict(color="black", linewidth=1.5),
    )
    for patch, cls in zip(bp["boxes"], classes):
        patch.set_facecolor(CLASS_COLORS[cls])
        patch.set_alpha(0.7)
    ax1.set_xticklabels(classes, rotation=30, ha="right", fontsize=9)
    ax1.set_ylabel("Character Count")
    ax1.set_title("Message Length by Class", fontweight="bold", fontsize=13)

    # Right: Overlaid histograms
    ax2 = axes[1]
    for cls in classes:
        lengths = df[df["label"] == cls]["text_length"]
        ax2.hist(
            lengths, bins=30, alpha=0.5,
            label=cls, color=CLASS_COLORS[cls],
            edgecolor="white", linewidth=0.5,
        )
    ax2.set_xlabel("Character Count")
    ax2.set_ylabel("Frequency")
    ax2.set_title("Message Length Distribution", fontweight="bold", fontsize=13)
    ax2.legend(fontsize=8)

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Saved: {output_path}")


def main():
    data_dir = Path(__file__).parent
    plots_dir = data_dir / "plots"
    plots_dir.mkdir(exist_ok=True)

    df = load_data(data_dir)

    # Print summary stats
    logger.info("\n=== Dataset Summary ===")
    logger.info(f"Total rows: {len(df)}")
    logger.info(f"Splits: {df['split'].value_counts().to_dict()}")
    logger.info(f"Classes: {df['label'].value_counts().to_dict()}")
    logger.info(f"Languages: {df['language'].value_counts().to_dict()}")
    logger.info(f"Message length: mean={df['text_length'].mean():.1f}, median={df['text_length'].median():.1f}, min={df['text_length'].min()}, max={df['text_length'].max()}")

    # Generate plots
    plot_class_distribution(df, plots_dir / "class_distribution.png")
    plot_language_distribution(df, plots_dir / "language_distribution.png")
    plot_message_length(df, plots_dir / "message_length_by_class.png")

    logger.info("\nAll EDA plots generated successfully!")


if __name__ == "__main__":
    main()
