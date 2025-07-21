import logging
from PromptingCode.prompting_techniques import (
    zero_shot,
    few_shot,
    contrastive_cot,
    universal_self_consistency,
    chain_of_verification,
    tree_of_thoughts,
)
from PromptingCode.utils import flatten_ethics_results

# Main Class to analyze 
class EthicsAnalyzer:
    
    def __init__(self):
        """Initialize the EthicsAnalyzer with available prompting techniques."""
        self.techniques = {
            "zero_shot": zero_shot,
            "few_shot": few_shot,
            "contrastive_cot": contrastive_cot,
            "universal_self_consistency": universal_self_consistency,
            "chain_of_verification": chain_of_verification,
            "tree_of_thoughts": tree_of_thoughts,
        }

    def analyze_one(self, process_description: str, extracted_steps: list, technique: str = "zero_shot") -> dict:
        """
        Run a single prompting technique and return its analysis results.
        
        Args:
            process_description (str): Description of the business process to analyze
            extracted_steps (list): List of process steps extracted from BPMN
            technique (str): Name of the prompting technique to use
            
        Returns:
            dict: Analysis results for the specified technique
            
        Raises:
            ValueError: If the specified technique is not available
        """
        prompt_func = self.techniques.get(technique)
        if not prompt_func:
            available_techniques = list(self.techniques.keys())
            raise ValueError(f"Unknown technique: {technique}. Available: {available_techniques}")

        result = prompt_func(process_description, extracted_steps)
        return result

    def analyze_all(self, process_description: str, extracted_steps: list) -> dict:
        """
        Run analysis using all available prompting techniques.
        
        This method executes all prompting techniques in sequence and returns
        a comprehensive analysis covering multiple perspectives on ethical concerns.
        
        Args:
            process_description (str): Description of the business process to analyze
            extracted_steps (list): List of process steps extracted from BPMN
            
        Returns:
            dict: Analysis results from all techniques, keyed by technique name
        """
        all_results = {}
        for tech_name, prompt_func in self.techniques.items():
            try:
                logging.info(f"Running analysis with technique: {tech_name}")
                result = prompt_func(process_description, extracted_steps)
                if result:
                    all_results[tech_name] = result
                else:
                    logging.warning(f"Technique {tech_name} returned no results.")
            except Exception as e:
                logging.error(f"Failed to run analysis with technique {tech_name}: {e}", exc_info=True)
        return all_results

    def analyze_all_techniques(self, process_description: str, extracted_steps: list):
        """
        Generator that yields results from all techniques one at a time.
        
        This method is useful for streaming results or implementing parallel processing
        where you want to handle results as they become available.
        
        Args:
            process_description (str): Description of the business process to analyze
            extracted_steps (list): List of process steps extracted from BPMN
            
        Yields:
            tuple: (technique_name, result) for each technique
        """
        for tech_name, prompt_func in self.techniques.items():
            try:
                result = prompt_func(process_description, extracted_steps)
                yield tech_name, result
            except Exception as e:
                logging.error(f"Failed to run analysis with technique {tech_name}: {e}", exc_info=True)
                yield tech_name, None
