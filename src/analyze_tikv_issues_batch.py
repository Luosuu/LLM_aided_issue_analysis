import json
import anthropic
from pathlib import Path
import time
from json.decoder import JSONDecodeError
from datetime import datetime, timedelta
from anthropic.types.beta.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.beta.messages.batch_create_params import Request

# Categories remain the same
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

def create_analysis_batch(issues, client):
    """Create a batch of analysis requests"""
    requests = []
    for issue_data in issues:
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

        requests.append(
            Request(
                custom_id=str(issue_data['issue_number']),
                params=MessageCreateParamsNonStreaming(
                    model="claude-3-5-haiku-latest",
                    max_tokens=300,
                    temperature=0,
                    messages=[{
                        "role": "user",
                        "content": prompt
                    }]
                )
            )
        )

    return client.beta.messages.batches.create(requests=requests)


def create_error_analysis(issue_number):
    """Create a default error analysis for failed requests"""
    return {
        "issue_number": issue_number,
        "bug_location": "Unknown",
        "severity": 3,
        "categories": ["Unknown"],
        "root_cause": "N/A - Analysis failed"
    }

def wait_for_batch_completion(batch_id, client, max_wait_time=300, check_interval=5):
    """Wait for batch processing to complete"""
    start_time = time.time()
    while True:
        try:
            # Try to get results
            next(client.beta.messages.batches.results(batch_id))
            return True
        except anthropic.AnthropicError as e:
            if "in_progress" in str(e):
                if time.time() - start_time > max_wait_time:
                    print(f"Batch {batch_id} timed out after {max_wait_time} seconds")
                    return False
                time.sleep(check_interval)
                continue
            else:
                print(f"Error checking batch {batch_id}: {str(e)}")
                return False

def process_batch_results(batch_id, client):
    """Process batch results and return analyzed issues"""
    analyzed_issues = {}

    # Wait for batch to complete
    if not wait_for_batch_completion(batch_id, client):
        return analyzed_issues

    for result in client.beta.messages.batches.results(batch_id):
        issue_number = result.custom_id

        match result.result.type:
            case "succeeded":
                try:
                    analysis = json.loads(result.result.message.content[0].text)
                    analysis = {
                        'bug_location': str(analysis.get('bug_location', 'Unknown'))[:100],
                        'severity': min(max(int(analysis.get('severity', 3)), 1), 5),
                        'categories': [cat for cat in analysis.get('categories', ['Unknown']) 
                                     if cat in BUG_CATEGORIES][:3],
                        'root_cause': str(analysis.get('root_cause', 'N/A'))[:200],
                        'issue_number': issue_number
                    }
                    analyzed_issues[issue_number] = analysis
                except Exception as e:
                    print(f"Error processing successful result for issue {issue_number}: {str(e)}")
                    analyzed_issues[issue_number] = create_error_analysis(issue_number)

            case "errored":
                print(f"Error analyzing issue {issue_number}: {result.result.error}")
                analyzed_issues[issue_number] = create_error_analysis(issue_number)

            case "expired":
                print(f"Request expired for issue {issue_number}")
                analyzed_issues[issue_number] = create_error_analysis(issue_number)

    return analyzed_issues

def main():
    client = anthropic.Anthropic()
    output_dir = Path('tikv_bug_analysis')
    output_dir.mkdir(exist_ok=True)
    issues_dir = Path('tikv_bug_details')

    # Load existing analysis
    combined_analysis_file = output_dir / 'combined_analysis.json'
    existing_analyses = {}
    if combined_analysis_file.exists():
        with open(combined_analysis_file, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
            existing_analyses = {str(item['issue_number']): item for item in existing_data}

    # Process issues in smaller batches
    BATCH_SIZE = 100  # Reduced batch size for better reliability
    pending_issues = []

    for issue_file in sorted(issues_dir.glob('issue_*.json')):
        issue_number = issue_file.stem.split('_')[1]

        if issue_number in existing_analyses:
            continue

        with open(issue_file, 'r', encoding='utf-8') as f:
            issue_data = json.load(f)
            pending_issues.append(issue_data)

        if len(pending_issues) >= BATCH_SIZE:
            print(f"Processing batch of {len(pending_issues)} issues...")
            batch = create_analysis_batch(pending_issues, client)
            analyzed_issues = process_batch_results(batch.id, client)

            # Update and save results
            existing_analyses.update(analyzed_issues)
            with open(combined_analysis_file, 'w', encoding='utf-8') as f:
                json.dump(list(existing_analyses.values()), f, indent=2)

            # Save individual analyses
            for analysis in analyzed_issues.values():
                analysis_file = output_dir / f"analysis_{analysis['issue_number']}.json"
                with open(analysis_file, 'w', encoding='utf-8') as f:
                    json.dump(analysis, f, indent=2)

            pending_issues = []
            time.sleep(2)  # Small delay between batches

    # Process remaining issues
    if pending_issues:
        print(f"Processing final batch of {len(pending_issues)} issues...")
        batch = create_analysis_batch(pending_issues, client)
        analyzed_issues = process_batch_results(batch.id, client)

        existing_analyses.update(analyzed_issues)
        with open(combined_analysis_file, 'w', encoding='utf-8') as f:
            json.dump(list(existing_analyses.values()), f, indent=2)

        for analysis in analyzed_issues.values():
            analysis_file = output_dir / f"analysis_{analysis['issue_number']}.json"
            with open(analysis_file, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, indent=2)

if __name__ == "__main__":
    main()