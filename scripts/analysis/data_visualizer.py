import pandas as pd
import matplotlib.pyplot as plt
import re


class DataVisualizer:
    def __init__(self, file_path):
        self.data = pd.read_csv(file_path)
        self._clean_data()

    def _clean_text(self,text):
        if pd.isna(text):
            return text
        text = re.sub(r'[^\x00-\x7F\u4e00-\u9fff\s,]', '', str(text))
        return text

    def _clean_data(self):
        for column in self.data.columns:
            if self.data[column].dtype == 'object':
                self.data[column] = self.data[column].apply(self._clean_text)

        self.data['D_nonempty'] = self.data['preconditions'].notna()
        self.data['E_nonempty'] = self.data['steps_to_reproduce'].notna()
        self.data['F_nonempty'] = self.data['expected_results'].notna()
        self.data['G_nonempty'] = self.data['actual_results'].notna()
        self.data['D_or_E'] = self.data['D_nonempty'] | self.data['E_nonempty']
        self.data['F_and_G'] = self.data['F_nonempty'] & self.data['G_nonempty']
        self.data['D_or_E_and_F_and_G'] = self.data['D_or_E'] & self.data['F_and_G']

    def plot_category_distribution(self, save=False):
        plt.figure(figsize=(8, 6))
        category_counts = self.data['category'].value_counts(normalize=True) * 100
        plt.pie(category_counts,
                labels=category_counts.index,
                autopct='%1.1f%%',
                startangle=140)
        plt.title('Proportion of Each Category')
        plt.axis('equal')
        if save:
            plt.savefig('../data-analysis/category_distribution.png', bbox_inches='tight', dpi=300)
            plt.close()
        else:
            plt.show()

    def plot_column_proportions(self, save=False):
        plt.figure(figsize=(10, 6))
        columns_proportion = {
            'D (preconditions)': self.data['D_nonempty'].mean() * 100,
            'E (steps)': self.data['E_nonempty'].mean() * 100,
            'F (expected)': self.data['F_nonempty'].mean() * 100,
            'G (actual)': self.data['G_nonempty'].mean() * 100,
            'D or E & F and G': self.data['D_or_E_and_F_and_G'].mean() * 100
        }
        bars = plt.bar(range(len(columns_proportion)),
                       list(columns_proportion.values()),
                       tick_label=list(columns_proportion.keys()))
        for idx, rect in enumerate(bars):
            height = rect.get_height()
            plt.text(rect.get_x() + rect.get_width() / 2., height,
                     f'{height:.1f}%',
                     ha='center', va='bottom')
        plt.xticks(rotation=45, ha='right')
        plt.title('Proportion of Columns')
        plt.tight_layout()
        if save:
            plt.savefig('../data-analysis/column_proportions.png', bbox_inches='tight', dpi=300)
            plt.close()
        else:
            plt.show()

    def plot_label_distribution(self, save=False):
        plt.figure(figsize=(16, 6))
        labels_split = self.data['labels'].dropna().str.split(',').explode().str.strip()
        labels_counts = labels_split.value_counts(normalize=True) * 100
        plt.bar(range(len(labels_counts)), labels_counts.values)
        plt.xticks(range(len(labels_counts)), labels_counts.index, rotation=45, ha='right')
        plt.title('Proportion of Each Label')
        plt.ylabel('Percentage (%)')
        for i, v in enumerate(labels_counts.values):
            if v >= 1:
                plt.text(i, v, f'{v:.1f}%', ha='center', va='bottom')
        plt.tight_layout()
        if save:
            plt.savefig('../data-analysis/label_distribution.png', bbox_inches='tight', dpi=300)
            plt.close()
        else:
            plt.show()

    def plot_component_distribution(self, save=False):
        plt.figure(figsize=(11, 11))
        components_split = self.data['component'].dropna().str.strip()
        component_counts = components_split.value_counts(normalize=True) * 100
        plt.pie(
            component_counts.values,
            labels=component_counts.index,
            autopct=lambda p: f'{p:.1f}%' if p > 1 else '',
            startangle=5,
            counterclock=False
        )
        plt.title('Proportion of Each Component')
        plt.tight_layout()
        if save:
            plt.savefig('../data-analysis/component_distribution_pie.png', bbox_inches='tight', dpi=300)
            plt.close()
        else:
            plt.show()

if __name__ == '__main__':
    visualizer = DataVisualizer('../data-analysis/filtered_issues.csv')
    save = True
    visualizer.plot_category_distribution(save)
    visualizer.plot_column_proportions(save)
    visualizer.plot_label_distribution(save)
    visualizer.plot_component_distribution(save)
