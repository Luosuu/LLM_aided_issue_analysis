import json
import os
import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, List
from collections import Counter

def calculate_bug_type_percentages(directory_path: str) -> Dict[str, float]:
    BUG_CATEGORIES = [
        "CodeBug", "Config", "Human", "Network", "Upgrade",
        "Security", "Storage", "LoadBalance", "Transaction",
        "Performance", "Memory", "Replication", "Monitoring",
        "Recovery", "Unknown"
    ]

    # Initialize counters
    category_counts = Counter()
    total_issues = 0

    # Process all JSON files
    for filename in os.listdir(directory_path):
        if filename.endswith('.json'):
            file_path = os.path.join(directory_path, filename)
            try:
                with open(file_path, 'r') as f:
                    bug_report = json.load(f)

                # Count this as one issue
                total_issues += 1

                # Count categories
                if 'categories' in bug_report:
                    categories = [cat for cat in bug_report['categories'] 
                                if cat in BUG_CATEGORIES]
                    for cat in categories:
                        category_counts[cat] += 1

            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"Error processing {filename}: {str(e)}")

    # Calculate percentages
    percentages = {cat: (count / total_issues * 100) 
                  for cat, count in category_counts.items()}

    # Add 0% for categories that didn't appear
    for cat in BUG_CATEGORIES:
        if cat not in percentages:
            percentages[cat] = 0.0

    return percentages, total_issues

def plot_bug_type_percentages(percentages: Dict[str, float], total_issues: int):
    # Sort categories by percentage
    sorted_items = sorted(percentages.items(), key=lambda x: x[1], reverse=True)
    categories, values = zip(*sorted_items)

    # Create figure with larger size
    plt.figure(figsize=(7, 6))

    # Create bars
    bars = plt.bar(categories, values)

    # Customize the plot
    plt.title(f'Bug Category Distribution (Total Issues: {total_issues})', 
              pad=20, fontsize=14)
    plt.xlabel('Categories', fontsize=12)
    plt.ylabel('Percentage of Issues (%)', fontsize=12)

    # Rotate x-axis labels
    plt.xticks(rotation=45, ha='right', fontsize=10)
    plt.yticks(fontsize=10)

    # Add percentage labels on top of each bar
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}%',
                ha='center', va='bottom')

    # Add grid for better readability
    plt.grid(axis='y', linestyle='--', alpha=0.7)

    # Adjust layout to prevent label cutoff
    plt.tight_layout()

    return plt

def main():
    # Replace with your directory path
    directory_path = "./tikv_bug_analysis_unified_type"

    # Calculate percentages
    percentages, total_issues = calculate_bug_type_percentages(directory_path)

    # Print textual summary
    print(f"\nBug Category Distribution (Total Issues: {total_issues})")
    print("\nPercentage of issues containing each bug type:")
    for category, percentage in sorted(percentages.items(), key=lambda x: x[1], reverse=True):
        print(f"{category}: {percentage:.1f}%")

    # Create and save visualization
    plot_bug_type_percentages(percentages, total_issues)
    plt.savefig('tikv_bug_type_percentages.png', 
                dpi=300,
                bbox_inches='tight',
                pad_inches=0.5)
    plt.close()

if __name__ == "__main__":
    main()
