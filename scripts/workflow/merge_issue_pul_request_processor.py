from pathlib import Path
from tqdm import tqdm
from bug_improving.utils.file_util import FileUtil
from config import DATA_DIR


class MergeIssuePullRequestProcessor:
    """
    A class to process issue and pull request data from a GitHub repository.
    """

    def __init__(self, repo_name, folder_name="issues_pulls"):
        """
        Initialize the processor with the repository name and folder name.

        :param repo_name: Name of the repository to process.
        :param folder_name: Name of the folder containing issue/pull request data.
        """
        self.repo_name = repo_name
        self.folder_name = folder_name
        self.filepath = Path(DATA_DIR, repo_name)

    def process_issues_and_pulls(self):
        """
        Process all JSON files in the specified folder, combining their content into a single file.
        """
        # Get all JSON filenames in the directory
        filenames = FileUtil.get_file_names_in_directory(Path(self.filepath, self.folder_name), 'json')
        filenames = sorted(filenames, key=lambda x: (len(x), x))

        # Load and combine issues and pull requests from all files
        issues_pull_requests = []
        for filename in tqdm(filenames, ascii=True):
            temp_issues_pull_requests = FileUtil.load_json(filename)
            issues_pull_requests.extend(temp_issues_pull_requests)

        # Save the combined data to a new JSON file
        FileUtil.dump_json(Path(self.filepath, f"{self.folder_name}.json"), issues_pull_requests)


# Public method to execute the processing
def execute_issue_pull_request_processing(repo_name):
    """
    Execute the issue and pull request processing for a specific repository.
    """
    # repo_name = 'odoo'
    processor = MergeIssuePullRequestProcessor(repo_name)
    processor.process_issues_and_pulls()

if __name__ == '__main__':
    execute_issue_pull_request_processing('erpnext')