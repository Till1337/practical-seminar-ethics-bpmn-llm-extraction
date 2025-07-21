import os
import csv
import logging
import concurrent.futures
import traceback
from datetime import datetime
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


def load_completed_set(csv_path):
    """
    Loads the set of (process_name, file_name, prompting_technique) already processed.
    """
    completed = set()
    if os.path.exists(csv_path):
        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                completed.add((row['process_name'], row['file_name'], row['prompting_technique']))
    return completed

def process_file(args):
    process_folder, file_name, process_folder_path, completed, analyzer = args
    file_path = os.path.join(process_folder_path, file_name)
    if not (os.path.isfile(file_path) and file_name.endswith('.gv')):
        logging.info(f"Skipping non-.gv file: {file_path}")
        return []
    if (process_folder, file_name) in [(c[0], c[1]) for c in completed]:
        logging.info(f"Skipping already completed file: {process_folder}/{file_name}")
        return []
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
    for tech_name, ethics_results in analyzer.analyze_all_techniques(process_description, extracted_steps):
        logging.info(f"  Running technique: {tech_name}")
        if (process_folder, file_name, tech_name) in completed:
            logging.info(f"    Skipping technique {tech_name} (already completed)")
            continue
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
    return results

def iterate_combined_dataset(dataset_path, output_csv_path):
    if not os.path.isdir(dataset_path):
        logging.error(f"Dataset directory does not exist: {dataset_path}")
        return

    processed_files = 0
    skipped_files = 0
    failed_files = 0
    analyzer = EthicsAnalyzer()

    fieldnames = ['process_name', 'file_name', 'prompting_technique', 'step_name', 'ethical_value', 'score', 'explanation', 'quotes']

    # Load already completed (process_name, file_name, prompting_technique)
    completed = load_completed_set(output_csv_path)

    # Always open in append mode, but only write header if file is empty
    file_exists = os.path.exists(output_csv_path)
    write_header = not file_exists or os.path.getsize(output_csv_path) == 0

    file_args = []
    for process_folder in os.listdir(dataset_path):
        process_folder_path = os.path.join(dataset_path, process_folder)
        if os.path.isdir(process_folder_path):
            for file_name in os.listdir(process_folder_path):
                file_args.append((process_folder, file_name, process_folder_path, completed, analyzer))

    with open(output_csv_path, 'a', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            for args in file_args:
                process_folder, file_name, process_folder_path, completed, analyzer = args
                logging.info(f"Processing: {process_folder}/{file_name}")
                max_retries = 3
                for attempt in range(1, max_retries + 1):
                    try:
                        flattened_results = process_file(args)
                        if flattened_results:
                            for row in flattened_results:
                                logging.info(f"    Technique: {row['prompting_technique']} | Step: {row['step_name']}")
                            writer.writerows(flattened_results)
                            csvfile.flush()
                            processed_files += 1
                        else:
                            skipped_files += 1
                        break  
                    except Exception as e:
                        failed_files += 1
                        logging.error(f"Error processing {process_folder}/{file_name} (attempt {attempt}/{max_retries}): {e}")
                        logging.error(traceback.format_exc())
                        if attempt == max_retries:
                            logging.error(f"Failed to process {process_folder}/{file_name} after {max_retries} attempts. Skipping.")
                        else:
                            logging.info(f"Retrying {process_folder}/{file_name}...")

    logging.info(f"Processing complete! Results saved to: {output_csv_path}")
    logging.info(f"Summary: {processed_files} files processed, {skipped_files} skipped, {failed_files} failed.")

if __name__ == "__main__":
    results_dir = os.path.join(os.path.dirname(__file__), 'results')
    os.makedirs(results_dir, exist_ok=True)

    combined_dataset_path = os.path.join(os.path.dirname(__file__), 'combined_dataset')
    output_csv_path = os.path.join(results_dir, 'ethics_analysis.csv')
    logging.info(f"Starting ethics analysis training pipeline...")
    iterate_combined_dataset(combined_dataset_path, output_csv_path)