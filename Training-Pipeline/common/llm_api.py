from ollama import chat
import os
import json
import logging
from google import genai
from google.genai import types


# --- Ollama (commented out, keep for reference) ---
'''
def call_llm(prompt, use_json_format=True):
    try:
        messages = [{"role": "user", "content": prompt}]
        resp = chat(
            model='gemma3:12b',
            messages=messages,
            format='json' if use_json_format else None,
            options={
                "temperature": 0.2,
            }
        )
        return resp.message.content
    except Exception as e:
        import json
        print(f"Error calling Ollama: {e}")
        return json.dumps({"error": f"Failed to call Ollama: {e}"})

'''
# --- Groq (commented out, keep for reference) ---
'''
def call_llm(prompt, use_json_format=True):
    """Calls the Groq API with the given prompt."""
    client = Groq(
        api_key=os.environ["GROQ_TOKEN"],
    )
    try:
        messages = [{"role": "user", "content": prompt}]
        
        response_kwargs = {
            "model": "llama3-70b-8192",
            "messages": messages,
            "temperature": 0.2,
        }
        if use_json_format:
            response_kwargs["response_format"] = {"type": "json_object"}

        resp = client.chat.completions.create(**response_kwargs)
         
        return resp.choices[0].message.content
        
    except Exception as e:
        print(f"Error calling Groq: {e}")
        return json.dumps({"error": f"Failed to call Groq: {e}"})
'''

def call_llm(prompt: str, model: str = "gemma-3-12b-it", use_json_format: bool = False) -> str:
    """
    Calls the Google Gemini API with a given prompt using a streaming client.

    Args:
        prompt: The text prompt to send to the model.
        model: The model to use (e.g., "gemma-3-12b-it").
        use_json_format: If True, the function will attempt to parse a JSON object
                         from the response. If False, it will return the raw text.

    Returns:
        A string containing either the JSON response, the plain text response,
        or a JSON string with an error message if something fails.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set.")

    logging.info(f"API CALL: Google Gemini | Model: {model} | Expect JSON: {use_json_format}")
    logging.debug(f"Prompt snippet: {prompt[:200]}...")

    
    client = genai.Client(api_key=api_key)

    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)],
        ),
    ]

    config = types.GenerateContentConfig(
        temperature=0.2,
        response_mime_type="text/plain", # Gemma = only text/plain 
    )

    response_text = ""
    try:
        # Stream the response from the model
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=config,
        ):
            if chunk.text is not None:
                response_text += chunk.text

        # --- Path 1: We are expecting a JSON object ---
        if use_json_format:
            logging.debug("Attempting to parse JSON from streamed response.")
            try:
                # Clean the response: LLMs often wrap JSON in ```json ... ```
                if "```json" in response_text:
                    json_str = response_text.split("```json")[1].split("```")[0].strip()
                else:
                    # Find the first '{' and last '}' to extract the JSON object
                    start = response_text.find('{')
                    end = response_text.rfind('}')
                    if start != -1 and end != -1 and end > start:
                        json_str = response_text[start:end+1]
                    else:
                        raise json.JSONDecodeError("No JSON object found in response.", response_text, 0)
                
                # Validate that the extracted string is valid JSON
                json.loads(json_str)
                logging.debug("Successfully parsed JSON.")
                return json_str

            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse LLM response as JSON. Error: {e}")
                logging.error(f"--- UNPARSABLE TEXT ---\n{response_text}\n--------------------")
                return json.dumps({"error": "Failed to parse LLM response as JSON", "response": response_text})
        
        else:
            logging.debug("Returning text/plain.")
            return response_text

    except Exception as e:
        logging.error(f"Error calling Google Gemini: {e}")
        return json.dumps({"error": f"API call to Google Gemini failed: {e}"})


