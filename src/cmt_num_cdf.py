import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from rank_issues import load_and_clean_data

def plot_comment_cdf(df):
    """Create a CDF plot of comment distribution"""
    plt.figure(figsize=(12, 6))

    # Get comments from non-PR issues
    comments = df[~df['is_pull_request']]['comments'].sort_values()

    # Calculate CDF
    y_vals = np.arange(len(comments)) / float(len(comments))

    # Plot CDF
    plt.plot(comments, y_vals, 'b-', label='CDF')

    # Add grid and labels
    plt.grid(True, alpha=0.3)
    plt.title('Cumulative Distribution of Comments per Issue')
    plt.xlabel('Number of Comments')
    plt.ylabel('Cumulative Proportion of Issues')

    # Add some reference lines
    plt.axhline(y=0.5, color='r', linestyle='--', alpha=0.3, label='Median')
    plt.axhline(y=0.75, color='g', linestyle='--', alpha=0.3, label='75th percentile')
    plt.axhline(y=0.90, color='y', linestyle='--', alpha=0.3, label='90th percentile')

    # Add legend
    plt.legend()

    # Save the plot
    plt.savefig('comment_distribution_cdf.png')
    plt.close()

def main():
    # Load and clean data
    df = load_and_clean_data('redis_issues.csv')

    # Plot CDF
    plot_comment_cdf(df)

    # Calculate and print percentile statistics
    comments = df[~df['is_pull_request']]['comments']
    percentiles = [50, 75, 90, 95, 99]

    print("\nComment Distribution Percentiles:")
    for p in percentiles:
        value = np.percentile(comments, p)
        print(f"{p}th percentile: {value:.0f} comments")
