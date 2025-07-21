from data.ethics_values import ETHICAL_VALUES

def format_steps(steps):
    return "\n".join(f"- Step: {step.get('name', step) if isinstance(step, dict) else step}" for step in steps)

def format_values():
    return "\n".join(f"- **{k}**: {v}" for k, v in ETHICAL_VALUES.items())

def flatten_ethics_results(ethics_results, process_name, file_name, prompting_technique):
    """
    Flattens the nested ethics results structure into a list of dicts for CSV writing.
    Each row will contain: process_name, file_name, prompting_technique, step_name, ethical_value, score, explanation, quotes
    """
    flattened_rows = []
    if not isinstance(ethics_results, dict):
        return []
    for step_name, values in ethics_results.items():
        if not isinstance(values, dict):
            continue
        for value_name, details in values.items():
            if not isinstance(details, dict):
                continue
            row = {
                'process_name': process_name,
                'file_name': file_name,
                'prompting_technique': prompting_technique,
                'step_name': step_name,
                'ethical_value': value_name,
                'score': details.get('score', 0),
                'explanation': details.get('explanation', ''),
                'quotes': '; '.join(details.get('quotes', [])) if isinstance(details.get('quotes', []), list) else str(details.get('quotes', ''))
            }
            flattened_rows.append(row)
    return flattened_rows
