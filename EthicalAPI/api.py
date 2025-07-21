"""
A FastAPI-based service for conducting ethical analyses of business processes.
Supports parallel processing of multiple BPMN files and provides LLM-as-a-judge evaluations.

"""

import os
import csv
import logging
import asyncio
import threading
from collections import defaultdict
from fastapi import FastAPI, HTTPException, Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Union

# Add PromptingCode to Python path for imports
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'PromptingCode'))

# Import analysis modules
from PromptingCode.ethics_analyzer import EthicsAnalyzer
from PromptingCode.process_extraction import extract_steps_from_bpmn, clean_extracted_steps
from PromptingCode.utils import flatten_ethics_results
from PromptingCode.llm_as_judge import run_judge_for_analysis

# Config

# API metadata for OpenAPI documentation
TAGS_METADATA = [
    {
        "name": "Ethical Analysis",
        "description": "Endpoints for creating and retrieving ethical analyses of business processes.",
    },
    {
        "name": "LLM-as-a-Judge Evaluation",
        "description": "Endpoints for retrieving LLM-as-a-judge evaluations of ethical analyses.",
    },
]

# File paths and configuration
RESULTS_DIR = "/app/PromptingCode/Results"
ETHICS_ANALYSIS_CSV = os.path.join(RESULTS_DIR, 'ethics_analysis.csv')
LLM_JUDGE_CSV = os.path.join(RESULTS_DIR, 'llm_judge_evaluation.csv')
FIELDNAMES = [
    'process_name', 'file_name', 'prompting_technique', 'step_name', 
    'ethical_value', 'score', 'explanation', 'quotes'
]

# Thread safety locks
CSV_LOCK = threading.Lock()
ANALYSIS_LOCK = threading.Lock()

# Active analysis tracking
ACTIVE_ANALYSES = {}

# API Init

app = FastAPI(
    title="Ethical Analysis API",
    description="""
    This API provides endpoints for conducting and retrieving ethical analyses of business processes.
    You can submit a process description to generate a new analysis or retrieve existing results.
    It also offers access to LLM-as-a-judge evaluations of the performed analyses.
    
    Features:
    - Parallel processing of multiple BPMN files
    - LLM-as-a-judge evaluations
    - Thread-safe CSV operations
    - Real-time status monitoring
    """,
    version="1.0.0",
    openapi_tags=TAGS_METADATA
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Data Models

class ProcessAnalysisRequest(BaseModel):
    """Request model for creating a new ethical analysis."""
    process_name: str = Field(..., description="The name of the business process.")
    file_name: str = Field(..., description="The file name associated with the process model.")
    description: Optional[str] = Field("BPMN diagram analysis", description="A textual description of the business process to be analyzed.")
    technique: Optional[str] = Field("all", description="This is ignored; all techniques are run by default.")
    bpmn_xml: Optional[str] = Field(None, description="BPMN XML content of the process model.")

class AnalysisResult(BaseModel):
    """Response model for ethical analysis results."""
    process_name: str = Field(..., description="The name of the business process.")
    file_name: str = Field(..., description="The file name associated with the process model.")
    prompting_technique: str = Field(..., description="The prompting technique used for the analysis.")
    step_name: str = Field(..., description="The name of the process step being analyzed.")
    ethical_value: str = Field(..., description="The ethical value identified in the step.")
    score: Optional[int] = Field(None, description="A score representing the intensity of the ethical concern.")
    explanation: str = Field(..., description="An explanation of why the ethical value is relevant.")
    quotes: Union[str, List[str]] = Field(..., description="Direct quotes from the process description supporting the analysis.")

class JudgeEvaluationResult(BaseModel):
    """Response model for LLM-as-a-judge evaluation results."""
    process_name: str = Field(..., description="The name of the business process.")
    file_name: str = Field(..., description="The file name associated with the process model.")
    method: str = Field(..., description="The prompting technique that was evaluated.")
    step_name: str = Field(..., description="The name of the process step being evaluated.")
    score: Optional[float] = Field(None, description="The evaluation score for the step.")
    strengths: str = Field(..., description="Strengths of the analysis for this step.")
    weaknesses: str = Field(..., description="Weaknesses of the analysis for this step.")
    missed_concerns: str = Field(..., description="Ethical concerns missed by the analysis.")
    invalid_concerns: str = Field(..., description="Concerns that were incorrectly identified.")
    overall_feedback: str = Field(..., description="Overall feedback on the analysis quality.")
    improvement_suggestions: str = Field(..., description="Suggestions for improving the analysis.")

 # Misc Func 

def initialize_data_files():
    """Initialize CSV files if they don't exist."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    
    if not os.path.exists(ETHICS_ANALYSIS_CSV):
        with open(ETHICS_ANALYSIS_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(FIELDNAMES)

    if not os.path.exists(LLM_JUDGE_CSV):
        with open(LLM_JUDGE_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "process_name", "file_name", "method", "step_name", "score", 
                "strengths", "weaknesses", "missed_concerns", "invalid_concerns", 
                "overall_feedback", "improvement_suggestions"
            ])

def append_to_csv(filepath: str, fieldnames: List[str], data_rows: List[dict]):
    """Append data rows to a CSV file with thread safety."""
    with CSV_LOCK:
        file_exists = os.path.isfile(filepath)
        with open(filepath, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not file_exists or os.path.getsize(filepath) == 0:
                writer.writeheader()
            writer.writerows(data_rows)

def check_and_load_existing_analysis(process_name: str, file_name: str, csv_path: str):
    """
    Check if an analysis exists and load it.
    
    Returns:
        tuple: (analysis_results_dict, raw_results_list) or (None, None) if not found
    """
    with CSV_LOCK:
        if not os.path.exists(csv_path):
            return None, None

        existing_results = defaultdict(lambda: defaultdict(dict))
        raw_rows = []
        found = False

        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['process_name'] == process_name and row['file_name'] == file_name:
                    found = True
                    raw_rows.append(row)
                    tech = row['prompting_technique']
                    step = row['step_name']
                    value = row['ethical_value']
                    
                    try:
                        score = int(row.get("score", 0))
                    except (ValueError, TypeError):
                        score = 0
                        
                    existing_results[tech][step][value] = {
                        "score": score,
                        "explanation": row.get("explanation", ""),
                        "quotes": [q.strip() for q in row.get("quotes", "").split(";") if q.strip()]
                    }

        if not found:
            return None, None

        final_results = {tech: dict(steps) for tech, steps in existing_results.items()}
        return final_results, raw_rows

# API Endpoints

@app.get("/analysis/{bpmn_id}", response_model=List[AnalysisResult], tags=["Ethical Analysis"])
async def get_analysis(bpmn_id: str = Path(..., description="The BPMN ID of the process to retrieve.")):
    """
    Retrieve existing ethical analysis results for a given BPMN ID.
    
    The BPMN ID is used directly to search for matching process_name or file_name in the database.
    """
    if not os.path.exists(ETHICS_ANALYSIS_CSV):
        raise HTTPException(status_code=404, detail="Analysis data file not found.")

    results = []
    with open(ETHICS_ANALYSIS_CSV, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row['process_name'] == bpmn_id or row['file_name'] == bpmn_id:
                row['score'] = int(row['score']) if row['score'] else None
                results.append(row)

    if not results:
        raise HTTPException(status_code=404, detail=f"No analysis found for BPMN ID '{bpmn_id}'.")

    return results

@app.get("/evaluation/{bpmn_id}", response_model=List[JudgeEvaluationResult], tags=["LLM-as-a-Judge Evaluation"])
async def get_evaluation(bpmn_id: str = Path(..., description="The BPMN ID of the process whose evaluation is to be retrieved.")):
    """
    Retrieve existing LLM-as-a-judge evaluation results for a given BPMN ID.
    
    The BPMN ID is used directly to search for matching process_name or file_name in the database.
    """
    if not os.path.exists(LLM_JUDGE_CSV):
        raise HTTPException(status_code=404, detail="LLM judge evaluation file not found.")

    results = []
    with open(LLM_JUDGE_CSV, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row['process_name'] == bpmn_id or row['file_name'] == bpmn_id:
                try:
                    row['score'] = float(row['score']) if row['score'] else None
                except (ValueError, TypeError):
                    row['score'] = None
                results.append(row)

    if not results:
        raise HTTPException(status_code=404, detail=f"No evaluation found for BPMN ID '{bpmn_id}'.")

    return results

@app.post("/analysis/create", response_model=List[AnalysisResult], tags=["Ethical Analysis"])
async def create_analysis(request: ProcessAnalysisRequest):
    """
    Create a new ethical analysis and run an LLM-as-a-judge evaluation.
    
    Features:
    - Supports parallel processing of multiple requests
    - Skips generation if analysis already exists
    - Thread-safe CSV operations
    - Real-time status tracking
    """
    try:
        search_process_name = request.process_name
        search_file_name = request.file_name
        analysis_id = f"{search_process_name}_{search_file_name}"
        
        logging.info(f"Received analysis request for {search_process_name}/{search_file_name}")

        # Track this analysis as active
        with ANALYSIS_LOCK:
            ACTIVE_ANALYSES[analysis_id] = {
                "status": "processing",
                "start_time": asyncio.get_event_loop().time(),
                "process_name": search_process_name,
                "file_name": search_file_name
            }

        # Run analysis in thread pool for parallel processing
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, 
            _process_analysis_request, 
            search_process_name, 
            search_file_name, 
            request.description, 
            request.bpmn_xml,
            analysis_id
        )
        
        # Mark analysis as completed
        with ANALYSIS_LOCK:
            if analysis_id in ACTIVE_ANALYSES:
                ACTIVE_ANALYSES[analysis_id]["status"] = "completed"
                ACTIVE_ANALYSES[analysis_id]["end_time"] = asyncio.get_event_loop().time()
        
        return result

    except ValueError as e:
        logging.error(f"Validation error during analysis creation: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"An unexpected error occurred during analysis creation: {e}", exc_info=True)
        # Mark analysis as failed
        analysis_id = f"{request.process_name}_{request.file_name}"
        with ANALYSIS_LOCK:
            if analysis_id in ACTIVE_ANALYSES:
                ACTIVE_ANALYSES[analysis_id]["status"] = "failed"
                ACTIVE_ANALYSES[analysis_id]["error"] = str(e)
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {e}")

@app.get("/analysis/status", tags=["Ethical Analysis"])
async def get_analysis_status():
    """
    Get the status of all active analysis requests.
    
    Useful for monitoring parallel processing and request progress.
    """
    # Clean up old completed analyses (older than 1 hour)
    current_time = asyncio.get_event_loop().time()
    with ANALYSIS_LOCK:
        # Remove analyses that completed more than 1 hour ago
        to_remove = []
        for analysis_id, analysis in ACTIVE_ANALYSES.items():
            if (analysis.get("status") in ["completed", "failed"] and 
                analysis.get("end_time") and 
                current_time - analysis["end_time"] > 3600):  # 1 hour
                to_remove.append(analysis_id)
        
        for analysis_id in to_remove:
            del ACTIVE_ANALYSES[analysis_id]
        
        return {
            "active_analyses": ACTIVE_ANALYSES,
            "total_active": len(ACTIVE_ANALYSES),
            "completed": len([a for a in ACTIVE_ANALYSES.values() if a.get("status") == "completed"]),
            "failed": len([a for a in ACTIVE_ANALYSES.values() if a.get("status") == "failed"]),
            "processing": len([a for a in ACTIVE_ANALYSES.values() if a.get("status") == "processing"])
        }

@app.get("/", tags=["General"])
def read_root():
    """Root endpoint with API information."""
    return {
        "message": "Welcome to the Ethical Analysis API",
        "version": "1.0.0",
        "docs": "/docs",
        "features": [
            "Parallel processing of BPMN files",
            "LLM-as-a-judge evaluations", 
            "Real-time status monitoring",
            "Thread-safe operations"
        ]
    }

# Analysis

def _process_analysis_request(search_process_name: str, search_file_name: str, 
                            description: str, bpmn_xml: str, analysis_id: str):
    """
    Process the analysis request in a separate thread.
    
    This function runs in a thread pool executor to support parallel processing
    without blocking the main event loop.
    """
    try:
        logging.info(f"Processing analysis request for {search_process_name}/{search_file_name}")

        # Check if analysis already exists
        all_ethics_results, existing_raw_results = check_and_load_existing_analysis(
            search_process_name, search_file_name, ETHICS_ANALYSIS_CSV
        )

        if all_ethics_results and existing_raw_results:
            logging.info(f"Analysis for {search_process_name}/{search_file_name} already exists. Skipping generation.")
            final_raw_results = existing_raw_results
        else:
            logging.info(f"No existing analysis found. Starting new analysis for {search_process_name}/{search_file_name}.")
            
            # Validate BPMN XML
            if not bpmn_xml:
                raise ValueError("BPMN XML content is required. The plugin failed to extract BPMN XML from the diagram.")
            
            # Extract and process BPMN steps
            extracted_steps = _extract_bpmn_steps(bpmn_xml)
            
            # Run ethical analysis
            analyzer = EthicsAnalyzer()
            all_ethics_results = analyzer.analyze_all(description, extracted_steps)
            if not all_ethics_results:
                raise ValueError("Ethical analysis returned no results.")

            # Flatten and save results
            final_raw_results = _save_analysis_results(all_ethics_results, search_process_name, search_file_name)

        # Run LLM-as-a-judge evaluation
        _run_judge_evaluation(search_process_name, search_file_name, description, all_ethics_results)

        return final_raw_results

    except Exception as e:
        logging.error(f"Error in _process_analysis_request for {search_process_name}/{search_file_name}: {e}")
        raise e

def _extract_bpmn_steps(bpmn_xml: str):
    """Extract process steps from BPMN XML content."""
    try:
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.bpmn', delete=False) as temp_file:
            temp_file.write(bpmn_xml)
            temp_file_path = temp_file.name
        
        extracted_steps = extract_steps_from_bpmn(temp_file_path)
        os.unlink(temp_file_path)  # Clean up temp file
        extracted_steps = clean_extracted_steps(extracted_steps)
        
        logging.info(f"Successfully extracted {len(extracted_steps)} steps from BPMN XML")
        return extracted_steps
        
    except Exception as e:
        logging.error(f"Failed to extract steps from BPMN XML: {e}")
        raise ValueError(f"Failed to parse BPMN XML content: {str(e)}")

def _save_analysis_results(all_ethics_results: dict, process_name: str, file_name: str):
    """Save analysis results to CSV file."""
    final_raw_results = []
    for tech, results in all_ethics_results.items():
        flattened = flatten_ethics_results(results, process_name, file_name, tech)
        final_raw_results.extend(flattened)
    
    if final_raw_results:
        append_to_csv(ETHICS_ANALYSIS_CSV, FIELDNAMES, final_raw_results)
        logging.info(f"Successfully saved {len(final_raw_results)} new analysis rows.")
    
    return final_raw_results

def _run_judge_evaluation(process_name: str, file_name: str, description: str, all_ethics_results: dict):
    """Run LLM-as-a-judge evaluation on the analysis results."""
    logging.info("Proceeding to LLM-as-a-judge evaluation.")
    
    # Ensure all_ethics_results is properly structured
    if all_ethics_results is None:
        return
    
    judge_results = run_judge_for_analysis(
        process_name=process_name,
        file_name=file_name,
        process_description=description,
        all_ethics_results=all_ethics_results
    )
    
    if judge_results:
        judge_fieldnames = [
            "process_name", "file_name", "method", "step_name", "score", 
            "strengths", "weaknesses", "missed_concerns", "invalid_concerns", 
            "overall_feedback", "improvement_suggestions"
        ]
        append_to_csv(LLM_JUDGE_CSV, judge_fieldnames, judge_results)
        logging.info(f"Successfully saved {len(judge_results)} LLM judge evaluation rows.")



# Initialize data files on startup
initialize_data_files()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
