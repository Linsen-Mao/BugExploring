import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

class IssueSimilarityFilter:
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        self.model = SentenceTransformer(model_name)

    def preprocess_title(self, title):
        """Preprocess titles to remove '(backport #...)'."""
        return title.split("(backport")[0].strip()

    def filter_issues(self, save_groups=False, combined_text_filter=False):
        """
        Filters issues based on title similarity and optionally combined_text similarity.

        Args:
            save_groups (bool): Whether to save the groups with issue numbers.
            combined_text_filter (bool): Whether to apply combined_text similarity filtering.
        """
        classification_csv = 'erpnext_issues_classification.csv'
        all_issues_csv = 'erpnext_issues_all.csv'

        # Load the issues CSV file
        all_issues_data = pd.read_csv(all_issues_csv)

        # Step 1: Filter out invalid issues based on URL
        valid_issues = all_issues_data[
            all_issues_data['url'].str.startswith('https://github.com/frappe/erpnext/', na=False)
        ].copy()

        # Step 2: Preprocess titles
        valid_issues['title'] = valid_issues['title'].apply(self.preprocess_title)

        # Compute title embeddings and similarity matrix
        title_embeddings = self.model.encode(valid_issues['title'].tolist())
        title_similarity_matrix = cosine_similarity(title_embeddings)

        # Group issues by title similarity > 0.97
        title_threshold = 0.97
        title_groups = []
        unused_indices = set(range(len(valid_issues)))

        while unused_indices:
            current = unused_indices.pop()
            group = [current]
            for other in list(unused_indices):
                if title_similarity_matrix[current, other] > title_threshold:
                    group.append(other)
                    unused_indices.remove(other)
            title_groups.append(group)

        # Optionally save the title groups to a CSV file
        if save_groups:
            title_groups_data = []
            for group in title_groups:
                group_numbers = valid_issues.iloc[group]['number'].tolist()
                title_groups_data.append({"Group_Number": len(title_groups_data) + 1, "Issue_Numbers": group_numbers})
            title_groups_df = pd.DataFrame(title_groups_data)
            title_groups_df.to_csv('../data-analysis/groups.csv', index=False)

        # Load the classification CSV file
        classification_data = pd.read_csv(classification_csv)

        # Select one issue from each title group with the longest combined_text
        selected_titles = []
        for group in title_groups:
            group_issues = valid_issues.iloc[group].copy()
            # Map group issues to classification data by 'number'
            group_issues_filtered = classification_data[classification_data['number'].isin(group_issues['number'])].copy()
            if not group_issues_filtered.empty:
                group_issues_filtered['combined_text'] = (
                    group_issues_filtered['preconditions'].fillna('') + ' ' +
                    group_issues_filtered['steps_to_reproduce'].fillna('') + ' ' +
                    group_issues_filtered['expected_results'].fillna('') + ' ' +
                    group_issues_filtered['actual_results'].fillna('')
                )
                group_issues_filtered['combined_length'] = group_issues_filtered['combined_text'].fillna('').apply(len)
                selected_issue = group_issues_filtered.sort_values(by='combined_length', ascending=False).iloc[0]
                selected_titles.append(selected_issue)

        filtered_issues = pd.DataFrame(selected_titles)

        # Save issues after title filtering
        filtered_issues.to_csv('../data-analysis/filtered_issues.csv', index=False)

        # Optionally apply combined_text similarity filtering
        if combined_text_filter:
            embeddings = self.model.encode(filtered_issues['combined_text'].tolist())
            similarity_matrix = cosine_similarity(embeddings)

            # Group issues by combined_text similarity > 0.9
            combined_threshold = 0.9
            combined_groups = []
            unused_indices = set(range(len(filtered_issues)))

            while unused_indices:
                current = unused_indices.pop()
                group = [current]
                for other in list(unused_indices):
                    if similarity_matrix[current, other] > combined_threshold:
                        group.append(other)
                        unused_indices.remove(other)
                combined_groups.append(group)

            # Optionally save the combined_text groups to a CSV file
            if save_groups:
                combined_groups_data = []
                for group in combined_groups:
                    group_numbers = filtered_issues.iloc[group]['number'].tolist()
                    combined_groups_data.append({"Group_Number": len(combined_groups_data) + 1, "Issue_Numbers": group_numbers})
                combined_groups_df = pd.DataFrame(combined_groups_data)
                combined_groups_df.to_csv('../data-analysis/combined_groups.csv', index=False)

            # Select one issue from each combined_text group with the longest combined_text
            selected_issues = []
            for group in combined_groups:
                group_issues = filtered_issues.iloc[group].copy()
                selected_issue = group_issues.sort_values(by='combined_length', ascending=False).iloc[0]
                selected_issues.append(selected_issue)

            filtered_issues = pd.DataFrame(selected_issues)

            # Save the filtered issues to the context_filtered_issues.csv
            filtered_issues.to_csv('../data-analysis/context_filtered_issues.csv', index=False)

if __name__ == '__main__':
    filter_instance = IssueSimilarityFilter()
    filter_instance.filter_issues(save_groups=True, combined_text_filter=True)
