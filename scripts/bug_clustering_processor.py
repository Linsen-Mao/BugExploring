from pathlib import Path

from langsmith import traceable
from sentence_transformers import SentenceTransformer
from bug_improving.utils.file_util import FileUtil
from bug_improving.utils.path_util import PathUtil

class BugClusteringProcessor:
    """
    A class for processing bug data and applying clustering using sentence embeddings.
    """

    def __init__(self):
        """
        Initializes the BugClusteringProcessor with the necessary embedding model.
        """
        # You can choose the embedding model to use here
        # For example: 'all-MiniLM-L6-v2' or 'paraphrase-MiniLM-L6-v2'
        self.embedder = SentenceTransformer('paraphrase-MiniLM-L6-v2')

    @traceable(run_type="chain")
    def process_and_cluster_bugs(self):
        """
        Loads bug data, applies clustering, and saves the clustered data.
        """
        bugs_filepath = PathUtil.get_filtered_bugs_filepath()  # Retrieve the file path for filtered bugs
        bugs = FileUtil.load_pickle(bugs_filepath)  # Load the bugs data

        # Perform clustering on the bug steps using the embedding model
        bugs.merge_steps_by_fast_clustering(self.embedder)

        # Save the clustered data back to the file
        FileUtil.dump_pickle(bugs_filepath, bugs)

@traceable(run_type="chain")
def execute_bug_clustering():
    """
    Executes the bug clustering process by creating an instance of the processor and running it.
    """
    processor = BugClusteringProcessor()
    processor.process_and_cluster_bugs()

if __name__ == "__main__":
    execute_bug_clustering()
