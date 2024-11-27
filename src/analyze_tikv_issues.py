import json
import anthropic
from pathlib import Path
import time
from json.decoder import JSONDecodeError
from datetime import datetime, timedelta

# Categories adapted for TiKV context
BUG_CATEGORIES = [
    "CodeBug",      # Core implementation bugs
    "Config",       # Configuration and setup issues
    "Human",        # User errors or misunderstandings
    "Network",      # Network, RPC, and connectivity issues
    "Upgrade",      # Version upgrade and compatibility issues
    "Security",     # Security vulnerabilities and access control
    "Storage",      # Storage engine, persistence, and data integrity
    "LoadBalance",  # Load balancing, scheduling, and cluster management
    "Transaction",  # Transaction, consistency, and isolation issues
    "Performance",  # Performance degradation and bottlenecks
    "Memory",       # Memory management and allocation issues
    "Replication",  # Data replication and synchronization
    "Monitoring",   # Metrics, logging, and observability issues
    "Recovery",     # Crash recovery and failover issues
    "Unknown"       # Unclassified or unclear issues
]

class RateLimitHandler:
    def __init__(self, max_retries=3, initial_wait=60):
        self.max_retries = max_retries
        self.initial_wait = initial_wait
        self.retry_count = 0
        self.last_error_time = None

    def should_retry(self, error):
        if "rate limit" in str(error).lower():
            self.retry_count += 1
            current_time = datetime.now()

            if self.last_error_time:
                # Exponential backoff
                wait_time = self.initial_wait * (2 ** (self.retry_count - 1))
                if (current_time - self.last_error_time).seconds < wait_time:
                    time.sleep(wait_time)

            self.last_error_time = current_time
            return self.retry_count < self.max_retries
        return False

    def reset(self):
        self.retry_count = 0
        self.last_error_time = None

def analyze_bug_issue(issue_data, rate_limit_handler):
    """Use Claude Haiku to analyze a TiKV bug issue"""

    claude = anthropic.Anthropic()

    # Create a concise prompt for TiKV issues
    prompt = f"""
    Analyze this TiKV bug issue. Provide a structured analysis in valid JSON format.
    Note that when the information is insufficient for analysis, please be honest to say that you are not sure for the bug location or root cause.
    Your response must be ONLY a JSON object with these exact fields:
    - bug_location: specific TiKV component affected
    - severity: integer 1-5 (5 most severe)
    - categories: array from {BUG_CATEGORIES}
    - root_cause: brief technical cause

    Title: {issue_data['title']}
    Description: {issue_data['body']}
    Labels: {issue_data.get('labels', [])}

    Comments:
    {json.dumps(issue_data['comments_data'], indent=2)}
    """

    while True:
        try:
            response = claude.messages.create(
                model="claude-3-5-haiku-latest",
                max_tokens=300,
                temperature=0,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            analysis = json.loads(response.content[0].text)

            # Validate and normalize
            analysis = {
                'bug_location': str(analysis.get('bug_location', 'Unknown'))[:100],
                'severity': min(max(int(analysis.get('severity', 3)), 1), 5),
                'categories': [cat for cat in analysis.get('categories', ['Unknown']) 
                             if cat in BUG_CATEGORIES][:3],
                'root_cause': str(analysis.get('root_cause', 'N/A'))[:200]
            }

            rate_limit_handler.reset()
            return analysis

        except Exception as e:
            if rate_limit_handler.should_retry(e):
                print(f"Rate limit hit, retrying after delay... (attempt {rate_limit_handler.retry_count})")
                continue
            else:
                print(f"Error in analysis: {str(e)}")
                return {
                    "bug_location": "Unknown",
                    "severity": 3,
                    "categories": ["Unknown"],
                    "root_cause": "N/A - Analysis failed"
                }

def main():
    # Create output directory
    output_dir = Path('tikv_bug_analysis_unified_type')
    output_dir.mkdir(exist_ok=True)

    # Read all issue files
    issues_dir = Path('tikv_bug_details')
    analysis_results = []

    # Load existing analysis if present
    combined_analysis_file = output_dir / 'combined_analysis.json'
    existing_analyses = {}
    if combined_analysis_file.exists():
        with open(combined_analysis_file, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
            existing_analyses = {str(item['issue_number']): item for item in existing_data}
            analysis_results = existing_data

    # Initialize rate limit handler
    rate_limit_handler = RateLimitHandler(max_retries=5, initial_wait=60)

    # Track progress
    total_issues = len(list(issues_dir.glob('issue_*.json')))
    processed = 0
    skipped = 0

    for issue_file in sorted(issues_dir.glob('issue_*.json')):
        issue_number = issue_file.stem.split('_')[1]

        # Skip if already analyzed
        if issue_number in existing_analyses:
            print(f"Skipping issue {issue_number} - analysis exists")
            skipped += 1
            continue

        print(f"Analyzing {issue_file.name}... ({processed + 1}/{total_issues})")

        try:
            with open(issue_file, 'r', encoding='utf-8') as f:
                issue_data = json.load(f)

            analysis = analyze_bug_issue(issue_data, rate_limit_handler)

            # Add metadata
            analysis['issue_number'] = issue_data['issue_number']
            analysis['title'] = issue_data['title']

            # Save individual analysis
            analysis_file = output_dir / f"analysis_{issue_number}.json"
            with open(analysis_file, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, indent=2)

            analysis_results.append(analysis)
            processed += 1

            # Save combined analysis every 5 successful analyses
            if processed % 5 == 0:
                with open(combined_analysis_file, 'w', encoding='utf-8') as f:
                    json.dump(analysis_results, f, indent=2)

        except Exception as e:
            print(f"Error processing issue {issue_number}: {str(e)}")

        # Print progress
        print(f"Progress: {processed}/{total_issues} analyzed, {skipped} skipped")

        # Add delay between requests
        time.sleep(3)

    # Final save
    with open(combined_analysis_file, 'w', encoding='utf-8') as f:
        json.dump(analysis_results, f, indent=2)

    print(f"\nAnalysis complete:")
    print(f"- Total issues: {total_issues}")
    print(f"- Newly processed: {processed}")
    print(f"- Skipped (already analyzed): {skipped}")
    print(f"- Results saved in {output_dir}")

if __name__ == "__main__":
    main()
