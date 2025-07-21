import re
import json
from common.llm_api import call_llm

def extract_process_description_from_gv(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        label_match = re.search(r'label="\s*\\n\\n\s*(.*?)\s*"', content, re.DOTALL)
        if label_match:
            description = label_match.group(1).strip()
            description = description.replace('\\n', ' ').replace('\\"', '"').strip()
            return description
        return None
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None

def extract_process_steps(text, source_id="unnamed_source"):
    if not text:
        return []
    extraction_prompt = f"""
    Extract the business process steps from the following text. 
    Return ONLY a JSON array of steps in sequential order.
    Each step should include:
    - "name": concise step name
    - "description": detailed description
    - "actors": responsible entities (if mentioned)
    - "input": required inputs (if mentioned)
    - "output": produced outputs (if mentioned)
    If no clear process steps are present, return an empty array.
    TEXT TO ANALYZE:
    {text}
    RESPOND WITH VALID JSON ONLY, NO EXPLANATIONS OR MARKDOWN
    """
    try:
        response = call_llm(extraction_prompt, use_json_format=True)
        result = response
        if "```json" in result:
            result = result.split("```json")[1].split("```")[0].strip()
        elif "```" in result:
            result = result.split("```")[1].split("```")[0].strip()
        extracted_steps = json.loads(result)
        return extracted_steps
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON from LLM response: {e}")
        return []
    except Exception as e:
        print(f"Error during extraction: {e}")
        return []
