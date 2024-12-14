import json
from datetime import datetime
from pathlib import Path

import openai
from langsmith import traceable
from tqdm import tqdm

from bug_improving.pipelines.constructor import StepSplitter
from bug_improving.utils.file_util import FileUtil
from bug_improving.utils.llm_util import LLMUtil
from bug_improving.utils.path_util import PathUtil
from config import DATA_DIR

class BugSplitProcessor:
    """
    Class to process bugs and interact with LLM for step-splitting.
    """

    def __init__(self):
        """Initialize BugProcessor with necessary configurations."""
        openai.api_key = LLMUtil.OPENAI_API_KEY
        self.bugs = FileUtil.load_pickle(PathUtil.get_filtered_bugs_filepath())
        self.step_result_filepath = Path(DATA_DIR, "step")

    @traceable(run_type="chain")
    def process_bug(self, bug, with_instances=None, with_step_type=True):
        """
        Process a single bug, interacting with LLM for step-splitting if applicable.

        Args:
            bug: The bug object to process.
            with_instances: Optional parameter to include instances.
            with_step_type: Optional parameter to include step types.

        Returns:
            A dictionary containing bug ID and its corresponding processed answer.
        """
        if not bug.description.steps_to_reproduce:
            return {"bug_id": bug.id, "ans": []}

        try:
            # Get the step-splitting answer
            answer, _ = StepSplitter.split_s2r(bug, with_instances, with_step_type)

            # Convert the string-formatted JSON answer to a Python object
            try:
                answer = answer.strip("```json").strip("```")
                ans_json = json.loads(answer)
                return {"bug_id": bug.id, "ans": ans_json}
            except json.JSONDecodeError as json_error:
                print(f"JSON decoding failed for bug {bug.id}: {json_error}")
                return {"bug_id": bug.id, "ans": []}

        except Exception as e:
            print(f"Unexpected error for bug {bug.id}: {e}")
            return {"bug_id": bug.id, "ans": []}

    @traceable(run_type="chain")
    def process_all_bugs(self, with_instances=None, with_step_type=True):
        """
        Process all bugs in the dataset and save results incrementally.

        Args:
            with_instances: Optional parameter to include instances.
            with_step_type: Optional parameter to include step types.
        """
        bug_id_answer_pairs = []

        for index, bug in tqdm(enumerate(self.bugs), ascii=True):
            print(index)
            print(bug)
            result = self.process_bug(bug, with_instances, with_step_type)
            bug_id_answer_pairs.append(result)

            print("************************************************")
            if index % 100 == 0:
                self._save_results(bug_id_answer_pairs)
                bug_id_answer_pairs = []

        if bug_id_answer_pairs:
            self._save_results(bug_id_answer_pairs)

    @traceable(run_type="chain")
    def _save_results(self, bug_id_answer_pairs):
        """
        Save the results to a JSON file with a timestamp.

        Args:
            bug_id_answer_pairs: List of processed bug ID and answer pairs.
        """
        current_datetime = datetime.now()
        FileUtil.dump_json(
            Path(self.step_result_filepath, f"bug_id_ans_pairs_{current_datetime}.json"),
            bug_id_answer_pairs
        )

@traceable(run_type="chain")
def run_bug_split_processing(with_instances=None, with_step_type=True):
    """
    Function to create a BugProcessor instance and run the processing.

    Args:
        with_instances: Optional parameter to include instances.
        with_step_type: Optional parameter to include step types.
    """
    processor = BugSplitProcessor()
    processor.process_all_bugs(with_instances, with_step_type)

# Exposed method for running the processing
if __name__ == "__main__":
    run_bug_split_processing()
