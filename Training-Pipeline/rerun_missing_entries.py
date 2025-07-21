import os
import sys
import csv
import logging
import argparse
import traceback
from datetime import datetime
from collections import defaultdict

# Add the 'Training-Pipeline' directory to the Python path
pipeline_dir = os.path.dirname(os.path.abspath(__file__))
if pipeline_dir not in sys.path:
    sys.path.append(pipeline_dir)

from common.process_extraction import extract_process_description_from_gv, extract_process_steps
from common.utils import flatten_ethics_results
from analysis.ethics_analyzer import EthicsAnalyzer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

# Suppress HTTP info logs from common HTTP libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("http.client").setLevel(logging.WARNING)


class MissingEntriesProcessor:
    def __init__(self, dataset_path, output_csv_path):
        self.dataset_path = dataset_path
        self.output_csv_path = output_csv_path
        self.analyzer = EthicsAnalyzer()
        self.fieldnames = ['process_name', 'file_name', 'prompting_technique', 'step_name', 
                          'ethical_value', 'score', 'explanation', 'quotes']
        self.processed_files = 0
        self.skipped_files = 0
        self.failed_files = 0
    
    def load_completed_entries(self):
        """
        Loads all (process_name, file_name, prompting_technique) entries from the CSV.
        Returns a set of completed entries and a dictionary of all entries by process/file.
        """
        completed = set()
        entries_by_file = defaultdict(set)
        
        if os.path.exists(self.output_csv_path):
            with open(self.output_csv_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    process_name = row['process_name']
                    file_name = row['file_name']
                    technique = row['prompting_technique']
                    
                    completed.add((process_name, file_name, technique))
                    entries_by_file[(process_name, file_name)].add(technique)
        
        return completed, entries_by_file
    
    def get_available_files(self):
        """
        Returns a list of (process_folder, file_name, process_folder_path) tuples
        for all .gv files in the dataset.
        """
        file_info = []
        for process_folder in os.listdir(self.dataset_path):
            process_folder_path = os.path.join(self.dataset_path, process_folder)
            if os.path.isdir(process_folder_path):
                for file_name in os.listdir(process_folder_path):
                    file_path = os.path.join(process_folder_path, file_name)
                    if os.path.isfile(file_path) and file_name.endswith('.gv'):
                        file_info.append((process_folder, file_name, process_folder_path))
        return file_info
    
    def find_missing_entries(self, target_techniques=None):
        """
        Identifies missing entries in the CSV.
        If target_techniques is provided, only finds missing entries for those techniques.
        Returns a list of (process_folder, file_name, process_folder_path, missing_techniques) tuples.
        """
        completed, entries_by_file = self.load_completed_entries()
        file_info = self.get_available_files()
        missing_entries = []
        
        available_techniques = self.analyzer.techniques.keys()
        if target_techniques:
            available_techniques = [t for t in target_techniques if t in available_techniques]
        
        for process_folder, file_name, process_folder_path in file_info:
            file_key = (process_folder, file_name)
            completed_techniques = entries_by_file.get(file_key, set())
            missing_techniques = [t for t in available_techniques if t not in completed_techniques]
            
            if missing_techniques:
                missing_entries.append((process_folder, file_name, process_folder_path, missing_techniques))
        
        return missing_entries
    
    def process_file_with_specific_techniques(self, process_folder, file_name, process_folder_path, techniques):
        """
        Processes a specific file with only the specified techniques.
        Returns a list of flattened results.
        """
        file_path = os.path.join(process_folder_path, file_name)
        process_description = extract_process_description_from_gv(file_path)
        if not process_description:
            logging.warning(f"No process description extracted from {file_path}")
            return []
        
        logging.info(f"Extracted process description ({len(process_description)} chars) from {file_name}")
        extracted_steps = extract_process_steps(process_description, source_id=file_name)
        if not extracted_steps:
            logging.warning(f"No steps extracted from {file_name}")
            return []
        
        logging.info(f"Extracted {len(extracted_steps)} steps from {file_name}")
        results = []
        
        # Filter techniques to only the ones we need to run
        filtered_techniques = {name: func for name, func in self.analyzer.techniques.items() if name in techniques}
        
        for tech_name, tech_func in filtered_techniques.items():
            logging.info(f"  Running technique: {tech_name}")
            try:
                ethics_results = tech_func(process_description, extracted_steps)
                if ethics_results:
                    flattened_results = flatten_ethics_results(
                        ethics_results,
                        process_folder,
                        file_name,
                        tech_name
                    )
                    if flattened_results:
                        logging.info(f"    Technique {tech_name} produced {len(flattened_results)} results")
                        results.extend(flattened_results)
                    else:
                        logging.warning(f"    Technique {tech_name} produced no results")
                else:
                    logging.warning(f"    Technique {tech_name} failed or returned no results")
            except Exception as e:
                logging.error(f"Error running technique {tech_name}: {e}")
                logging.error(traceback.format_exc())
        
        return results
    
    def rerun_missing_entries(self, target_techniques=None):
        """
        Reruns only the missing entries for the specified techniques.
        If target_techniques is None, reruns all missing entries.
        """
        missing_entries = self.find_missing_entries(target_techniques)
        if not missing_entries:
            logging.info("No missing entries found.")
            return
        
        logging.info(f"Found {len(missing_entries)} files with missing entries.")
        
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(self.output_csv_path), exist_ok=True)
        
        # Open CSV in append mode
        file_exists = os.path.exists(self.output_csv_path)
        write_header = not file_exists or os.path.getsize(self.output_csv_path) == 0
        
        with open(self.output_csv_path, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.fieldnames)
            if write_header:
                writer.writeheader()
            
            for process_folder, file_name, process_folder_path, missing_techniques in missing_entries:
                logging.info(f"Processing: {process_folder}/{file_name} | Missing techniques: {', '.join(missing_techniques)}")
                
                max_retries = 5
                for attempt in range(1, max_retries + 1):
                    try:
                        flattened_results = self.process_file_with_specific_techniques(
                            process_folder, file_name, process_folder_path, missing_techniques
                        )
                        
                        if flattened_results:
                            for row in flattened_results:
                                logging.info(f"    Technique: {row['prompting_technique']} | Step: {row['step_name']}")
                            writer.writerows(flattened_results)
                            csvfile.flush()
                            self.processed_files += 1
                        else:
                            self.skipped_files += 1
                        
                        break  # Success, exit retry loop
                    except Exception as e:
                        self.failed_files += 1
                        logging.error(f"Error processing {process_folder}/{file_name} (attempt {attempt}/{max_retries}): {e}")
                        logging.error(traceback.format_exc())
                        if attempt == max_retries:
                            logging.error(f"Failed to process {process_folder}/{file_name} after {max_retries} attempts. Skipping.")
                        else:
                            logging.info(f"Retrying {process_folder}/{file_name}...")
        
        logging.info(f"Processing complete! Results saved to: {self.output_csv_path}")
        logging.info(f"Summary: {self.processed_files} files processed, {self.skipped_files} skipped, {self.failed_files} failed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Rerun missing entries in the ethics analysis CSV.')
    parser.add_argument('--techniques', nargs='+', 
                        choices=['zero_shot', 'few_shot', 'contrastive_cot', 'universal_self_consistency', 
                                'chain_of_verification', 'tree_of_thoughts'],
                        help='Specify techniques to rerun (e.g., --techniques tree_of_thoughts chain_of_verification)')
    args = parser.parse_args()
    
    results_dir = os.path.join(os.path.dirname(__file__), 'results')
    os.makedirs(results_dir, exist_ok=True)
    
    combined_dataset_path = os.path.join(os.path.dirname(__file__), 'combined_dataset')
    output_csv_path = os.path.join(results_dir, 'ethics_analysis.csv')
    
    logging.info(f"Starting rerun of missing entries...")
    if args.techniques:
        logging.info(f"Target techniques: {', '.join(args.techniques)}")
    
    processor = MissingEntriesProcessor(combined_dataset_path, output_csv_path)
    processor.rerun_missing_entries(args.techniques)
