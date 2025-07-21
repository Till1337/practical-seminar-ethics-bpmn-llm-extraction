import os
import json
import csv
from collections import defaultdict
from common.llm_api import call_llm  


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
    # Use the imported call_llm function
    response_str = call_llm(prompt, model=model, use_json_format=True)
    try:
        # The call_llm function returns a JSON string, so we parse it here.
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

if __name__ == "__main__":
    # --- CONFIG ---
    results_dir = os.path.join(os.path.dirname(__file__), 'results')
    os.makedirs(results_dir, exist_ok=True)

    # Use the correct input file name
    csv_input_path = os.path.join(results_dir, 'ethics_analysis.csv')
    output_csv_path = os.path.join(results_dir, 'llm_judge_evaluation.csv')

    # --- EXTRACT EVERYTHING FROM CSV ---
    all_data = extract_all_from_csv(csv_input_path)

    # --- PREPARE OUTPUT ---
    fieldnames = [
        "process_name",
        "file_name",
        "method",
        "comprehensiveness",
        "accuracy",
        "specificity",
        "relevance",
        "actionability",
        "overall_feedback"
    ]
    # Check which (process_name, file_name, method) are already in the output CSV
    already_done = set()
    if os.path.exists(output_csv_path):
        with open(output_csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                already_done.add((row["process_name"], row["file_name"], row["method"]))

    with open(output_csv_path, "a", newline='', encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        # Only write header if file is empty
        if os.stat(output_csv_path).st_size == 0:
            writer.writeheader()

        for (process_name, file_name), info in all_data.items():
            steps = info["steps"]
            for method, results in info["methods"].items():
                key = (process_name, file_name, method)
                if key in already_done:
                    continue
                print(f"\nProcessing: {process_name}/{file_name} | Method: {method}")
                process_description_text = f"Process description for {process_name}/{file_name}"  # Placeholder
                # Updated call to evaluate_ethics_analysis
                result = evaluate_ethics_analysis(
                    process_description=process_description_text,
                    process_steps=steps,
                    results=results,
                    model="gemini-2.5-flash"  # Specify the model to be used by call_llm
                )
                if "overall_scores" in result:
                    row = {
                        "process_name": process_name,
                        "file_name": file_name,
                        "method": method,
                        "comprehensiveness": result["overall_scores"].get("comprehensiveness", ""),
                        "accuracy": result["overall_scores"].get("accuracy", ""),
                        "specificity": result["overall_scores"].get("specificity", ""),
                        "relevance": result["overall_scores"].get("relevance", ""),
                        "actionability": result["overall_scores"].get("actionability", ""),
                        "overall_feedback": result.get("overall_feedback", ""),
                    }
                else:
                    row = {
                        "process_name": process_name,
                        "file_name": file_name,
                        "method": method,
                        "comprehensiveness": "",
                        "accuracy": "",
                        "specificity": "",
                        "relevance": "",
                        "actionability": "",
                        "overall_feedback": result.get("error", result.get("raw_response", ""))
                    }
                writer.writerow(row)
                csvfile.flush()

    print(f"LLM-as-judge evaluation saved to {output_csv_path}")