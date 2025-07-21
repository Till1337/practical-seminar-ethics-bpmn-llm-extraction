import json
from common.utils import format_steps, format_values
from common.llm_api import call_llm
import re

def zero_shot(process_description, extracted_steps):
    steps_text = format_steps(extracted_steps)
    values_text = format_values()
    prompt = f"""
    You are an ethics analyst. Analyze the given process description and its individual steps. Identify which ethical values from the provided list are potentially at risk or relevant for EACH process step.
This is very important to the company.
Now, analyze this:
LIST OF ETHICAL VALUES:
{values_text}
PROCESS DESCRIPTION:
{process_description}
PROCESS STEPS:
{steps_text}
INSTRUCTIONS:
1.  Go through EACH process step listed above.
2.  For each step, determine which ethical values are most relevant or at risk.
3.  Focus ONLY on clear, substantive ethical concerns. Do NOT invent issues.
4.  For each relevant value within a step, provide: `score` (1–10), `explanation`, and `quotes`.
5.  IMPORTANT: Always assign a score between 1-10. NEVER use 0.
6.  If a step has NO relevant values, omit it. If a value isn't relevant, omit it.
7.  Return ONLY valid JSON with this exact structure:
{{
  "Step Name 1": {{
    "value_name_A": {{ "score": int, "explanation": str, "quotes": [str, ...] }},
    "value_name_B": {{ ... }}
  }},
  "Step Name 2": {{ "value_name_C": {{ ... }} }},
  // ... other steps
}}
OUTPUT:
"""
    content = call_llm(prompt, use_json_format=True)
    return json.loads(content)

# Few Shot 

def few_shot(process_description, extracted_steps):
    """Few-Shot Prompting: Includes examples with step-mapping."""
    steps_text = format_steps(extracted_steps)
    example_process = "The system collects user feedback via a form, analyzes it using AI, and then an agent contacts the user if needed."
    example_steps = ["Collect Feedback", "Analyze with AI", "Contact User"]
    example_output = {
      "Collect Feedback": {
        "privacy": {"score": 7, "explanation": "Collecting feedback might involve personal data.", "quotes": ["collects user feedback via a form"]},
        "human_autonomy": {"score": 6, "explanation": "Users should consent to how their feedback is used.", "quotes": ["collects user feedback"]}
      },
      "Analyze with AI": {
        "transparency": {"score": 8, "explanation": "The AI analysis process should be understandable.", "quotes": ["analyzes it using AI"]},
        "fairness": {"score": 7, "explanation": "AI analysis must avoid biases.", "quotes": ["analyzes it using AI"]}
      }
    }
    values_text = format_values()
    prompt = f"""
    You are an ethics analyst. Analyze the given process description and its individual steps. Identify which ethical values from the provided list are potentially at risk or relevant for EACH process step.


Below is an example.

--- EXAMPLE START ---
PROCESS DESCRIPTION: {example_process}
PROCESS STEPS:
- Step: {example_steps[0]}
- Step: {example_steps[1]}
- Step: {example_steps[2]}
OUTPUT:
{json.dumps(example_output, indent=2)}
--- EXAMPLE END --- 

Now, analyze this:

LIST OF ETHICAL VALUES:
{values_text}

PROCESS DESCRIPTION:
{process_description}

PROCESS STEPS:
{steps_text}

INSTRUCTIONS:
1.  Go through EACH process step listed above.
2.  For each step, determine which ethical values are most relevant or at risk.
3.  The keys in your output JSON must be the exact names of the process steps.
4.  Focus ONLY on clear, substantive ethical concerns. Do NOT invent issues.
5.  For each relevant value within a step, provide: `score` (1–10), `explanation`, and `quotes`.
6.  IMPORTANT: Always assign a score between 1-10. NEVER use 0.
7.  If a step has NO relevant values, omit it. If a value isn't relevant, omit it.
8.  Return ONLY valid JSON with this exact structure:
{{
  "Step Name 1": {{
    "value_name_A": {{ "score": int, "explanation": str, "quotes": [str, ...] }},
    "value_name_B": {{ ... }}
  }},
  "Step Name 2": {{ "value_name_C": {{ ... }} }},
  // ... other steps
}}

OUTPUT:
""" # We expect only JSON here
    content = call_llm(prompt, use_json_format=True)
    return json.loads(content)

# Chain-of-Thought

def contrastive_cot(process_description, extracted_steps):
    """Contrastive Chain-of-Thought Prompting: Includes positive and negative examples for reasoning."""
    steps_text = format_steps(extracted_steps)
    example_process = "The system collects user feedback via a form, analyzes it using AI, and then an agent contacts the user if needed."
    example_steps = ["Collect Feedback", "Analyze with AI", "Contact User"]
    
    # Positive example
    positive_example_output = {
      "Collect Feedback": {
        "privacy": {"score": 7, "explanation": "Collecting feedback might involve personal data.", "quotes": ["collects user feedback via a form"]},
        "human_autonomy": {"score": 6, "explanation": "Users should consent to how their feedback is used.", "quotes": ["collects user feedback"]}
      },
      "Analyze with AI": {
        "transparency": {"score": 8, "explanation": "The AI analysis process should be understandable.", "quotes": ["analyzes it using AI"]},
        "fairness": {"score": 7, "explanation": "AI analysis must avoid biases.", "quotes": ["analyzes it using AI"]}
      }
    }
    
    # Negative example (incorrect reasoning)
    negative_example_output = {
      "Collect Feedback": {
        "privacy": {"score": 3, "explanation": "Feedback collection does not involve personal data.", "quotes": ["collects user feedback via a form"]},
        "human_autonomy": {"score": 2, "explanation": "Users do not need to consent to feedback usage.", "quotes": ["collects user feedback"]}
      },
      "Analyze with AI": {
        "transparency": {"score": 4, "explanation": "AI analysis does not need to be understandable.", "quotes": ["analyzes it using AI"]},
        "fairness": {"score": 3, "explanation": "Biases in AI analysis are not a concern.", "quotes": ["analyzes it using AI"]}
      }
    }
    
    values_text = format_values()
    prompt = f"""
    You are an ethics analyst. Analyze the given process description and its individual steps. Identify which ethical values from the provided list are potentially at risk or relevant for EACH process step.

Below are examples of correct and incorrect reasoning.

--- POSITIVE EXAMPLE START ---
PROCESS DESCRIPTION: {example_process}
PROCESS STEPS:
- Step: {example_steps[0]}
- Step: {example_steps[1]}
- Step: {example_steps[2]}
OUTPUT:
{json.dumps(positive_example_output, indent=2)}
--- POSITIVE EXAMPLE END ---

--- NEGATIVE EXAMPLE START ---
PROCESS DESCRIPTION: {example_process}
PROCESS STEPS:
- Step: {example_steps[0]}
- Step: {example_steps[1]}
- Step: {example_steps[2]}
OUTPUT:
{json.dumps(negative_example_output, indent=2)}
--- NEGATIVE EXAMPLE END ---

Now, analyze this:

LIST OF ETHICAL VALUES:
{values_text}

PROCESS DESCRIPTION:
{process_description}

PROCESS STEPS:
{steps_text}

INSTRUCTIONS:
1.  Go through EACH process step listed above.
2.  For each step, determine which ethical values are most relevant or at risk.
3.  The keys in your output JSON must be the exact names of the process steps.
4.  Focus ONLY on clear, substantive ethical concerns. Do NOT invent issues.
5.  For each relevant value within a step, provide: `score` (1–10), `explanation`, and `quotes`.
6.  IMPORTANT: Always assign a score between 1-10. NEVER use 0.
7.  If a step has NO relevant values, omit it. If a value isn't relevant, omit it.
8.  Return ONLY valid JSON with this exact structure:
{{
  "Step Name 1": {{
    "value_name_A": {{ "score": int, "explanation": str, "quotes": [str, ...] }},
    "value_name_B": {{ ... }}
  }},
  "Step Name 2": {{ "value_name_C": {{ ... }} }},
  // ... other steps
}}

OUTPUT:
""" # We expect only JSON here
    content = call_llm(prompt, use_json_format=True)
    return json.loads(content)

def universal_self_consistency(process_description, extracted_steps):
    """Universal Self-Consistency: Generate multiple responses and select the most consistent one."""
    steps_text = format_steps(extracted_steps)
    values_text = format_values()

    # Step 1: Generate multiple responses
    prompt = f"""
    You are an ethics analyst. Analyze the given process description and its individual steps. Identify which ethical values from the provided list are potentially at risk or relevant for EACH process step.

LIST OF ETHICAL VALUES:
{values_text}

PROCESS DESCRIPTION:
{process_description}

PROCESS STEPS:
{steps_text}

INSTRUCTIONS:
1.  Go through EACH process step listed above.
2.  For each step, determine which ethical values are most relevant or at risk.
3.  Focus ONLY on clear, substantive ethical concerns. Do NOT invent issues.
4.  For each relevant value within a step, provide: `score` (1–10), `explanation`, and `quotes`.
5.  IMPORTANT: Always assign a score between 1-10. NEVER use 0.
6.  If a step has NO relevant values, omit it. If a value isn't relevant, omit it.
7.  Return ONLY valid JSON with this exact structure:
{{
  "Step Name 1": {{
    "value_name_A": {{ "score": int, "explanation": str, "quotes": [str, ...] }},
    "value_name_B": {{ ... }}
  }},
  "Step Name 2": {{ "value_name_C": {{ ... }} }},
  // ... other steps
}}

OUTPUT:
""" # We expect only JSON here

    # Generate multiple responses
    responses = [call_llm(prompt, use_json_format=True) for _ in range(5)]

    # Step 2: Compile responses into a new prompt for consistency evaluation
    evaluation_prompt = f"""
    I have generated the following responses to the task:

    Response 1: {responses[0]}
    Response 2: {responses[1]}
    Response 3: {responses[2]}
    Response 4: {responses[3]}
    Response 5: {responses[4]}

    Evaluate these responses. Select the most consistent response based on majority consensus. 
    Start your answer with "The most consistent response is Response X" (without quotes).
    """
    consistent_response = call_llm(evaluation_prompt, use_json_format=False)
    

    # Extract the selected response
    try:
        match = re.search(r"Response (\d+)", consistent_response)
        if not match:
            raise ValueError("Could not find a valid candidate number in the evaluation response.")
        selected_response_index = int(match.group(1)) - 1
        return json.loads(responses[selected_response_index])
    except (IndexError, ValueError, json.JSONDecodeError) as e:
        print(f"Error parsing response: {e}")
        #print("Consistent response:", consistent_response)
        return None
    

# Self Criticism

def chain_of_verification(process_description, extracted_steps):
    """Chain-of-Verification (CoVe): Refine responses by planning and verifying key questions."""
    steps_text = format_steps(extracted_steps)
    values_text = format_values()

    # Step 1: Baseline response generation
    baseline_prompt = f"""
    You are an ethics analyst. Analyze the given process description and its individual steps. Identify which ethical values from the provided list are potentially at risk or relevant for EACH process step.

LIST OF ETHICAL VALUES:
{values_text}

PROCESS DESCRIPTION:
{process_description}

PROCESS STEPS:
{steps_text}

INSTRUCTIONS:
1.  Go through EACH process step listed above.
2.  For each step, determine which ethical values are most relevant or at risk.
3.  Focus ONLY on clear, substantive ethical concerns. Do NOT invent issues.
4.  For each relevant value within a step, provide: `score` (1–10), `explanation`, and `quotes`.
5.  IMPORTANT: Always assign a score between 1-10. NEVER use 0.
6.  If a step has NO relevant values, omit it. If a value isn't relevant, omit it.
7.  Return ONLY valid JSON with this exact structure:
{{
  "Step Name 1": {{
    "value_name_A": {{ "score": int, "explanation": str, "quotes": [str, ...] }},
    "value_name_B": {{ ... }}
  }},
  "Step Name 2": {{ "value_name_C": {{ ... }} }},
  // ... other steps
}}

OUTPUT:
""" # We expect only JSON here
    baseline_response = call_llm(baseline_prompt, use_json_format=True)

    # Step 2: Planning verification questions
    verification_plan_prompt = f"""
    Based on the following baseline response, generate a list of verification questions to ensure the accuracy and consistency of the analysis:

BASELINE RESPONSE:
{json.dumps(baseline_response, indent=2)}

INSTRUCTIONS:
1. For each process step, identify potential areas of uncertainty or ambiguity in the baseline response.
2. Generate specific verification questions to address these areas.
3. Return the questions as a numbered list.
"""
    verification_questions = call_llm(verification_plan_prompt, use_json_format=False)

    # Step 3: Verification execution
    verification_execution_prompt = f"""
    Answer the following verification questions to refine the baseline response:

VERIFICATION QUESTIONS:
{verification_questions}

INSTRUCTIONS:
1. Provide clear and concise answers to each question.
2. Ensure the answers are factually accurate and address the questions directly.
3. Return the answers as a numbered list corresponding to the questions.
"""
    verification_answers = call_llm(verification_execution_prompt, use_json_format=False)

    # Step 4: Final response generation
    final_response_prompt = f"""
    Refine the baseline response using the answers to the verification questions:

BASELINE RESPONSE:
{json.dumps(baseline_response, indent=2)}

VERIFICATION ANSWERS:
{verification_answers}

LIST OF ETHICAL VALUES:
{values_text}

INSTRUCTIONS:
1. Incorporate the verification answers into the baseline response.
2. Ensure the final response is accurate, consistent, and adheres to the required JSON format.
3. Return ONLY valid JSON with this exact structure:
{{
  "Step Name 1": {{
    "value_name_A": {{ "score": int, "explanation": str, "quotes": [str, ...] }},
    "value_name_B": {{ ... }}
  }},
  "Step Name 2": {{ "value_name_C": {{ ... }} }},
  // ... other steps
}}
4. Make sure that each value is present in the list of ethical values. Else map it to one of the values and remove all values not present in the ethical values list.
"""
    final_response = call_llm(final_response_prompt, use_json_format=True)
    final_response = json.loads(final_response)
    return final_response



def tree_of_thoughts(process_description, extracted_steps):
    """Tree of Thoughts (ToT): Explore multiple reasoning paths and evaluate the best solution."""
    steps_text = format_steps(extracted_steps)
    values_text = format_values()

    # Step 1: Generate initial candidate solutions (propose step)
    propose_prompt = f"""
    You are an ethics analyst. Analyze the given process description and its individual steps. Identify which ethical values from the provided list are potentially at risk or relevant for EACH process step.

LIST OF ETHICAL VALUES:
{values_text}

PROCESS DESCRIPTION:
{process_description}

PROCESS STEPS:
{steps_text}

1.  Go through EACH process step listed above.
2.  For each step, determine which ethical values are most relevant or at risk.
3.  Focus ONLY on clear, substantive ethical concerns. Do NOT invent issues.
4.  For each relevant value within a step, provide: `score` (1–10), `explanation`, and `quotes`.
5.  IMPORTANT: Always assign a score between 1-10. NEVER use 0.
6.  If a step has NO relevant values, omit it. If a value isn't relevant, omit it.
7.  Return ONLY valid JSON with this exact structure:


INSTRUCTIONS:
1. Generate exactly 3 distinct candidate analyses plans on how you would tackle this problem. 
2. Each candidate should explore a different reasoning path or perspective.
4. Return the candidates as a numbered list.
5. Structure your response clearly, starting each candidate with "Candidate X:" on a new line.
"""
    candidate_solutions = call_llm(propose_prompt, use_json_format=False)

    # Step 2: Evaluate candidate solutions (value step)
    value_prompt = f"""
    Evaluate the following candidate solutions for their accuracy, consistency, and adherence to identifiy the ethical concerns.

CANDIDATE SOLUTIONS:
---
{candidate_solutions}
---

INSTRUCTIONS:
1. For each candidate, provide a score between 1-10 based on its quality.
2. Justify the score with a brief explanation.
3. Identify the most promising candidate based on the scores.
4. Start your answer with "The most promising candidate is Candidate X" (without quotes).
"""
    # Choice Analysis only exectuted once for efficiency but can be repeated if needed to provide more robust results
    evaluation_response = call_llm(value_prompt, use_json_format=False)

    # Extract the most promising candidate
    try:
        # Use regex to find the chosen candidate number
        match = re.search(r"The most promising candidate is Candidate (\d+)", evaluation_response, re.IGNORECASE)
        if not match:
            raise ValueError("Could not find the chosen candidate number in the evaluation response.")
        
        selected_candidate_num = int(match.group(1))

        # Use regex to extract the full text of the selected candidate
        candidate_match = re.search(
            rf"Candidate {selected_candidate_num}:(.*?)(?=Candidate \d+:|\Z)", 
            candidate_solutions, 
            re.DOTALL | re.IGNORECASE
        )
        
        if not candidate_match:
            raise ValueError(f"Could not extract the content for Candidate {selected_candidate_num}.")
            
        selected_candidate = candidate_match.group(1).strip()

    except (ValueError, IndexError) as e:
        print(f"Error parsing candidates: {e}")
        return None

    # Step 3: Refine the selected candidate
    refine_prompt = f"""
    Refine and follow the following analysis plan and execute it into the required JSON format. Ensure all details like scores, explanations, and relevant quotes from the process description are included.

SELECTED ANALYSIS:
{selected_candidate}

LIST OF ETHICAL VALUES:
{values_text}

PROCESS DESCRIPTION:
{process_description}

PROCESS STEPS:
{steps_text}

INSTRUCTIONS:
1. Execute the SELECTED ANALYSIS Plan and apply it on the provided LIST OF ETHICAL VALUES, PROCESS DESCRIPTION, PROCESS STEPS into a valid JSON object.
2. For each step, and for each relevant value, provide a `score`, `explanation`, and `quotes` from the process description that justify the analysis.
3. The final output must be ONLY the JSON object, with no other text.
4. The JSON structure must be:
{{
  "Step Name 1": {{
    "value_name_A": {{ "score": int, "explanation": str, "quotes": [str, ...] }},
    "value_name_B": {{ ... }}
  }},
  "Step Name 2": {{ "value_name_C": {{ ... }} }},
  // ... other steps
}}
"""
    refined_response = call_llm(refine_prompt, use_json_format=True)
    try:
        return json.loads(refined_response)
    except json.JSONDecodeError as e:
        print(f"Error decoding final JSON response: {e}")
        # print("Refined response string:", refined_response)
        return None

''' 
def tree_of_thoughts(process_description, extracted_steps):
    """Tree of Thoughts (ToT): Explore multiple reasoning paths and evaluate the best solution."""
    steps_text = format_steps(extracted_steps)
    values_text = format_values()

    # Step 1: Generate initial candidate solutions (propose step)
    propose_prompt = f"""
    You are an ethics analyst. Analyze the given process description and its individual steps. Identify which ethical values from the provided list are potentially at risk or relevant for EACH process step.

LIST OF ETHICAL VALUES:
{values_text}

PROCESS DESCRIPTION:
{process_description}

PROCESS STEPS:
{steps_text}

INSTRUCTIONS:
1. Generate multiple candidate analyses for the process description and steps.
2. Each candidate should explore a different reasoning path or perspective.
3. Return the candidates as a numbered list.
"""
    candidate_solutions = call_llm(propose_prompt, use_json_format=False)

    # Step 2: Evaluate candidate solutions (value step)
    value_prompt = f"""
    Evaluate the following candidate solutions for their accuracy, consistency, and adherence to ethical analysis principles:

CANDIDATE SOLUTIONS:
{candidate_solutions}

INSTRUCTIONS:
1. For each candidate, provide a score between 1-10 based on its quality.
2. Justify the score with a brief explanation.
3. Identify the most promising candidate based on the scores.
4. Start your answer with "The most promising candidate is Candidate X" (without quotes).
"""
    evaluation_response = call_llm(value_prompt, use_json_format=False)

    # Extract the most promising candidate
    try:
        # Use regex to extract the candidate number
        match = re.search(r"The most promising candidate is Candidate (\d+)", evaluation_response)
        if not match:
            raise ValueError("Could not find a valid candidate number in the evaluation response.")
        selected_candidate_index = int(match.group(1)) - 1
    except ValueError as e:
        print(f"Error parsing candidate number: {e}")
        #print("Evaluation response:", evaluation_response)
        return None

    selected_candidate = candidate_solutions.split("\n")[selected_candidate_index]

    # Step 3: Refine the selected candidate
    refine_prompt = f"""
    Refine the selected candidate solution to ensure it is accurate, consistent, and adheres to the required JSON format:

SELECTED CANDIDATE:
{selected_candidate}

LIST OF ETHICAL VALUES:
{values_text}

INSTRUCTIONS:
1. Refine the analysis to ensure it is complete and accurate.
2. Return ONLY valid JSON with this exact structure:
{{
  "Step Name 1": {{
    "value_name_A": {{ "score": int, "explanation": str, "quotes": [str, ...] }},
    "value_name_B": {{ ... }}
  }},
  "Step Name 2": {{ "value_name_C": {{ ... }} }},
  // ... other steps
}}
4. Make sure that each value is present in the list of ethical values. Else map it to one of the values and remove all values not present in the ethical values list.
"""
    refined_response = call_llm(refine_prompt, use_json_format=True)
    refined_response = json.loads(refined_response)
    return refined_response
'''