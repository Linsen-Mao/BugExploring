from pathlib import Path

from langsmith import traceable
from tqdm import tqdm
from bug_improving.utils.file_util import FileUtil
from bug_improving.utils.path_util import PathUtil
from config import DATA_DIR

class BugDataMerger:
    """
    Class to handle merging of step JSONs and processing bug data.
    """

    def __init__(self):
        # Initialize paths
        self.section_dir = Path(DATA_DIR, "step")
        self.all_dir = Path(self.section_dir, "all")
        self.all_dir.mkdir(exist_ok=True)

    @staticmethod
    @traceable(run_type="chain")
    def get_s2r_result_by_bug_id(bug_id, step_results):
        """
        Retrieve the steps-to-reproduce (S2R) result for a given bug ID.
        """
        for step_result in step_results:
            if step_result["bug_id"] == bug_id:
                return step_result
        return None

    @traceable(run_type="chain")
    def merge_step_jsons(self):
        """
        Merge all JSON files in the step directory into a single file and organize the directory structure.
        """
        # Get all JSON files in the step directory
        json_files = list(self.section_dir.glob("bug_id_ans_pairs_*.json"))

        if not json_files:
            print("No JSON files found in the step directory.")
            return

        # Merge all JSON files
        merged_results = []
        seen_bug_ids = set()  # Track unique bug IDs

        print("Merging JSON files...")
        for json_file in tqdm(json_files, ascii=True):
            try:
                current_data = FileUtil.load_json(json_file)

                # Process each entry and keep only unique bug IDs
                for entry in current_data:
                    bug_id = entry.get("bug_id")
                    if bug_id and bug_id not in seen_bug_ids:
                        merged_results.append(entry)
                        seen_bug_ids.add(bug_id)

            except Exception as e:
                print(f"Error processing file {json_file}: {str(e)}")
                continue

        # Save merged results
        output_file = Path(self.all_dir, "bug_id_ans_pairs.json")
        FileUtil.dump_json(output_file, merged_results)

        print(f"Successfully merged {len(json_files)} files.")
        print(f"Total unique bug entries: {len(merged_results)}")
        print(f"Merged file saved to: {output_file}")

    @traceable(run_type="chain")
    def update_bugs_with_steps(self, bugs):
        """
        Update bugs with steps-to-reproduce information from the merged JSON file.
        """
        step_filename = Path(DATA_DIR, "step", "all", "bug_id_ans_pairs.json")
        step_results = FileUtil.load_json(step_filename)

        for bug in tqdm(bugs, ascii=True):
            step_result = self.get_s2r_result_by_bug_id(bug.id, step_results)
            if step_result:
                bug.description.get_steps_to_reproduce_from_dict(step_result["ans"])
            else:
                bug.description.steps_to_reproduce = []

@traceable(run_type="chain")
def run_bug_save_step_processing():
    """
    Merge JSON files and update bugs with steps-to-reproduce information.
    """
    merger = BugDataMerger()
    merger.merge_step_jsons()

    filtered_bugs_filepath = PathUtil.get_filtered_bugs_filepath()
    bugs = FileUtil.load_pickle(filtered_bugs_filepath)

    merger.update_bugs_with_steps(bugs)

    FileUtil.dump_pickle(filtered_bugs_filepath, bugs)

if __name__ == "__main__":
    run_bug_save_step_processing()
