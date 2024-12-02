import json
import os
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from typing import List, Dict, Set
from itertools import combinations

def create_cooccurrence_matrix(directory_path: str) -> np.ndarray:
    BUG_CATEGORIES = [
        "CodeBug", "Config", "Human", "Network", "Upgrade",
        "Security", "Storage", "LoadBalance", "Transaction",
        "Performance", "Memory", "Replication", "Monitoring",
        "Recovery", "Unknown"
    ]

    cat_to_idx = {cat: idx for idx, cat in enumerate(BUG_CATEGORIES)}
    n_categories = len(BUG_CATEGORIES)
    cooccurrence_matrix = np.zeros((n_categories, n_categories), dtype=int)

    for filename in os.listdir(directory_path):
        if filename.endswith('.json'):
            file_path = os.path.join(directory_path, filename)
            try:
                with open(file_path, 'r') as f:
                    bug_report = json.load(f)

                if 'categories' in bug_report:
                    categories = [cat for cat in bug_report['categories'] 
                                if cat in BUG_CATEGORIES]

                    # Only count pairs of different categories
                    for cat1, cat2 in combinations(categories, 2):
                        idx1, idx2 = cat_to_idx[cat1], cat_to_idx[cat2]
                        cooccurrence_matrix[idx1][idx2] += 1
                        cooccurrence_matrix[idx2][idx1] += 1

            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"Error processing {filename}: {str(e)}")

    return cooccurrence_matrix, BUG_CATEGORIES

def plot_cooccurrence_matrix(matrix: np.ndarray, categories: List[str]):
    plt.figure(figsize=(20, 16))

    # Set font sizes
    FONT_SIZE = 24
    ANNOT_SIZE = 24
    plt.rc('font', size=FONT_SIZE)
    plt.rc('axes', titlesize=FONT_SIZE + 2)
    plt.rc('axes', labelsize=FONT_SIZE)
    plt.rc('xtick', labelsize=FONT_SIZE)
    plt.rc('ytick', labelsize=FONT_SIZE)

    # Create masks for both upper triangle and diagonal
    mask_upper = np.triu(np.ones_like(matrix, dtype=bool), k=0)

    # Create heatmap
    sns.heatmap(matrix, 
                mask=mask_upper,
                annot=True,
                fmt='d',
                cmap='YlOrRd',
                xticklabels=categories,
                yticklabels=categories,
                square=True,
                annot_kws={'size': ANNOT_SIZE},
                cbar_kws={'shrink': .8},
                linewidths=0.5,
                linecolor='white')

    plt.title('Bug Category Co-occurrence Matrix', pad=20, fontsize=FONT_SIZE + 4)

    plt.xticks(rotation=45, ha='right')
    plt.yticks(rotation=0)

    plt.tight_layout()

    return plt

def analyze_top_pairs(matrix: np.ndarray, categories: List[str], top_n: int = 10):
    cooccurrences = []
    n = len(categories)
    # Only look at lower triangle, excluding diagonal
    for i in range(n):
        for j in range(i):  # j < i ensures we're below diagonal
            if matrix[i][j] > 0:
                cooccurrences.append((
                    categories[i],
                    categories[j],
                    matrix[i][j]
                ))

    return sorted(cooccurrences, key=lambda x: x[2], reverse=True)[:top_n]

def main():
    # Replace with your directory path
    directory_path = "./tikv_bug_analysis_unified_type"

    # Generate co-occurrence matrix
    matrix, categories = create_cooccurrence_matrix(directory_path)

    # Plot and save the matrix
    plot_cooccurrence_matrix(matrix, categories)
    plt.savefig('tikv_bug_cooccurrence_matrix.png', 
                dpi=300,
                bbox_inches='tight',
                pad_inches=0.2)
    plt.close()

    # Print top co-occurrences
    print("\nTop 10 most frequent bug category co-occurrences:")
    top_pairs = analyze_top_pairs(matrix, categories)
    for cat1, cat2, count in top_pairs:
        print(f"{cat1} + {cat2}: {count} co-occurrences")

if __name__ == "__main__":
    main()
