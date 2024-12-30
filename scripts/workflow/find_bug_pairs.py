from bug_improving.utils.file_util import FileUtil
from bug_improving.utils.path_util import PathUtil


def find_bug_pairs():
    pairs = []  # To store the resulting pairs
    bugs = FileUtil.load_pickle(PathUtil.get_filtered_bugs_filepath())
    # Extract clusters for each bug
    bug_clusters = {}  # Dictionary to store clusters per bug
    for bug in bugs:
        clusters = set()
        description = getattr(bug, 'description', None)
        if not description:
            continue
        steps_to_reproduce = getattr(description, 'steps_to_reproduce', [])
        for step in steps_to_reproduce:
            cluster_index = getattr(step, 'cluster_index', None)
            if cluster_index is not None:
                clusters.add(cluster_index)
        bug_clusters[getattr(bug, 'id', None)] = clusters

    # Compare clusters between bugs to find pairs
    for bug_id_1, clusters_1 in bug_clusters.items():
        for bug_id_2, clusters_2 in bug_clusters.items():
            if bug_id_1 >= bug_id_2:
                continue  # Avoid duplicate pairs and self-comparison

            # Check for overlap in clusters, excluding None
            if clusters_1 & clusters_2:
                pairs.append((bug_id_1, bug_id_2))

                # Stop if 5 pairs are found
                if len(pairs) == 7:
                    return pairs

    return pairs
if __name__ == '__main__':
    pairs = find_bug_pairs()
    print(pairs)