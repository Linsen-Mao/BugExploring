from scripts.github_issue_crawler import run_github_issue_crawler
from scripts.merge_issue_pul_request_processor import execute_issue_pull_request_processing
from scripts.github_issue_processor import process_and_filter_github_issues
from scripts.bug_clustering_processor import execute_bug_clustering
from scripts.bug_data_merger import run_bug_save_step_processing
from scripts.bug_save_section_processor import run_bug_save_section_processing
from scripts.bug_scenario_processor import process_and_save_bug_scenarios
from scripts.bug_section_processor import run_bug_processing
from scripts.bug_split_processor import run_bug_split_processing

if __name__ == "__main__":
    owner = 'frappe'
    repo = 'erpnext'
    max_issue_id = 44811
    min_issue_id = 1
    seed_id = 44616

    import sys

    sys.setrecursionlimit(5000)

    print("Starting the execution pipeline...")
    print("Step 1: Running GitHub Issue Crawler...")
    # run_github_issue_crawler(owner, repo, max_issue_id, min_issue_id)

    print("Step 2: Executing Issue Pull Request Processing...")
    # execute_issue_pull_request_processing(repo)

    print("Step 3: Processing and Filtering GitHub Issues...")
    # process_and_filter_github_issues(repo)

    print("Step 4: Running Bug Processing...")
    # run_bug_processing()

    print("Step 5: Running Bug Save Section Processing...")
    # run_bug_save_section_processing()

    print("Step 6: Running Bug Split Processing...")
    # run_bug_split_processing()

    print("Step 7: Running Bug Save Step Processing...")
    run_bug_save_step_processing()

    print("Step 8: Executing Bug Clustering...")
    execute_bug_clustering()

    print("Step 9: Processing and Saving Bug Scenarios...")
    process_and_save_bug_scenarios(44199)

    print("Execution pipeline completed successfully.")
