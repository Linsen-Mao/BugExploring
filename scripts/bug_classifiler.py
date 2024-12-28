import os

import requests
import pandas as pd
import openai  # Import OpenAI for LLM analysis
import json

from dotenv import load_dotenv

# GitHub API base URL for issues
BASE_URL = "https://api.github.com/repos/frappe/erpnext/issues"

load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')
github_token = os.getenv('GITHUB_TOKEN')

# Headers for GitHub API (optional: include your personal token for higher rate limits)
HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "Authorization": f"token {github_token}"  # Use GitHub token
}


# Function to fetch issues and pull requests with a limit on the number of items
def fetch_issues_with_limit(limit):
    issues = []
    page = 1
    fetched_count = 0

    while fetched_count < limit:
        print(f"Fetching page {page}...")
        params = {
            "state": "all",  # Fetch open and closed issues and pull requests
            "per_page": 100,
            "page": page,
        }
        response = requests.get(BASE_URL, headers=HEADERS, params=params)

        if response.status_code != 200:
            print(f"Error: {response.status_code}, {response.text}")
            break

        data = response.json()

        if not data:  # Exit loop if no more issues are found
            break

        remaining = limit - fetched_count
        issues.extend(data[:remaining])
        fetched_count += len(data[:remaining])

        if fetched_count >= limit:
            break

        page += 1

    return issues


# Function to classify an issue or pull request using LLM

def classify_issue_and_analyze(title, body, is_pull_request):
    if not title or not body:
        return {
            "category": "Insufficient information",
            "reason": "Insufficient information provided in title or description.",
            "preconditions": "",
            "steps_to_reproduce": "",
            "expected_results": "",
            "actual_results": ""
        }

    categories = [
    "UI/UX Issues",
    "Workflow Issues",
    "Performance and Compatibility Issues",
    "Documentation and Validation Issues",
    "Security Issues",
    "Other (Miscellaneous)"
    ]

    prompt = f"""
Classify the following {'pull request' if is_pull_request else 'issue'} into one of these categories and extract the following fields if present. If not present, leave the field blank:

- UI/UX Issues: Problems related to graphical user interface changes or issues that do not affect business logic or database data. This includes layout issues and interaction design problems.
- Workflow Issues: Problems that may affect business logic or database data, including errors in workflows, data processing anomalies, module interaction conflicts, or usability enhancements that impact ERP processes. This covers core ERP operations such as financial management, inventory control, and order processing.
- Performance and Compatibility Issues: System performance issues, such as slow response times, resource inefficiency, or integration with third-party systems and module compatibility.
- Documentation and Validation Issues: Missing or incorrect documentation, insufficient testing coverage, or validation logic errors.
- Security Issues: Vulnerabilities, such as data leaks, insufficient encryption, or improper access controls.
- Other (Miscellaneous): Minor inconsistencies or rare edge cases that do not fit into the above categories.

{'If this pull request addresses an issue, classify it based on the issue it resolves. If it introduces a new feature or enhancement, classify it based on the relevant category.' if is_pull_request else ''}

Extract the following fields if they exist:
- preconditions
- steps_to_reproduce
- expected_results
- actual_results

Output the result in strict JSON format with the following structure:
{{
  "category": "<category>",
  "reason": "<reason>",
  "preconditions": "<preconditions>",
  "steps_to_reproduce": "<steps_to_reproduce>",
  "expected_results": "<expected_results>",
  "actual_results": "<actual_results>"
}}

Title: {title}
Description: {body}
""".strip()

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system",
             "content": "You are an assistant that classifies issues into predefined categories and extracts specific fields."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=300
    )

    content = response['choices'][0]['message']['content'].strip()

    # Try to parse JSON, clean up if necessary
    try:
        # Ensure the content starts and ends with valid JSON
        content = content.strip().lstrip('```json').rstrip('```').strip()
        result = json.loads(content)
        category = result.get("category", "Other (Miscellaneous)")
        reason = result.get("reason", "No explanation provided.")
        preconditions = result.get("preconditions", "")
        steps_to_reproduce = result.get("steps_to_reproduce", "")
        expected_results = result.get("expected_results", "")
        actual_results = result.get("actual_results", "")
        labels = result.get("labels", [])
    except json.JSONDecodeError:
        # Handle parsing failure gracefully
        category = "Other (Miscellaneous)"
        reason = "Could not parse the JSON response. Raw content: " + content
        preconditions = ""
        steps_to_reproduce = ""
        expected_results = ""
        actual_results = ""
        labels = []

    # Validate the category
    if category not in categories:
        category = "Other (Miscellaneous)"
        reason = "Category not recognized, defaulting to Other."

    return {
        "category": category,
        "reason": reason,
        "preconditions": preconditions,
        "steps_to_reproduce": steps_to_reproduce,
        "expected_results": expected_results,
        "actual_results": actual_results,
        "labels": labels
    }


# Parse fetched issues into a Pandas DataFrame
def parse_issues_to_dataframe(issues):
    all_data = []
    classifications = []

    for issue in issues:
        is_pull_request = "pull_request" in issue  # Check if it's a pull request
        labels = [label["name"] for label in issue.get("labels", [])]  # Extract labels
        issue_data = {
            "id": issue.get("id"),
            "number": issue.get("number"),
            "title": issue.get("title"),
            "state": issue.get("state"),
            "created_at": issue.get("created_at"),
            "updated_at": issue.get("updated_at"),
            "closed_at": issue.get("closed_at"),
            "url": issue.get("html_url"),
            "is_pull_request": is_pull_request,
            "labels": labels
        }
        all_data.append(issue_data)

        # Classify the issue or pull request and analyze specific fields
        analysis = classify_issue_and_analyze(issue.get("title"), issue.get("body", ""), is_pull_request)
        classifications.append({
            "number": issue.get("number"),
            "category": analysis["category"],
            "reason": analysis["reason"],
            "preconditions": analysis["preconditions"],
            "steps_to_reproduce": analysis["steps_to_reproduce"],
            "expected_results": analysis["expected_results"],
            "actual_results": analysis["actual_results"],
            "labels": ", ".join(labels)  # Join labels into a string for CSV
        })

    df_all = pd.DataFrame(all_data)
    df_classification = pd.DataFrame(classifications)

    df_url = df_all[["url"]]
    df_basic = df_all[["url", "number", "state"]]

    return df_url, df_basic, df_all, df_classification


# Main function to fetch and save the data
def main(limit=50):
    print(f"Fetching up to {limit} issues and pull requests from ERPNext repository...")
    issues = fetch_issues_with_limit(limit)

    if issues:
        print(f"Fetched {len(issues)} issues and pull requests.")
        df_url, df_basic, df_all, df_classification = parse_issues_to_dataframe(issues)

        # Save to CSV files
        df_url.to_csv("erpnext_issues_url.csv", index=False)
        print("URL-only issues saved to 'erpnext_issues_url.csv'.")

        df_basic.to_csv("erpnext_issues_basic.csv", index=False)
        print("Basic issues saved to 'erpnext_issues_basic.csv'.")

        df_all.to_csv("erpnext_issues_all.csv", index=False)
        print("All issues saved to 'erpnext_issues_all.csv'.")

        df_classification.to_csv("erpnext_issues_classification.csv", index=False)
        print("Classified issues saved to 'erpnext_issues_classification.csv'.")
    else:
        print("No issues found or an error occurred.")


if __name__ == "__main__":
    main(limit=20)
