import ast
from pathlib import Path

import openai
from json_repair import repair_json
from langsmith import traceable
from tqdm import tqdm

from bug_improving.pipelines.generator import ScenarioLinker, ScenarioCombiner
from bug_improving.utils.file_util import FileUtil
from bug_improving.utils.graph_util import GraphUtil
from bug_improving.utils.llm_util import LLMUtil
from bug_improving.utils.path_util import PathUtil
from config import DATA_DIR


class BugScenarioProcessor:
    """
    A class to process and link bug scenarios, leveraging LLM for scenario linking and combining.
    """

    def __init__(self):
        openai.api_key = LLMUtil.OPENAI_API_KEY
        self.bugs = FileUtil.load_pickle(PathUtil.get_filtered_bugs_filepath())
        self.model_name = LLMUtil.GPT4_MODEL_NAME
        self.with_instances = self.bugs
        self.with_step_cluster = True

    @staticmethod
    def get_bug_id_pairs(seed_bug_id, bugs):
        """
        Generate pairs of bug IDs from a seed bug ID and a list of bugs.
        """
        bug_id_pairs = []
        for bug in bugs:
            bug_id_pairs.append((seed_bug_id, bug.id))
        return bug_id_pairs

    @traceable(run_type="chain")
    def link_scenario(self, bug_pair, with_instances, model_name):
        """
        Link scenarios for a given pair of bugs using an LLM.
        """
        answer, _ = ScenarioLinker.link_scenario(bug_pair, with_instances, model_name, temperature=0.35)
        fixed_json = repair_json(answer)
        return ast.literal_eval(fixed_json)

    @traceable(run_type="chain")
    def combine_scenario(self, bug_pair, with_instances, with_step_cluster, model_name):
        """
        Combine scenarios for a given pair of bugs using an LLM.
        """
        answer, _ = ScenarioCombiner.combine_scenario(bug_pair, with_instances, with_step_cluster, model_name)
        fixed_json = repair_json(answer)
        return ast.literal_eval(fixed_json)

    @traceable(run_type="chain")
    def process_bug_scenarios(self, seed_bug_id, foldername="scenarios"):
        """
        Process and save linked and combined scenarios for a given seed bug ID.
        """
        filename = f"{seed_bug_id}"

        GraphUtil.BUGS = self.bugs
        GraphUtil.get_bug_id_bug_dict(self.bugs)
        GraphUtil.get_index_cluster_dict(self.bugs)
        GraphUtil.get_index_cluster_expected_actual_result_dict()

        bug_list, bug_ranking_details_dict = GraphUtil.find_relevant_ranked_bugs_by_bug_id_with_step_type(
            self.bugs, seed_bug_id
        )

        bug_id_pairs = self.get_bug_id_pairs(seed_bug_id, bug_list[0:10])
        answers = []

        for bug_id_pair in tqdm(bug_id_pairs, ascii=True):
            bug_pair = (
                self.bugs.get_bug_by_id(bug_id_pair[0]),
                self.bugs.get_bug_by_id(bug_id_pair[1])
            )

            # Link scenarios
            linked_answer = self.link_scenario(bug_pair, self.with_instances, self.model_name)
            answers.append({
                "bug_id_pair": bug_id_pair,
                "answer": linked_answer
            })
            FileUtil.dump_json(Path(DATA_DIR, foldername, f"{filename}.json"), answers)

            # Combine scenarios
            combined_answer = self.combine_scenario(bug_pair, self.with_instances, self.with_step_cluster,
                                                    self.model_name)
            answers.append({
                "bug_id_pair": bug_id_pair,
                "answer": combined_answer
            })
            FileUtil.dump_json(Path(DATA_DIR, foldername, f"{filename}.json"), answers)


@traceable(run_type="chain")
def process_and_save_bug_scenarios(seed_bug_id):
    """
    Public method to process and save bug scenarios for a given seed bug ID.
    """
    processor = BugScenarioProcessor()
    processor.process_bug_scenarios(seed_bug_id)

if __name__ == "__main__":
    process_and_save_bug_scenarios(2733806130)
