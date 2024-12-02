## Filter isssue by keywords like `bug`` and `crash`
## Input: issue details collected by GitHub API

import pandas as pd
import numpy as np
from rank_issues import load_and_clean_data

def identify_bug_issues(df):
    """
    Identify bug-related issues based on both labels and titles
    Returns a DataFrame with only bug-related issues
    """
    # Check labels for 'bug'
    bug_in_labels = df['labels'].str.contains('bug', case=False, na=False)

    # Check titles for '[bug]' or '[crash]'
    bug_in_title = df['title'].str.contains(r'\[bug\]|\[crash\]', case=False, na=False)

    # Combine both conditions and filter non-PRs
    bug_issues = df[
        (bug_in_labels | bug_in_title) & 
        (~df['is_pull_request'])
    ].copy()

    # Sort by number of comments (most discussed first)
    bug_issues = bug_issues.sort_values('comments', ascending=False)

    return bug_issues

def analyze_bug_issues(bug_issues):
    """Print statistics about bug issues"""
    print("\nBug Issues Statistics:")
    print(f"Total bug reports: {len(bug_issues)}")
    print(f"Open bugs: {len(bug_issues[bug_issues['state'] == 'open'])}")
    print(f"Closed bugs: {len(bug_issues[bug_issues['state'] == 'closed'])}")
    print(f"Average comments on bugs: {bug_issues['comments'].mean():.2f}")
    print(f"Median comments on bugs: {bug_issues['comments'].median():.0f}")
    print(f"Maximum comments on a bug: {bug_issues['comments'].max()}")

def main():
    # Load the data
    df = load_and_clean_data('tikv_issues.csv')

    # Identify and analyze bug issues
    bug_issues = identify_bug_issues(df)

    # Print bug statistics
    analyze_bug_issues(bug_issues)

    # Print top 10 most discussed bug issues
    print("\nTop 10 Most Discussed Bug Issues:")
    print("-" * 100)
    for _, issue in bug_issues.head(10).iterrows():
        print(f"#{issue['number']} - {issue['comments']} comments")
        print(f"Title: {issue['title']}")
        print(f"State: {issue['state']}")
        if isinstance(issue['labels'], str) and issue['labels']:
            print(f"Labels: {issue['labels']}")
        print(f"Created: {issue['created_at']}")
        print("-" * 100)

    # Save bug issues to a separate CSV file
    bug_issues.to_csv('tikv_bug_issues.csv', index=False)

    # Calculate percentage of bugs in total issues
    total_issues = len(df[~df['is_pull_request']])
    bug_percentage = (len(bug_issues) / total_issues) * 100
    print(f"\nPercentage of issues that are bugs: {bug_percentage:.1f}%")

if __name__ == "__main__":
    main()
