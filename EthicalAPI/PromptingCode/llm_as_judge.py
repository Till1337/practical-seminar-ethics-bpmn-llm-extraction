import os
import json
import csv
import logging
from collections import defaultdict
from ollama_api import call_llm

# Configure logging
logging.basicConfig(level=logging.INFO)

def format_steps(steps):
    """Formats a list of steps for inclusion in the prompt."""
    if isinstance(steps, list):
        return "\n".join(f"- Step: {step['name'] if isinstance(step, dict) and 'name' in step else str(step)}" for step in steps)
    return str(steps)

def evaluate_ethics_analysis(process_description, process_steps, results, model="gemini-2.5-flash"):
    """
    Evaluates the quality of ethical analysis using an LLM as judge.
    Returns a dict with evaluation results.
    """
    prompt = f"""
# Evaluation of Ethical Analysis

You are an expert evaluator assessing the quality of ethical analysis on business processes.

## Original Process Description
```
{process_description}
```
## Original Process Steps
```
{format_steps(process_steps)}
```

## Extracted Ethical Analysis JSON Output
```
{json.dumps(results, indent=2) if isinstance(results, dict) else str(results)}
```

## Evaluation Task

Evaluate the ethical analysis using these criteria (score 1-5):

1. **Comprehensiveness**: Were all potential ethical concerns identified?
2. **Accuracy**: Are the identified concerns actually relevant to the process?
3. **Specificity**: Are the concerns specific and detailed rather than generic?
4. **Relevance**: How relevant are the concerns to important ethical dimensions?
5. **Actionability**: Can the identified concerns guide practical improvements?

For each process step:
- Identify any missed ethical concerns (false negatives)
- Identify any incorrectly flagged concerns (false positives)
- Suggest improvements to make the analysis better

## Output Format

Provide your evaluation as a valid JSON object.

```json
{{
    "overall_scores": {{
        "comprehensiveness": X,
        "accuracy": X, 
        "specificity": X,
        "relevance": X,
        "actionability": X
    }},
    "step_evaluations": [
        {{
            "step_name": "Step name",
            "score": X.X,
            "strengths": ["Strength 1", "Strength 2"],
            "weaknesses": ["Weakness 1", "Weakness 2"],
            "missed_concerns": ["Missed ethical issue 1", "Missed ethical issue 2"],
            "invalid_concerns": ["Invalid concern 1", "Invalid concern 2"]
        }}
    ],
    "overall_feedback": "Overall assessment of the ethical analysis quality",
    "improvement_suggestions": ["Suggestion 1", "Suggestion 2"]
}}
```

Be fair, thorough, and constructive in your evaluation.
"""
    
    response_str = call_llm(prompt, model=model, use_json_format=True)
    try:
        
        evaluation_results = json.loads(response_str)
    except json.JSONDecodeError:
        evaluation_results = {
            "error": "Failed to parse evaluation results from API",
            "raw_response": response_str
        }
    return evaluation_results

def extract_all_from_csv(csv_path):
    """
    Extracts all process_name/file_name pairs, their steps, and grouped results from the CSV.
    Returns:
        {
            (process_name, file_name): {
                "steps": [ {"name": ...}, ... ],
                "methods": {
                    method_name: {
                        "results": {step: {value: {...}, ...}, ...}
                    }
                }
            }
        }
    """
    data = {}
    with open(csv_path, newline='', encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            key = (row["process_name"], row["file_name"])
            method = row["prompting_technique"]
            step = row["step_name"]
            value = row["ethical_value"]
            if key not in data:
                data[key] = {"steps": [], "methods": defaultdict(dict)}
            # Steps (unique, ordered)
            if step and {"name": step} not in data[key]["steps"]:
                data[key]["steps"].append({"name": step})
            # Results
            if step and value:
                if step not in data[key]["methods"][method]:
                    data[key]["methods"][method][step] = {}
                data[key]["methods"][method][step][value] = {
                    "score": int(row["score"]) if row["score"] else None,
                    "explanation": row["explanation"],
                    "quotes": [q.strip() for q in row["quotes"].split(";") if q.strip()] if row["quotes"] else [],
                }
    return data

def run_judge_for_analysis(process_name, file_name, process_description, all_ethics_results):
    """
    Main function to be called from the API to run the judge evaluation.
    
    Args:
        process_name (str): The name of the process.
        file_name (str): The file name of the process model.
        process_description (str): The textual description of the process.
        all_ethics_results (dict): A dictionary with analysis results, keyed by technique.

    Returns:
        list: A list of dictionaries, where each dict is a row for the judge CSV.
    """

    all_judge_results = []
    for tech, analysis_result in all_ethics_results.items():
        logging.info(f"Running judge evaluation for technique: {tech}")

        
        steps = analysis_result.get("steps", []) 

        # Call the LLM judge - it returns a single dictionary for the evaluation
        eval_result = evaluate_ethics_analysis(process_description, steps, analysis_result)
        
        # Check if the evaluation was successful and contains step evaluations
        if isinstance(eval_result, dict) and "step_evaluations" in eval_result and eval_result.get("step_evaluations"):
            overall_feedback = eval_result.get("overall_feedback", "")
            improvement_suggestions = "; ".join(eval_result.get("improvement_suggestions", []))

            # Create a row for each step evaluation
            for step_eval in eval_result["step_evaluations"]:
                if isinstance(step_eval, dict):
                    row = {
                        "process_name": process_name,
                        "file_name": file_name,
                        "method": tech,
                        "step_name": step_eval.get("step_name", "N/A"),
                        "score": step_eval.get("score", ""),
                        "strengths": "; ".join(step_eval.get("strengths", [])),
                        "weaknesses": "; ".join(step_eval.get("weaknesses", [])),
                        "missed_concerns": "; ".join(step_eval.get("missed_concerns", [])),
                        "invalid_concerns": "; ".join(step_eval.get("invalid_concerns", [])),
                        "overall_feedback": overall_feedback, # Duplicated for each step
                        "improvement_suggestions": improvement_suggestions # Duplicated for each step
                    }
                    all_judge_results.append(row)
        else: # Handle failed evaluation by creating a single error row
            error_message = eval_result.get("error", "Evaluation failed") if isinstance(eval_result, dict) else "Evaluation failed"
            raw_response = eval_result.get("raw_response", "") if isinstance(eval_result, dict) else ""
            row = {
                "process_name": process_name,
                "file_name": file_name,
                "method": tech,
                "step_name": "EVALUATION_ERROR",
                "score": "",
                "strengths": "",
                "weaknesses": f"Error: {error_message}. Raw Response: {raw_response[:500]}...",
                "missed_concerns": "",
                "invalid_concerns": "",
                "overall_feedback": "",
                "improvement_suggestions": ""
            }
            all_judge_results.append(row)
    
    return all_judge_results

def run_llm_judge(csv_input_path, output_csv_path):
    """
    Runs the LLM-as-judge evaluation on an ethics analysis CSV file.
    """
    logging.info(f"Starting LLM-as-judge evaluation...")
    logging.info(f"Reading analysis from: {csv_input_path}")
    logging.info(f"Writing evaluation to: {output_csv_path}")

    
    all_data = extract_all_from_csv(csv_input_path)

    
    fieldnames = [
        "process_name",
        "file_name",
        "method",
        "step_name",
        "score",
        "strengths",
        "weaknesses",
        "missed_concerns",
        "invalid_concerns",
        "overall_feedback",
        "improvement_suggestions"
    ]
    
    
    already_done = set()
    if os.path.exists(output_csv_path):
        try:
            with open(output_csv_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    # A non-empty 'score' indicates a successful run for a step.
                    if row.get("score"):
                        already_done.add((row["process_name"], row["file_name"], row["method"]))
        except (FileNotFoundError, StopIteration, KeyError):
            # Ignore errors if file is empty, not found, or has wrong columns.
            # We will overwrite or append correctly.
            pass 

    file_exists = os.path.exists(output_csv_path)
    with open(output_csv_path, "a", newline='', encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
        if not file_exists or os.stat(output_csv_path).st_size == 0:
            writer.writeheader()

        for (process_name, file_name), info in all_data.items():
            steps = info["steps"]
            for method, results in info["methods"].items():
                key = (process_name, file_name, method)
                if key in already_done:
                    logging.info(f"Skipping: {process_name}/{file_name} | Method: {method} (already evaluated)")
                    continue

                logging.info(f"\nProcessing: {process_name}/{file_name} | Method: {method}")
                process_description_text = f"Process description for {process_name} from file {file_name}"

                # Call the LLM judge
                eval_result = evaluate_ethics_analysis(
                    process_description=process_description_text,
                    process_steps=steps,
                    results=results,
                    model="gemini-2.5-flash"
                )

                # Process and write the result rows
                if isinstance(eval_result, dict) and "step_evaluations" in eval_result and eval_result.get("step_evaluations"):
                    overall_feedback = eval_result.get("overall_feedback", "")
                    improvement_suggestions = "; ".join(eval_result.get("improvement_suggestions", []))

                    for step_eval in eval_result["step_evaluations"]:
                        if isinstance(step_eval, dict):
                            row = {
                                "process_name": process_name,
                                "file_name": file_name,
                                "method": method,
                                "step_name": step_eval.get("step_name", "N/A"),
                                "score": step_eval.get("score", ""),
                                "strengths": "; ".join(step_eval.get("strengths", [])),
                                "weaknesses": "; ".join(step_eval.get("weaknesses", [])),
                                "missed_concerns": "; ".join(step_eval.get("missed_concerns", [])),
                                "invalid_concerns": "; ".join(step_eval.get("invalid_concerns", [])),
                                "overall_feedback": overall_feedback,
                                "improvement_suggestions": improvement_suggestions
                            }
                            writer.writerow(row)
                else: # Handle failed evaluation
                    error_message = eval_result.get("error", "Evaluation failed") if isinstance(eval_result, dict) else "Evaluation failed"
                    raw_response = eval_result.get("raw_response", "") if isinstance(eval_result, dict) else ""
                    row = {
                        "process_name": process_name,
                        "file_name": file_name,
                        "method": method,
                        "step_name": "EVALUATION_ERROR",
                        "weaknesses": f"Error: {error_message}. Raw Response: {raw_response[:500]}..."
                    }
                    writer.writerow(row)

                csvfile.flush() # Save progress immediately

    logging.info(f"LLM-as-judge evaluation saved to {output_csv_path}")