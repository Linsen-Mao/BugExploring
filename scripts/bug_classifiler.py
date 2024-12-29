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

    async def fetch_issues_with_limit(self, limit):
        page = 1
        fetched_count = 0

        async with aiohttp.ClientSession() as session:
            while fetched_count < limit:
                batch_issues = []
                tasks = []
                print(f"Fetching pages {page} to {page + 2}...")

                for i in range(3):
                    if fetched_count >= limit:
                        break
                    params = {
                        "state": "all",
                        "per_page": 100,
                        "page": page + i,
                    }

                    async with self.semaphore:
                        task = session.get(BASE_URL, headers=HEADERS, params=params)
                        tasks.append(task)

                responses = await asyncio.gather(*tasks)

                for response in responses:
                    if response.status != 200:
                        print(f"Error: {response.status}, {await response.text()}")
                        continue

                    data = await response.json()
                    if not data:
                        break

                    remaining = limit - fetched_count
                    batch_issues.extend(data[:remaining])
                    fetched_count += len(data[:remaining])

                    if fetched_count >= limit:
                        break

                if not batch_issues:
                    break

                # Process the fetched issues
                print(f"Processing fetched issues from pages {page} to {page + len(tasks) - 1}...")
                df_all, df_classification = await self.parse_issues_to_dataframe(batch_issues)

                self.save_to_csv(df_all, "./erpnext_issues_all.csv")
                self.save_to_csv(df_classification, "./erpnext_issues_classification.csv")
                print(f"Saved fetched issues from pages {page} to {page + len(tasks) - 1}...")

                page += len(tasks)  # Move to the next batch of pages

        print("Finished fetching and processing issues.")

    async def classify_issue_and_analyze(self, title, body, label, is_pull_request):
        if not title or not body:
            return {
                "category": "Insufficient information",
                "reason": "Insufficient information provided in title or description.",
                "components": "",
                "preconditions": "",
                "steps_to_reproduce": "",
                "expected_results": "",
                "actual_results": ""
            }

        categories = [
            "UI/UX",
            "ERP Workflow",
            "General Workflow",
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
            "Project",
            "Support",
            "Assets",
            "Quality",
            "Website",
            "Tools",
            "Integrations",
            "Regional"
        ]

        prompt = f"""
        Classify the following {'pull request' if is_pull_request else 'issue'} into one or more of these categories and identify the related components. If not applicable, leave the field blank.

        ### Categories
        - **UI/UX**: Problems related to the graphical user interface (GUI) and user experience without affecting business logic or database data. Examples:
          - Layout, alignment, or design issues.
          - Data display errors due to incorrect UI rendering.
          - Interaction design problems (e.g., unresponsive buttons, unclear labels).
          - Visual experience or accessibility improvements.

        - **ERP Workflow**: Issues impacting core ERP business logic, focusing on critical processes and database interactions. Examples:
          - Errors or fixes in core modules such as financial management, inventory control, or procurement workflows.
          - Problems with intended business rules or logic.
          - Backend data handling logic errors or missing workflows.

        - **General Workflow**: Issues affecting business logic or database interactions that are not tied to core ERP workflows. Examples:
          - Fixes or enhancements in secondary modules.
          - Modifications to auxiliary workflows (e.g., automation scripts).

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
        Identify related components based on the issue description. The components must be one or more of the following. Select a component only if it directly applies based on the issue details and you are confident in its relevance:

        - **Settings**
          Focuses on system-wide and module-specific core configurations, including:
          - System settings (global parameters)
          - Email server/domain configuration
          - Naming rules (Naming Series) for forms/documents
          - Workflow configurations
          - Print style/format setups
          - Automation features (like scheduled tasks)
          If the issue centers on foundational system or module setups, rules, or automation scenarios, select **Settings**.

        - **Users and Permissions**
          Manages user accounts, roles, and access controls, covering:
          - User creation, role/permission assignments
          - User group management and permission rules
          - Login/access policies
          If the issue relates to user management, permission vulnerabilities, role setups, or access controls, choose **Users and Permissions**.

        - **Data Management**
          Handles data import/export, backups, bulk updates/deletions, and data renaming, including:
          - Data import/export tools
          - Backup and restore processes
          - Large-scale data updates or cleanups
          - Personal data protection and deletion
          If the issue involves batch data processes or data administration, select **Data Management**.

        - **Accounting**
          Manages financial and accounting operations, involving:
          - General ledger, payables/receivables, budgeting, multi-currency
          - Taxation, invoicing, bank reconciliation
          - Subscription billing, shareholder management
          - Deferred revenue/expenses
          If the issue concerns the finance module, accounting workflows, tax calculations, or reconciliation, choose **Accounting**.

        - **CRM**
          Manages customer relationship and the front end of the sales pipeline, including:
          - Leads, opportunities
          - Customer profiles, marketing campaigns, sales funnel
          - Reporting, analytics, sales team setups
          If the issue involves customer relationship management, leads/opportunities, or sales funnels, select **CRM**.

        - **Buying**
          Manages procurement processes, covering:
          - RFQs, purchase orders, purchase invoices
          - Supplier management, supplier scorecards
          - Procurement-related reports and configurations
          If the issue concerns purchase requests, purchase orders, or supplier workflows, choose **Buying**.

        - **Selling**
          Oversees sales processes, including:
          - Quotations, sales orders, sales invoices
          - Customer data management, payment collections
          - POS, delivery notes, sales performance tracking
          If the issue relates to the sales workflow, order management, POS, or customer quotations, select **Selling**.

        - **Loans**
          Manages the full loan lifecycle, including:
          - Loan applications, disbursements, repayments
          - Interest, penalties, collateral management
          - Related reports and accounting
          If the issue relates to loan management and its processes, choose **Loans**.

        - **Stock**
          Handles inventory and warehousing, involving:
          - Inventory records, bin/warehouse operations
          - Stock transactions, batch/serial number tracking
          - Stock valuation, stock reconciliation
          If the issue is tied to inventory, warehousing, or material movement, choose **Stock**.

        - **Manufacturing**
          Oversees production and manufacturing workflows, including:
          - Bill of Materials, work orders, material resource planning
          - Subcontracting, capacity planning
          - Production dashboards, manufacturing reports
          If the issue relates to production work orders, scheduling, material planning, or BOM, select **Manufacturing**.

        - **Project**
          Supports project management and delivery, covering:
          - Projects, tasks, milestones
          - Time logs, resource allocation, cost tracking
          - Project reports and progress monitoring
          If the issue involves project tasks, Gantt charts, resource or cost management, choose **Project**.

        - **Support**
          Addresses customer support and after-sales service scenarios, including:
          - Issue (ticket) reception and tracking
          - Maintenance contracts, SLAs, priority handling
          - Warranty management, maintenance plans, support reports
          If the issue relates to customer service, ticket processing, or after-sales support, choose **Support**.

        - **Assets**
          Handles tangible and intangible asset management, including:
          - Asset acquisition, depreciation, disposal
          - Asset maintenance, asset reports
          - Compliance and asset audits
          If the issue concerns asset acquisition, depreciation, or disposal, select **Assets**.

        - **Quality**
          Manages quality control and inspection processes, covering:
          - Quality checks, inspection templates
          - Non-conformance tracking, supplier quality
          - Batch tracking and quality reports
          If the issue relates to incoming/outgoing inspection, quality audits, or similar, select **Quality**.

        - **Website**
          Manages website and portal features, including:
          - Website pages, blogs, content management
          - Website settings, custom themes
          If the issue ties to website building, page rendering, choose **Website**.

        - **Tools**
          Includes various utilities and collaboration features, such as:
          - To-do lists, calendars, dashboards
          - Kanban views, global search
          - Internal collaboration/organization tools
          If the issue involves these collaborative/organizational utilities, select **Tools**.

        - **Integrations**
          Manages external platform or system connections, including:
          - Third-party payments, logistics, social media APIs
          If the issue involves integrating with third-party systems, select **Integrations**.

        - **Regional**
          Handles localization and region-specific requirements, involving:
          - Multi-language translations, local settings
          - Local tax structures, financial report formats
          - Regional or country-specific compliance
          If the issue involves localization, translations, or region-specific tax/legal requirements, choose **Regional**.

        ### Fields to Extract
        Extract the following fields if they exist. If not present, leave them blank:
        - preconditions
        - steps_to_reproduce
        - expected_results
        - actual_results

        Output the result in **strict JSON** format with the structure:
        {{
        "category": "<category>",
        "reason": "<reason>",
        "components": ["<component_1>", "<component_2>", ...],
        "preconditions": "<preconditions>",
        "steps_to_reproduce": "<steps_to_reproduce>",
        "expected_results": "<expected_results>",
        "actual_results": "<actual_results>"
        }}

        Title: {title}
        Description: {body}
        Labels: {label}
        """.strip()

        try:
            while True:
                response = openai.ChatCompletion.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You classify issues and extract relevant fields."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=500
                )
                content = response['choices'][0]['message']['content'].strip()
                content = content.strip().lstrip('```json').rstrip('```').strip()
                result = json.loads(content)

                if result.get("category") not in categories or not all(
                        comp in components_list for comp in result.get("components", [])):
                    continue

                break

        except Exception as e:
            result = {
                "category": "Other",
                "reason": f"Error processing issue: {str(e)}",
                "components": "",
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
            analysis = await self.classify_issue_and_analyze(issue.get("title"), issue.get("body", ""), labels, is_pull_request)
            classification = {
                "number": issue.get("number"),
                "category": analysis["category"],
                "reason": analysis["reason"],
                "preconditions": analysis["preconditions"],
                "steps_to_reproduce": analysis["steps_to_reproduce"],
                "expected_results": analysis["expected_results"],
                "actual_results": analysis["actual_results"],
                "labels": ", ".join(labels),
                "components": ", ".join(analysis["components"])
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
        return pd.DataFrame(all_data), pd.DataFrame(classifications)

    def save_to_csv(self, new_df, file_name):
        if os.path.exists(file_name):
            existing_df = pd.read_csv(file_name)
            combined_df = pd.concat([existing_df, new_df]).drop_duplicates(subset="number")
            combined_df.to_csv(file_name, index=False)
        else:
            new_df.to_csv(file_name, index=False)

    async def main(self, limit=50):
        print(f"Fetching up to {limit} issues and pull requests from ERPNext repository...")
        await self.fetch_issues_with_limit(limit)


if __name__ == "__main__":
    processor = IssueProcessor()
    asyncio.run(processor.main(limit=50))
