import logging
from datetime import datetime
from pathlib import Path
import json
from tqdm import tqdm

from bug_improving.types.bug import Bugs, Bug
from bug_improving.utils.file_util import FileUtil
from bug_improving.utils.path_util import PathUtil
from config import DATA_DIR

class GitHubIssueProcessor:
    """
    Class to process GitHub Issues and filter them into Bug objects.
    """

    @staticmethod
    def github_issue_to_bug(issue):
        """
        Converts a GitHub Issue to a Bug object dictionary.
        """

        def parse_datetime(date_str):
            """
            Parses a datetime string, handling formats with and without 'Z'.
            """
            if not date_str:
                return None
            try:
                return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S").isoformat()
            except ValueError:
                try:
                    return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ").isoformat()
                except ValueError:
                    return None

        description_text = issue.get("body", "No description provided")
        comments = [{"text": description_text}] if description_text else []

        labels = issue.get("labels", [])
        component = labels[0]["name"] if labels else "General"

        status_map = {"open": "OPEN", "closed": "CLOSED"}
        status = status_map.get(issue.get("state", "").lower(), "UNKNOWN")

        return {
            "id": issue.get("number"),
            "summary": issue.get("title", "No summary available"),
            "description": {"text": description_text},
            "comments": comments,
            "product": "GitHub",
            "component": component,
            "creation_time": parse_datetime(issue.get("created_at")),
            "last_change_time": parse_datetime(issue.get("updated_at")),
            "closed_time": parse_datetime(issue.get("closed_at")),
            "status": status,
            "type": "ISSUE" if "pull_request" not in issue else "PULL_REQUEST",
            "attachments": [],
            "history": [],
        }

    def process_github_issues(self,repo):
        """
        Process GitHub issues into filtered Bug objects and save the results.
        """
        # Load GitHub Issues data
        github_issues_filepath = Path(DATA_DIR) / repo / "issues_pulls.json"
        with open(github_issues_filepath, "r") as f:
            github_issues = json.load(f)

        # Convert GitHub Issues to Bug format
        bugs_data = [self.github_issue_to_bug(issue) for issue in github_issues]

        # Save intermediate data
        bugs_filepath = PathUtil.get_bugs_filepath()
        FileUtil.dump_json(bugs_filepath, bugs_data)

        # Load and process Bugs
        bugs = FileUtil.load_json(bugs_filepath)

        bug_list = []
        logging.warning(f"filter {len(bugs)} bugs by desc.text")
        for bug in tqdm(bugs, ascii=True):
            bug = Bug.from_dict(bug)
            if bug.description.text:
                bug_list.append(bug)
        bugs = Bugs(bug_list)
        logging.warning(f"{bugs.get_length()} bugs left")

        logging.warning(f"filter {len(bugs)} bugs by most bug desc don't consist of log")
        bug_list = []
        for bug in tqdm(bugs, ascii=True):
            if not bug.is_most_desc_as_log():
                bug_list.append(bug)
        bugs = Bugs(bug_list)
        logging.warning(f"{bugs.get_length()} bugs left")

        logging.warning(f"filter {len(bugs)} bugs by status")
        bug_list = []
        for bug in tqdm(bugs, ascii=True):
            if bug.status in ['CLOSED', 'RESOLVED', 'VERIFIED']:
                bug_list.append(bug)
        bugs = Bugs(bug_list)
        logging.warning(f"{bugs.get_length()} bugs left")

        # Final processing and saving
        bugs.overall_bugs()
        filtered_bugs_filepath = PathUtil.get_filtered_bugs_filepath()
        FileUtil.dump_pickle(filtered_bugs_filepath, bugs)

# Exposed method for external use
def process_and_filter_github_issues(repo):
    """
    Entry point to process and filter GitHub issues.
    """
    processor = GitHubIssueProcessor()
    processor.process_github_issues(repo)


if __name__ == '__main__':
    process_and_filter_github_issues('erpnext')