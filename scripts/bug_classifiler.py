import os

import aiohttp
import pandas as pd
import openai
import json
import asyncio
from tqdm import tqdm
from dotenv import load_dotenv

# GitHub API base URL for issues
BASE_URL = "https://api.github.com/repos/frappe/erpnext/issues"

load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')
github_token = os.getenv('GITHUB_TOKEN')

# Headers for GitHub API
HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "Authorization": f"token {github_token}"
}


class IssueProcessor:
    def __init__(self, max_concurrent_tasks=10):
        self.semaphore = asyncio.Semaphore(max_concurrent_tasks)

    async def fetch_issues_with_limit(self, limit, start_issue_number=None):
        fetched_count = 0
        current_issue_number = start_issue_number

        async with aiohttp.ClientSession() as session:
            while fetched_count < limit:
                tasks = []

                # Build the URL based on the current issue number
                if current_issue_number:
                    url = f"{BASE_URL}/{current_issue_number}"
                else:
                    url = BASE_URL

                print(f"Fetching issues starting from #{current_issue_number or 'latest'}...")

                async with self.semaphore:
                    task = session.get(url, headers=HEADERS)
                    tasks.append(task)

                responses = await asyncio.gather(*tasks)

                for response in responses:
                    if response.status != 200:
                        print(f"Error: {response.status}, {await response.text()}")
                        continue

                    data = await response.json()

                    # If data is empty, stop fetching
                    if not data:
                        break

                    if isinstance(data, list):
                        # Batch fetched when no specific issue number provided
                        batch_issues = data[:limit - fetched_count]
                        fetched_count += len(batch_issues)
                    else:
                        # Single issue fetched when specific issue number provided
                        batch_issues = [data]
                        fetched_count += 1
                        current_issue_number -= 1  # Decrease issue number

                    if fetched_count > limit:
                        break

                    # Process the fetched issues
                    print(f"Processing fetched issues...")
                    df_all, df_classification = await self.parse_issues_to_dataframe(batch_issues)

                    self.save_to_csv(df_all, "./erpnext_issues_all.csv")
                    self.save_to_csv(df_classification, "./erpnext_issues_classification.csv")
                    print(f"Saved fetched issues.")

                # Stop fetching if reached the earliest issue
                if current_issue_number is not None and current_issue_number <= 0:
                    break

        print("Finished fetching and processing issues.")

    async def classify_issue_and_analyze(self, title, body, label, is_pull_request):
        if not title or not body:
            return {
                "category": "Insufficient information",
                "category_reason": "Insufficient information provided in title or description.",
                "component": "",
                "component_reason": "",
                "preconditions": "",
                "steps_to_reproduce": "",
                "expected_results": "",
                "actual_results": ""
            }

        categories = [
            "UI/UX",
            "ERP Workflow",  # Now includes both ERP and General Workflow
            "Performance",
            "Docs & Validation",
            "Security",
            "Other"
        ]

        components_list = [
            "Settings",
            "Users and Permissions",
            "Data Management",
            "Accounting",
            "CRM",
            "Buying",
            "Selling",
            "Loans",
            "Stock",
            "Manufacturing",
            "Assets",
            "Quality",
            "Regional"
        ]

        prompt = f"""
        
        Title: {title}
        Description: {body}
        Labels: {label}
        
        ### Fields to Extract
        Extract the following fields if they exist. If not present, leave them blank:
        - preconditions
        - steps_to_reproduce
        - expected_results
        - actual_results
        
        Classify the following {'pull request' if is_pull_request else 'issue'} into one of these categories and identify the most relevant component. 
        Provide specific reasons for both category and component selections. If not applicable, leave the field blank.
        
        ### Categories
        - **UI/UX**: Problems related to the graphical user interface (GUI) and user experience without affecting business logic or database data. Examples:
          - Layout, alignment, or design issues.
          - Data display errors due to incorrect UI rendering.
          - Interaction design problems (e.g., unresponsive buttons, unclear labels).
          - Visual experience or accessibility improvements.

        - **ERP Workflow**: Issues impacting business logic or database interactions, including both core and auxiliary processes. Examples:
          - Errors or fixes in core modules such as financial management, inventory control, or procurement workflows.
          - Problems with intended business rules or logic.
          - Backend data handling logic errors or missing workflows.
          - Modifications to auxiliary workflows (e.g., automation scripts).
          - Fixes or enhancements in secondary modules.

        - **Performance**: Issues related to system efficiency, scalability, or integration. Examples:
          - Slow queries or delayed system responses.
          - Compatibility issues with third-party integrations.
          - Scalability concerns with high system load or large datasets.

        - **Docs & Validation**: Problems involving incorrect or incomplete documentation, or validation issues. Examples:
          - Errors in user manuals or API documentation.
          - Missing workflow tests or logical gaps in validation rules.

        - **Security**: Issues compromising system security. Examples:
          - Unsecured sensitive data or improper user access control.
          - Exploitable vulnerabilities (e.g., SQL injection, XSS).

        - **Other**: Issues not clearly fitting into the above categories. Examples:
          - Minor inconsistencies or rare edge cases with limited impact.

        {"If this pull request addresses an issue, classify it based on the issue it resolves. If it introduces a new feature or enhancement, classify it based on the relevant category." if is_pull_request else ""}
        
        ### Components
        Identify the most relevant component based on the issue description and the provided labels. Follow the steps below:
        Labels: {label}

        1. **Match Component in Labels**:
           - If the `labels` contain or closely match one of the components, directly return the corresponding component and reason it is derived from the label.
           - Example: If `labels` contain "accounts", return "Accounting" as the component with the reason "Derived from label 'accounts'."

        2. **Analyze Issue Description**:
           - If no matching component is found in the `labels`, analyze the issue description to determine the most relevant component. Select the component only if:
             - The issue explicitly involves business processes or functionalities of the component.
             - You are confident the issue pertains to workflows or features managed by the component.

        #### Components:
        - **Settings**
          Focuses on system-wide and module-specific core configurations, including:
          - System settings (global parameters)
          - Email server/domain configuration
          - Naming rules (Naming Series) for forms/documents
          - Workflow configurations
          - Print style/format setups
          - Automation features (like scheduled tasks)

        - **Users and Permissions**
          Manages user accounts, roles, and access controls, covering:
          - User creation, role/permission assignments
          - User group management and permission rules
          - Login/access policies

        - **Data Management**
          Handles data import/export, backups, bulk updates/deletions, and data renaming, including:
          - Data import/export tools
          - Backup and restore processes
          - Large-scale data updates or cleanups
          - Personal data protection and deletion

        - **Accounting**
          Manages financial and accounting operations, involving:
          - General ledger, payables/receivables, budgeting, multi-currency
          - Taxation, invoicing, bank reconciliation
          - Subscription billing, shareholder management
          - Deferred revenue/expenses
          - Chart Of Accounts, Payment Terms, Purchase/sales Invoice, Payment Request/entry/order, Dunning
          - cost center

        - **CRM**
          Manages customer relationship and the front end of the sales pipeline, including:
          - Leads, opportunities
          - Customer profiles, marketing campaigns, sales funnel
          - Reporting, analytics, sales team setups

        - **Buying**
          Manages procurement processes, covering:
          - RFQs, purchase orders, purchase invoices, Supplier Quotation, Purchase Return, Material Request
          - Supplier management, supplier scorecards
          - Procurement-related reports and configurations

        - **Selling**
          Oversees sales processes, including:
          - Selling Transactions: Quotations, sales orders, sales invoices,Sales return
          - Customer, Sales Person
          - Customer data management, payment collections
          - POS, delivery notes, sales performance tracking

        - **Loans**
          Manages the full loan lifecycle, including:
          - Loan applications, disbursements, repayments
          - Interest, penalties, collateral management
          - Related reports and accounting

        - **Stock**
          Handles inventory and warehousing, involving:
          - Inventory records, bin/warehouse operations
          - Stock transactions, batch/serial number tracking
          - Stock valuation, stock reconciliation

        - **Manufacturing**
          Oversees production and manufacturing workflows, including:
          - Bill of Materials, work orders, material resource planning
          - Subcontracting, capacity planning
          - Production dashboards, manufacturing reports

        - **Assets**
          Handles tangible and intangible asset management, including:
          - Asset acquisition, depreciation, disposal
          - Asset maintenance, asset reports
          - Compliance and asset audits

        - **Quality**
          Manages quality control and inspection processes, covering:
          - Quality checks, inspection templates
          - Non-conformance tracking, supplier quality
          - Batch tracking and quality reports

        - **Regional**
          Handles localization and region-specific requirements, involving:
          - Multi-language translations, local settings
          - Local tax structures, financial report formats
          - Regional or country-specific compliance

        ### Selection Guidelines:
        - Select a component only if the issue explicitly mentions its ERP functionalities.
        - Avoid defaulting to general components unless clearly relevant.
        - Do not select a component based on generic mentions.

        Output the result in **strict JSON** format with the structure:
        {{
            "category": "<category>",
            "category_reason": "<detailed reason for category selection>",
            "component": "<component>",
            "component_reason": "<detailed reason for component selection>",
            "preconditions": "<preconditions>",
            "steps_to_reproduce": "<steps_to_reproduce>",
            "expected_results": "<expected_results>",
            "actual_results": "<actual_results>"
        }}
        """.strip()

        try:
            while True:
                response = openai.ChatCompletion.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system",
                         "content": "You classify issues and extract relevant fields with detailed reasoning."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=800
                )
                content = response['choices'][0]['message']['content'].strip()
                content = content.strip().lstrip('```json').rstrip('```').strip()
                result = json.loads(content)

                # Validate category
                if result.get("category") not in categories:
                    continue

                # Validate component and reason
                if result.get("component") and result.get("component") not in components_list:
                    continue
                if result.get("component") and not result.get("component_reason"):
                    continue

                break

        except Exception as e:
            result = {
                "category": "Other",
                "category_reason": f"Error processing issue: {str(e)}",
                "component": "",
                "component_reason": "",
                "preconditions": "",
                "steps_to_reproduce": "",
                "expected_results": "",
                "actual_results": ""
            }

        return result

    async def parse_issues_to_dataframe(self, issues):
        all_data = []
        classifications = []
        progress_bar = tqdm(total=len(issues), desc="Processing issues")

        async def process_issue(issue):
            is_pull_request = "pull_request" in issue
            labels = [label["name"] for label in issue.get("labels", [])]

            # Basic issue data remains the same
            issue_full_data = {
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

            # Get analysis with new structure
            analysis = await self.classify_issue_and_analyze(
                issue.get("title"),
                issue.get("body", ""),
                labels,
                is_pull_request
            )

            # Updated classification dictionary to match new structure
            classification = {
                "number": issue.get("number"),
                "category": analysis["category"],
                "category_reason": analysis["category_reason"],
                "component": analysis["component"],
                "component_reason": analysis["component_reason"],
                "preconditions": analysis["preconditions"],
                "steps_to_reproduce": analysis["steps_to_reproduce"],
                "expected_results": analysis["expected_results"],
                "actual_results": analysis["actual_results"],
                "labels": ", ".join(labels)
            }

            tqdm.write(f"Processed issue #{issue.get('number')}: {issue.get('title')}")
            progress_bar.update(1)
            progress_bar.refresh()  # Ensure the bar stays up-to-date
            return issue_full_data, classification

        tasks = [process_issue(issue) for issue in issues]
        results = await asyncio.gather(*tasks)

        for issue_data, classification_data in results:
            all_data.append(issue_data)
            classifications.append(classification_data)

        progress_bar.close()

        # Create DataFrames
        issues_df = pd.DataFrame(all_data)
        classifications_df = pd.DataFrame(classifications)

        return issues_df, classifications_df

    def save_to_csv(self, new_df, file_name):
        if os.path.exists(file_name):
            existing_df = pd.read_csv(file_name)
            combined_df = pd.concat([existing_df, new_df]).drop_duplicates(subset="number")
            combined_df.to_csv(file_name, index=False)
        else:
            new_df.to_csv(file_name, index=False)

    async def main(self, limit=50, start_issue_number=None):
        print(f"Fetching up to {limit} issues from ERPNext repository...")
        await self.fetch_issues_with_limit(limit, start_issue_number=start_issue_number)

if __name__ == "__main__":
    processor = IssueProcessor()
    start_number = 39990  # Example starting issue number
    asyncio.run(processor.main(limit=10, start_issue_number=start_number))
