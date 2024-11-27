import json
import anthropic
from pathlib import Path
import sys
import time
from json.decoder import JSONDecodeError

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

def analyze_bug_issue(issue_data):
    """Use Claude to analyze a bug issue with improved error handling"""

    claude = anthropic.Anthropic()

    prompt = f"""
    Analyze this Redis bug issue and provide a structured analysis in valid JSON format.
    Note that when the information is insufficient for analysis, please be honest to say that you are not sure for the bug location or root cause.
    Your response must be ONLY a JSON object with these exact fields:
    - bug_location: string describing which Redis component is affected
    - severity: integer from 1-5
    - categories: array of strings from {BUG_CATEGORIES}
    - root_cause: string explaining the technical cause

    Issue Title: {issue_data['title']}
    Issue Description: {issue_data['body']}
    Labels: {issue_data.get('labels', [])}

    Comments:
    {json.dumps(issue_data['comments_data'], indent=2)}
    """

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

        # Try to parse the response
        try:
            analysis = json.loads(response.content[0].text)

            # Validate required fields
            required_fields = ['bug_location', 'severity', 'categories', 'root_cause']
            missing_fields = [field for field in required_fields if field not in analysis]

            if missing_fields:
                raise ValueError(f"Missing required fields: {missing_fields}")

            # Validate severity is integer 1-5
            if not isinstance(analysis['severity'], int) or not 1 <= analysis['severity'] <= 5:
                analysis['severity'] = int(analysis['severity'])

            # Validate categories
            if not isinstance(analysis['categories'], list):
                analysis['categories'] = [analysis['categories']]
            analysis['categories'] = [cat for cat in analysis['categories'] if cat in BUG_CATEGORIES]

            return analysis

        except JSONDecodeError as e:
            # If JSON parsing fails, try to extract just the JSON portion
            response_text = response.content[0].text
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                cleaned_json = response_text[json_start:json_end]
                return json.loads(cleaned_json)
            else:
                raise ValueError(f"Could not extract valid JSON from response: {str(e)}")

    except Exception as e:
        print(f"Error in analyze_bug_issue: {str(e)}")
        # Return a default analysis structure
        return {
            "bug_location": "Unknown",
            "severity": 3,
            "categories": ["Unknown"],
            "root_cause": "N/A - Analysis failed"
        }

def main():
    # Create output directory
    output_dir = Path('redis_bug_analysis_unified_type')
    output_dir.mkdir(exist_ok=True)

    # Read all issue files
    issues_dir = Path('redis_bug_details')
    analysis_results = []

    # Load existing combined analysis if it exists
    combined_analysis_file = output_dir / 'combined_analysis.json'
    existing_analyses = {}
    if combined_analysis_file.exists():
        with open(combined_analysis_file, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
            existing_analyses = {str(item['issue_number']): item for item in existing_data}
            analysis_results = existing_data

    # Track progress
    total_issues = len(list(issues_dir.glob('issue_*.json')))
    processed = 0
    skipped = 0

    for issue_file in issues_dir.glob('issue_*.json'):
        issue_number = issue_file.stem.split('_')[1]

        # Skip if analysis already exists
        if issue_number in existing_analyses:
            print(f"Skipping issue {issue_number} - analysis already exists")
            skipped += 1
            continue

        print(f"Analyzing {issue_file.name}... ({processed + 1}/{total_issues})")

        try:
            with open(issue_file, 'r', encoding='utf-8') as f:
                issue_data = json.load(f)

            # Add retry logic
            max_retries = 3
            retry_count = 0
            while retry_count < max_retries:
                try:
                    analysis = analyze_bug_issue(issue_data)
                    break
                except Exception as e:
                    retry_count += 1
                    if retry_count == max_retries:
                        print(f"Failed to analyze issue {issue_number} after {max_retries} attempts")
                        raise e
                    print(f"Retry {retry_count}/{max_retries} for issue {issue_number}")
                    time.sleep(5)  # Wait 5 seconds before retry

            # Add metadata
            analysis['issue_number'] = issue_data['issue_number']
            analysis['title'] = issue_data['title']

            # Save individual analysis
            analysis_file = output_dir / f"analysis_{issue_number}.json"
            with open(analysis_file, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, indent=2)

            analysis_results.append(analysis)
            processed += 1

            # Save combined analysis periodically (every 5 successful analyses)
            if processed % 5 == 0:
                with open(combined_analysis_file, 'w', encoding='utf-8') as f:
                    json.dump(analysis_results, f, indent=2)

        except Exception as e:
            print(f"Error processing issue {issue_number}: {str(e)}")

        # Print progress
        print(f"Progress: {processed}/{total_issues} analyzed, {skipped} skipped")

        # Add a small delay between requests to avoid rate limiting
        time.sleep(2)

        # Final save of combined analysis
        with open(combined_analysis_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_results, f, indent=2)

        # Print progress
        print(f"Progress: {processed}/{total_issues} analyzed, {skipped} skipped")

    print(f"\nAnalysis complete:")
    print(f"- Total issues: {total_issues}")
    print(f"- Newly processed: {processed}")
    print(f"- Skipped (already analyzed): {skipped}")
    print(f"- Results saved in {output_dir}")

if __name__ == "__main__":
    main()
