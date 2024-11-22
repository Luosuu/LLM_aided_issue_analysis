import requests
import pandas as pd
from datetime import datetime
from collections import Counter

def fetch_github_issues(owner, repo, state='all', auth_token=None):
    """
    Fetch issues from a GitHub repository using the GitHub API

    Parameters:
    - owner: repository owner
    - repo: repository name
    - state: 'open', 'closed', or 'all'
    - auth_token: GitHub personal access token
    """

    # GitHub API endpoint
    url = f"https://api.github.com/repos/{owner}/{repo}/issues"

    # Setup headers
    headers = {
        'Accept': 'application/vnd.github.v3+json'
    }
    if auth_token:
        headers['Authorization'] = f'token {auth_token}'

    # Store all issues
    all_issues = []
    page = 1

    while True:
        params = {
            'state': state,
            'per_page': 100,
            'page': page
        }

        response = requests.get(url, params=params, headers=headers)

        if response.status_code == 403:
            print("Rate limit exceeded. Please use a GitHub token.")
            break
        elif response.status_code != 200:
            print(f"Error fetching data: {response.status_code}")
            break

        issues = response.json()
        if not issues:
            break

        all_issues.extend(issues)
        page += 1

        print(f"Fetched {len(all_issues)} issues...")

    return all_issues

def analyze_issues(issues):
    """Analyze issues and their labels"""

    # Extract relevant information
    issues_data = []
    labels_counter = Counter()

    for issue in issues:
        # Count labels
        issue_labels = [label['name'] for label in issue['labels']]
        for label in issue_labels:
            labels_counter[label] += 1

        # Collect issue data
        issues_data.append({
            'number': issue['number'],
            'title': issue['title'],
            'state': issue['state'],
            'created_at': issue['created_at'],
            'closed_at': issue.get('closed_at'),
            'labels': ','.join(issue_labels),  # Store labels as comma-separated string
            'comments': issue['comments'],
            'is_pull_request': 'pull_request' in issue
        })

    return pd.DataFrame(issues_data), labels_counter

def print_statistics(df, labels_counter):
    """Print basic statistics about the issues"""

    print("\nIssue Statistics:")
    print(f"Total issues: {len(df)}")
    print(f"Open issues: {len(df[df['state'] == 'open'])}")
    print(f"Closed issues: {len(df[df['state'] == 'closed'])}")

    # Exclude pull requests from bug analysis
    true_issues = df[~df['is_pull_request']]
    print(f"\nTrue issues (excluding PRs): {len(true_issues)}")

    print("\nTop 10 labels:")
    for label, count in labels_counter.most_common(10):
        print(f"{label}: {count}")

def main():
    # Your GitHub token (optional but recommended)
    auth_token = "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"  # Replace with your token if available

    # Fetch Redis repository issues
    issues = fetch_github_issues('redis', 'redis', auth_token=auth_token)

    # Analyze issues
    df, labels_counter = analyze_issues(issues)

    # Print statistics
    print_statistics(df, labels_counter)

    # Save to CSV for further analysis
    df.to_csv('redis_issues.csv', index=False)

    # Basic bug analysis
    bug_issues = df[df['labels'].str.contains('bug', case=False, na=False)]
    print(f"\nNumber of bug reports: {len(bug_issues)}")

if __name__ == "__main__":
    main()
