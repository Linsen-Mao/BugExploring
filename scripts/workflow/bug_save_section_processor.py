from pathlib import Path

from langsmith import traceable
from tqdm import tqdm
from bug_improving.types.description import Description
from bug_improving.utils.file_util import FileUtil
from bug_improving.utils.path_util import PathUtil
from config import DATA_DIR

class BugSaveSectionProcessor:
    """
    Class for handling bug processing and JSON merging tasks.
    """

    @staticmethod
    def get_sec_result_by_bug_id(bug_id, sec_results):
        """
        Retrieve the section result matching the given bug ID.
        """
        for sec_result in sec_results:
            if sec_result["bug_id"] == bug_id:
                return sec_result
        return None

    @staticmethod
    @traceable(run_type="chain")
    def merge_section_jsons():
        """
        Merge all JSON files in the sections directory into a single file and organize the directory structure.
        """
        # Setup paths
        section_dir = Path(DATA_DIR, "section")
        all_dir = Path(section_dir, "all")
        all_dir.mkdir(exist_ok=True)

        # Get all JSON files in the section directory
        json_files = list(section_dir.glob("bug_id_ans_pairs_*.json"))

        if not json_files:
            print("No JSON files found in the section directory.")
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
        output_file = Path(all_dir, "bug_id_ans_pairs.json")
        FileUtil.dump_json(output_file, merged_results)

        print(f"Successfully merged {len(json_files)} files.")
        print(f"Total unique bug entries: {len(merged_results)}")
        print(f"Merged file saved to: {output_file}")

    @staticmethod
    @traceable(run_type="chain")
    def process_bugs():
        """
        Process bugs and update their descriptions with sections from the merged JSON file.
        """
        foldername = "all"

        # Load bugs and section results
        bugs = FileUtil.load_pickle(PathUtil.get_filtered_bugs_filepath())
        sec_results = FileUtil.load_json(Path(DATA_DIR, "section", foldername, "bug_id_ans_pairs.json"))

        print("Processing bugs...")
        for bug in tqdm(bugs, ascii=True):
            sec_result = BugSaveSectionProcessor.get_sec_result_by_bug_id(bug.id, sec_results)
            if sec_result:
                bug.description.get_sections_from_dict(sec_result["ans"])
            else:
                bug.description = Description(bug, bug.description.text)

        # Save updated bugs to a pickle file
        filtered_bugs_filepath = PathUtil.get_filtered_bugs_filepath()
        FileUtil.dump_pickle(filtered_bugs_filepath, bugs)

        print(f"Processed bugs saved to: {filtered_bugs_filepath}")

@traceable(run_type="chain")
def run_bug_save_section_processing():
    """
    Run the bug processing and JSON merging tasks.
    """
    BugSaveSectionProcessor.merge_section_jsons()
    BugSaveSectionProcessor.process_bugs()

if __name__ == "__main__":
    run_bug_save_section_processing()
