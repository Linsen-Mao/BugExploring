import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from tqdm import tqdm

from bug_improving.utils.crawel_util import CrawelUtil
from bug_improving.utils.file_util import FileUtil
from bug_improving.utils.list_util import ListUtil
from config import SYNC_CRAWEL_NUM, DATA_DIR

class GitHubIssueCrawler:
    """
    A class to manage the crawling and saving of GitHub issues and pull requests.
    """

    def __init__(self,owner, repo, max_issue_id, min_issue_id):
        """
        Initializes the crawler with GitHub authentication and repository details.
        """
        load_dotenv()
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.headers = {
            'Authorization': f'token {self.github_token}',
        } if self.github_token else None
        self.folder_name = "issues_pulls"
        # owner = 'frappe'
        # repo = 'erpnext'
        # max_issue_id = 44643
        # min_issue_id = 44000
        self.owner = owner  # Repository owner
        self.repo = repo
        self.max_issue_id = max_issue_id  # Maximum issue ID to crawl
        self.min_issue_id = min_issue_id  # Minimum issue ID to crawl
        # self.owner = 'odoo'  # Repository owner
        # self.repo = 'odoo'  # Repository name
        # self.max_issue_id = 190657  # Maximum issue ID to crawl
        # self.min_issue_id = 190620  # Minimum issue ID to crawl
        self.filepath = Path(DATA_DIR, self.repo, self.folder_name)
        self._prepare_directory()

    def _prepare_directory(self):
        """
        Ensures the target directory for saving issue data exists.
        """
        if not os.path.exists(self.filepath):
            os.makedirs(self.filepath)

    async def _fetch_issues_async(self, issue_urls, headers):
        """
        Fetch issues asynchronously from GitHub.

        :param issue_urls: List of issue URLs to fetch.
        :param headers: HTTP headers for authentication.
        :return: List of responses.
        """
        return await CrawelUtil.crawel_by_async(issue_urls, headers)

    def crawl_and_save_issues(self):
        """
        Main method to crawl GitHub issues and save them as JSON files.
        """
        issue_urls = CrawelUtil.get_github_issue_urls(
            self.owner,
            self.repo,
            max_issue_id=self.max_issue_id,
            min_issue_id=self.min_issue_id
        )

        issue_urls_list = ListUtil.list_of_groups(issue_urls, SYNC_CRAWEL_NUM)
        loop = asyncio.get_event_loop()

        for index, issue_urls in tqdm(enumerate(issue_urls_list), ascii=True):
            responses = loop.run_until_complete(
                self._fetch_issues_async(issue_urls, self.headers)
            )
            FileUtil.dump_json(Path(self.filepath, f'{self.folder_name}_{index}.json'), responses)

# Exposed function to run the issue crawler
def run_github_issue_crawler(owner, repo, max_issue_id, min_issue_id):
    """
    Run the GitHub issue crawler.
    """
    crawler = GitHubIssueCrawler(owner, repo, max_issue_id, min_issue_id)
    crawler.crawl_and_save_issues()

if __name__ == "__main__":
    run_github_issue_crawler('frappe', 'erpnext', 44643, 44400)