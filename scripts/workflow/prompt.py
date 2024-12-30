classify_and_extract_prompt = """
Classify the following {item_type} into one of these categories and extract the following fields if present. If not present, leave the field blank:

- UI/UX: Problems related to graphical user interface (GUI) and user experience that do not affect business logic or database data. This includes:
  - Layout, alignment, or design issues.
  - Data display errors due to incorrect UI rendering (e.g., filters working correctly in the backend but displaying incorrect results in the frontend).
  - Interaction design problems, such as unresponsive buttons, unclear labels, or navigation inconsistencies.
  - Enhancements to improve the visual experience or accessibility without altering underlying logic or data.

- ERP Workflow: Issues or changes that directly impact ERP core business logic, focusing on critical processes and database interactions. This includes:
  - Errors or fixes related to core modules like financial management, inventory control, order management, or procurement workflows.
  - Problems where the functionality fails to reflect intended business rules or logic.
  - Missing or incorrect data handling logic, such as filters not applying correctly in backend queries.
  - Fixes or enhancements to essential workflows ensuring accurate and reliable ERP operations.

- General Workflow: Issues affecting business logic or database interactions but not tied to ERP core workflows. These typically include:
  - Improvements or fixes to secondary modules or optional processes.
  - Modifications to auxiliary workflows, such as automation scripts or custom module interactions.

- Performance: Issues related to system efficiency, scalability, or integration. Examples include:
  - Slow query performance, resource inefficiency, or delayed responses in ERP operations.
  - Compatibility issues with third-party integrations (e.g., payment gateways, external CRMs) or between ERP modules.
  - Scalability concerns under high system load or with large datasets.

- Docs & Validation: Issues involving incorrect, missing, or incomplete documentation, as well as problems with testing or validation logic. This includes:
  - Errors or ambiguities in user manuals, API documentation, or technical guides.
  - Insufficient or missing testing for workflows, leading to logical gaps or regressions.
  - Failures in data validation rules, such as accepting invalid inputs or missing critical constraints.

- Security: Issues or vulnerabilities compromising system confidentiality, integrity, or availability. Examples include:
  - Unsecured sensitive data, such as plaintext passwords or unencrypted financial records.
  - Incorrect user access control, allowing unauthorized users to perform restricted actions.
  - Exploitable vulnerabilities, such as SQL injection or cross-site scripting (XSS).

- Other: Issues that do not clearly fit into the above categories, including:
  - Minor inconsistencies or cosmetic issues that are not part of the primary workflow.
  - Rare edge cases with limited business impact but requiring attention.

{additional_instructions}

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

def get_classify_and_extract_prompt(is_pull_request, title, body):
    item_type = "pull request" if is_pull_request else "issue"
    additional_instructions = (
        "If this pull request addresses an issue, classify it based on the issue it resolves. "
        "If it introduces a new feature or enhancement, classify it based on the relevant category."
        if is_pull_request else ""
    )

    prompt = classify_and_extract_prompt.format(
        item_type=item_type,
        additional_instructions=additional_instructions,
        title=title,
        body=body
    )

    return prompt
