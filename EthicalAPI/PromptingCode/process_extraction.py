import re
import json
import xml.etree.ElementTree as ET
import os
from ollama import ChatResponse
from ollama_api import call_llm

def extract_process_name_and_file(file_path):
    """
    Extract process name and file name from a BPMN file path.
    
    Args:
        file_path (str): Path like 'accounts_receivable_process_172.gv' or 'accounts_receivable_process_172.bpmn'
    
    Returns:
        tuple: (process_name, file_name)
        Example: ('accounts_receivable_process', 'accounts_receivable_process_172.gv')
    """
    # Remove any directory path and get just the filename
    file_name = os.path.basename(file_path)
    
    # Split by underscore and find the last part that contains a number
    parts = file_name.split('_')
    
    if len(parts) < 2:
        # If we can't parse it properly, return the whole filename as both
        return file_name, file_name
    
    # Find the last part that contains a number (the version/ID)
    version_part = None
    for i in range(len(parts) - 1, -1, -1):
        if any(char.isdigit() for char in parts[i]):
            version_part = parts[i]
            break
    
    if version_part:
        # Reconstruct the process name (everything before the version part)
        process_name = '_'.join(parts[:i])
        return process_name, file_name
    else:
        # No version found, return the whole filename as both
        return file_name, file_name

def extract_steps_from_bpmn(file_path):
    # Parse BPMN XML
    tree = ET.parse(file_path)
    root = tree.getroot()
    ns = {'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL'}

    # Collect all task-like elements
    step_elements = []
    for tag in ['task', 'userTask', 'serviceTask', 'manualTask', 'scriptTask', 'businessRuleTask', 'sendTask', 'receiveTask', 'callActivity', 'subProcess']:
        step_elements.extend(root.findall(f".//bpmn:{tag}", ns))

    # Build a list of step names and (optionally) documentation
    steps = []
    for elem in step_elements:
        name = elem.attrib.get('name', '').strip()
        doc = ''
        doc_elem = elem.find('.//bpmn:documentation', ns)
        if doc_elem is not None:
            doc = doc_elem.text.strip() if doc_elem.text else ''
        
        if name:  # Only include steps with names
            steps.append({
                'name': name,
                'documentation': doc
            })

    return steps

def clean_extracted_steps(steps):
    """
    For each step, if the name contains a colon (e.g., "Step: Add to Pool" → "Add to Pool"), keep only the part after the colon (stripped of whitespace).
    Do not remove steps based on length or content—just clean the name as described.
    """
    cleaned_steps = []
    for step in steps:
        name = step.get('name', '')
        if ':' in name:
            # Keep only the part after the first colon
            new_name = name.split(':', 1)[1].strip()
            step['name'] = new_name
        cleaned_steps.append(step)
    return cleaned_steps
