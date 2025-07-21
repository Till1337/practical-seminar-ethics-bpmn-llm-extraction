from analysis.prompting_techniques import (
    zero_shot, few_shot, contrastive_cot,
    universal_self_consistency, chain_of_verification, tree_of_thoughts
)

class EthicsAnalyzer:
    def __init__(self, techniques=None):
        if techniques is None:
            self.techniques = {
                "zero_shot": zero_shot,
                "few_shot": few_shot,
                "contrastive_cot": contrastive_cot,
                "universal_self_consistency": universal_self_consistency,
                "chain_of_verification": chain_of_verification,
                "tree_of_thoughts": tree_of_thoughts,
            }
        else:
            self.techniques = techniques

    def analyze_all_techniques(self, process_description, extracted_steps):
        """
        Yields (technique_name, result_dict) for each technique.
        """
        for tech_name, tech_func in self.techniques.items():
            try:
                result = tech_func(process_description, extracted_steps)
                yield tech_name, result
            except Exception as e:
                print(f"        ERROR running {tech_name}: {e}")
                yield tech_name, None

    def analyze_one(self, process_description, extracted_steps, technique="zero_shot"):
        """
        Run a single technique and return its result.
        """
        if technique not in self.techniques:
            raise ValueError(f"Technique '{technique}' not found.")
        return self.techniques[technique](process_description, extracted_steps)
