import json
from datetime import datetime
from pathlib import Path

import openai
from langsmith import traceable
from tqdm import tqdm

from bug_improving.pipelines.constructor import SecSplitter
from bug_improving.utils.file_util import FileUtil
from bug_improving.utils.llm_util import LLMUtil
from bug_improving.utils.path_util import PathUtil
from config import DATA_DIR


class BugSectionProcessor:
    """Processes bugs into sections using SecSplitter and saves the results."""

    def __init__(self):
        """Initialize the processor, set the OpenAI API key and data paths."""
        openai.api_key = LLMUtil.OPENAI_API_KEY
        self.bugs = FileUtil.load_pickle(PathUtil.get_filtered_bugs_filepath())
        self.result_filepath = Path(DATA_DIR, "section")
        self.result_filepath.mkdir(parents=True, exist_ok=True)
        self.with_instances = self.bugs  # Used by SecSplitter to process sections

    @staticmethod
    def clean_json_string(answer):
        """Remove markdown code blocks and extra whitespace from an answer."""
        if answer is None:
            return None

        # Remove code fences if present
        if answer.startswith('```'):
            lines = answer.split('\n')
            # Remove the first code fence line
            if lines and lines[0].startswith('```'):
                lines = lines[1:]
            # Remove the last code fence line
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            answer = '\n'.join(lines)

        return answer.strip()

    @staticmethod
    def parse_json_safely(answer):
        """Parse JSON with multiple fallback attempts."""
        if answer is None:
            return None
        try:
            return json.loads(answer)
        except json.JSONDecodeError:
            cleaned_answer = BugSectionProcessor.clean_json_string(answer)
            try:
                return json.loads(cleaned_answer)
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON after cleaning: {str(e)}")
                print(f"Cleaned answer:\n{cleaned_answer}")
                raise

    @traceable(run_type="chain")
    def process_bug_batch(self, bug_batch, start_index):
        """Process a single batch of bugs, calling the LLM-based section splitting and storing results."""
        bug_id_answer_pairs = []
        for idx, bug in enumerate(bug_batch, start=start_index):
            print(f"Processing bug {idx}")
            print(bug)
            answer = None

            try:
                # This call to SecSplitter likely involves LLM interaction
                answer, _ = SecSplitter.split_section(bug, self.with_instances)
                ans_json = self.parse_json_safely(answer)
                if ans_json is not None:
                    bug_id_answer_pairs.append({
                        "bug_id": bug.id,
                        "ans": ans_json
                    })
            except Exception as e:
                print(f"Error processing bug {bug.id}: {str(e)}")
                print(f"Problematic answer: {answer}")
                continue

            print("*" * 50)

            # Save results every 100 bugs
            if (idx + 1) % 100 == 0:
                self.save_results(bug_id_answer_pairs)
                bug_id_answer_pairs = []

        # Save remaining results
        if bug_id_answer_pairs:
            self.save_results(bug_id_answer_pairs)

    @traceable(run_type="chain")
    def save_results(self, bug_id_answer_pairs):
        """Write bug_id-answer pairs to a JSON file with timestamp."""
        if not bug_id_answer_pairs:
            return

        current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.result_filepath / f"bug_id_ans_pairs_{current_datetime}.json"

        try:
            FileUtil.dump_json(output_file, bug_id_answer_pairs)
            print(f"Successfully saved results to {output_file}")
        except Exception as e:
            print(f"Error saving results: {str(e)}")
            backup_file = self.result_filepath / f"backup_{current_datetime}.json"
            FileUtil.dump_json(backup_file, bug_id_answer_pairs)

    @traceable(run_type="chain")
    def process_all_bugs(self):
        """Process all bugs in batches, orchestrating everything via a progress bar."""
        total_bugs = len(self.bugs)
        batch_size = 100

        with tqdm(total=total_bugs, ascii=True) as pbar:
            for start_idx in range(0, total_bugs, batch_size):
                end_idx = min(start_idx + batch_size, total_bugs)
                current_batch = self.bugs[start_idx:end_idx]
                self.process_bug_batch(current_batch, start_idx)
                pbar.update(len(current_batch))

@traceable(run_type="chain")
def run_bug_processing():
    """Run the bug processing workflow."""
    processor = BugSectionProcessor()
    processor.process_all_bugs()


if __name__ == "__main__":
    run_bug_processing()
