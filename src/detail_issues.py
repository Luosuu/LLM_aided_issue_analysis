import requests
import pandas as pd
import time
import json
from pathlib import Path

def load_github_token(token_path):
    """Load GitHub token from file"""
    try:
        with open(token_path, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"Warning: Token file not found at {token_path}")
        return None

def fetch_issue_details(owner, repo, issue_number, auth_token=None):
    """
    Fetch detailed information about a specific issue including its comments
    """
    # Base URLs for GitHub API
    issue_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"
    comments_url = f"{issue_url}/comments"

    # Setup headers
    headers = {
        'Accept': 'application/vnd.github.v3+json'
    }
    if auth_token:
        headers['Authorization'] = f'Bearer {auth_token}'

    try:
        # Fetch issue details
        issue_response = requests.get(issue_url, headers=headers)
        issue_response.raise_for_status()

        # Fetch all comments
        comments = []
        page = 1
        while True:
            params = {
                'per_page': 100,
                'page': page
            }
            comments_response = requests.get(comments_url, headers=headers, params=params)
            comments_response.raise_for_status()

            page_comments = comments_response.json()
            if not page_comments:
                break

            comments.extend(page_comments)
            page += 1

        # Combine issue and comments data
        issue_data = issue_response.json()

        # Extract relevant information
        return {
            'issue_number': issue_number,
            'title': issue_data['title'],
            'body': issue_data['body'],
            'state': issue_data['state'],
            'created_at': issue_data['created_at'],
            'updated_at': issue_data['updated_at'],
            'closed_at': issue_data['closed_at'],
            'labels': [label['name'] for label in issue_data['labels']],
            'comments_data': [{
                'id': comment['id'],
                'user': comment['user']['login'],
                'created_at': comment['created_at'],
                'body': comment['body']
            } for comment in comments]
        }

    except requests.exceptions.RequestException as e:
        print(f"Error fetching issue #{issue_number}: {str(e)}")
        return None

def main():
    # Load GitHub token
    auth_token = load_github_token('token/github_token.txt')
    if not auth_token:
        print("Warning: Proceeding without GitHub token. Rate limits will be restricted.")

    # Load bug issues CSV
    bug_df = pd.read_csv('redis_bug_issues.csv')

    # Create directory for storing detailed issue data
    output_dir = Path('redis_bug_details')
    output_dir.mkdir(exist_ok=True)

    # Track progress and failures
    successful_fetches = 0
    failed_fetches = []

    # Fetch details for each issue
    total_issues = len(bug_df)
    for idx, row in bug_df.iterrows():
        issue_number = row['number']
        print(f"Fetching issue #{issue_number} ({idx + 1}/{total_issues})")

        # Check if we already have this issue cached
        issue_file = output_dir / f"issue_{issue_number}.json"
        if issue_file.exists():
            print(f"Issue #{issue_number} already cached, skipping...")
            successful_fetches += 1
            continue

        # Fetch issue details
        issue_details = fetch_issue_details('redis', 'redis', issue_number, auth_token)

        if issue_details:
            # Save individual issue details to JSON
            with open(issue_file, 'w', encoding='utf-8') as f:
                json.dump(issue_details, f, ensure_ascii=False, indent=2)
            successful_fetches += 1
        else:
            failed_fetches.append(issue_number)

        # Respect GitHub API rate limits
        time.sleep(1)

    # Print summary
    print("\nFetch Summary:")
    print(f"Successfully fetched: {successful_fetches}/{total_issues}")
    if failed_fetches:
        print(f"Failed to fetch {len(failed_fetches)} issues: {failed_fetches}")
    print(f"Details saved in directory: {output_dir}")

if __name__ == "__main__":
    main()
