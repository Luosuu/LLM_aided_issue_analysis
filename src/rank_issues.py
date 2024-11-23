import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

def load_and_clean_data(csv_path):
    """Load and prepare the CSV data for analysis"""
    df = pd.read_csv(csv_path)

    # Convert date columns to datetime
    df['created_at'] = pd.to_datetime(df['created_at'])
    df['closed_at'] = pd.to_datetime(df['closed_at'])

    # Convert is_pull_request to boolean
    df['is_pull_request'] = df['is_pull_request'].fillna(False).astype(bool)

    # Convert comments to numeric, replacing any non-numeric values with 0
    df['comments'] = pd.to_numeric(df['comments'], errors='coerce').fillna(0).astype(int)

    return df

def analyze_top_discussions(df, top_n=20):
    """Analyze most discussed issues"""
    # Separate issues and PRs
    issues = df[df['is_pull_request'] == False].copy()

    # Sort by number of comments
    top_issues = issues.nlargest(top_n, 'comments')

    # Calculate some statistics
    total_issues = len(issues)
    avg_comments = issues['comments'].mean()
    median_comments = issues['comments'].median()
    max_comments = issues['comments'].max()

    return top_issues, {
        'total_issues': total_issues,
        'avg_comments': avg_comments,
        'median_comments': median_comments,
        'max_comments': max_comments
    }

def print_top_issues(top_issues):
    """Print detailed information about top issues"""
    print("\nMost Discussed Issues (sorted by number of comments):")
    print("-" * 100)

    for idx, issue in top_issues.iterrows():
        print(f"#{issue['number']} - {issue['comments']} comments")
        print(f"Title: {issue['title']}")
        print(f"State: {issue['state']}")
        if isinstance(issue['labels'], str) and issue['labels']:
            print(f"Labels: {issue['labels']}")
        print(f"Created: {issue['created_at'].strftime('%Y-%m-%d')}")
        print("-" * 100)

def analyze_comment_ranges(df):
    """Analyze issues by comment count ranges"""
    issues = df[~df['is_pull_request']]

    ranges = [
        (0, 0, "No comments"),
        (1, 5, "1-5 comments"),
        (6, 10, "6-10 comments"),
        (11, 20, "11-20 comments"),
        (21, float('inf'), "21+ comments")
    ]

    print("\nComment Range Distribution:")
    total_issues = len(issues)
    for start, end, label in ranges:
        count = len(issues[(issues['comments'] >= start) & (issues['comments'] <= end)])
        percentage = (count / total_issues) * 100
        print(f"{label}: {count} issues ({percentage:.1f}%)")

def main():
    # Load the data
    df = load_and_clean_data('tikv_bug_issues.csv')

    # Analyze top discussions
    top_issues, stats = analyze_top_discussions(df)

    # Print statistics
    print("\nOverall Issue Statistics:")
    print(f"Total number of issues: {stats['total_issues']}")
    print(f"Average comments per issue: {stats['avg_comments']:.2f}")
    print(f"Median comments per issue: {stats['median_comments']:.0f}")
    print(f"Maximum comments on an issue: {stats['max_comments']}")

    # Print detailed information about top issues
    print_top_issues(top_issues)

    # Analyze comment ranges
    analyze_comment_ranges(df)

    # Additional analysis: Issues with bug labels
    bug_issues = df[
        (df['labels'].str.contains('bug', case=False, na=False)) & 
        (~df['is_pull_request'])
    ]

    if len(bug_issues) > 0:
        print("\nBug Report Statistics:")
        print(f"Total bug reports: {len(bug_issues)}")
        print(f"Average comments on bugs: {bug_issues['comments'].mean():.2f}")
        print(f"Median comments on bugs: {bug_issues['comments'].median():.0f}")
        print(f"Maximum comments on a bug: {bug_issues['comments'].max()}")

    # Save top issues to a new CSV for further analysis
    top_issues.to_csv('tikv_most_discussed_bug_issues.csv', index=False)

if __name__ == "__main__":
    main()
