# Ethical Analysis API

A FastAPI-based service for conducting ethical analyses of business processes using LLM-as-a-judge evaluations.

## Project Structure

```
EthicalAPI/
├── api.py                    # Main FastAPI application
├── README.md                 # This file
├── Dockerfile               # Container configuration
└── PromptingCode/           # Core analysis modules
    ├── ethics_analyzer.py   # Main ethical analysis engine
    ├── ethics_values.py     # Ethical value definitions
    ├── llm_as_judge.py     # LLM-as-a-judge evaluation
    ├── ollama_api.py       # Ollama LLM integration
    ├── process_extraction.py # BPMN XML processing
    ├── prompting_techniques.py # Prompting strategies
    ├── utils.py            # Utility functions
    ├── requirements.txt    # Python dependencies
    └── Results/           # Analysis output files
        ├── ethics_analysis.csv
        └── llm_judge_evaluation.csv
```

## Setup & Installation

### Prerequisites

- Python 3.8+
- Gemini API Key (for LLM integration) 
- FastAPI and Uvicorn

### Quick Start Docker

```bash
# Build the container
docker build -t ethical-analysis-api .

# Run the container
# If needed with your Auth Credentials and the mnt directory 
docker run -p 8000:8000 -v /path/to/your/local/directory:/app/PromptingCode/Results -e GEMINI_API_KEY="YOUR API KEY" ethical-analysis-api
```

## API Endpoints

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information |
| `/analysis/{bpmn_id}` | GET | Retrieve existing analysis results |
| `/analysis/create` | POST | Create new ethical analysis (Ethical Score + LLM as a Judge) |
| `/evaluation/{bpmn_id}` | GET | Retrieve LLM-as-a-judge evaluations |
| `/analysis/status` | GET | Monitor active analysis requests |

### Request Examples

#### Create Analysis
```bash
curl -X POST "http://localhost:8000/analysis/create" \
  -H "Content-Type: application/json" \
  -d '{
    "process_name": "credit_scoring",
    "file_name": "credit_scoring.bpmn",
    "description": "Credit scoring process for loan applications",
    "bpmn_xml": "<bpmn:definitions>...</bpmn:definitions>"
  }'
```

#### Retrieve Analysis
```bash
curl "http://localhost:8000/analysis/credit_scoring"
```

#### Check Status
```bash
curl "http://localhost:8000/analysis/status"
```

## Configuration

### Environment Variables

The API uses the following default configuration:

- **Host**: `0.0.0.0`
- **Port**: `8000`
- **Results Directory**: `docker volumn or mnt file path`
- **CSV Files in the Volumne**: 
  - `ethics_analysis.csv`
  - `llm_judge_evaluation.csv`

### LLM Provider Configuration

The API supports multiple LLM providers. You can switch between them by modifying `PromptingCode/ollama_api.py` and rebuilding the docker image:


**To switch providers:**
1. Open `PromptingCode/ollama_api.py`
2. Comment out the current `call_ollama` function
3. Uncomment the desired provider's function
4. Set the appropriate environment variable:
   - **Gemini**: `GEMINI_API_KEY="your_key"`
   - **Groq**: `GROQ_TOKEN="your_token"`
   - **Ollama**: No API key needed (runs locally)


## Data Models

### Analysis Request
```python
{
    "process_name": "string",      # Process identifier
    "file_name": "string",         # BPMN file name
    "description": "string",       # Process description
    "technique": "string",         # Analysis technique (ignored)
    "bpmn_xml": "string"          # BPMN XML content
}
```

### Analysis Result
```python
{
    "process_name": "string",
    "file_name": "string", 
    "prompting_technique": "string",
    "step_name": "string",
    "ethical_value": "string",
    "score": "integer",
    "explanation": "string",
    "quotes": "string"
}
```

### Judge Evaluation
```python
{
    "process_name": "string",
    "file_name": "string",
    "method": "string",
    "step_name": "string", 
    "score": "float",
    "strengths": "string",
    "weaknesses": "string",
    "missed_concerns": "string",
    "invalid_concerns": "string",
    "overall_feedback": "string",
    "improvement_suggestions": "string"
}
```

## Parallel Processing

The API supports multiple concurrent requests:

1. **Request Tracking**: Each analysis is tracked with status updates
2. **Thread Pool**: Analysis runs in background threads
3. **Status Monitoring**: Real-time progress tracking
4. **Auto Cleanup**: Old completed analyses are automatically removed

### Status Types
- `processing`: Analysis in progress
- `completed`: Analysis finished successfully  
- `failed`: Analysis encountered an error

## Error Handling

The API provides comprehensive error handling:

- **400 Bad Request**: Invalid input data
- **404 Not Found**: Analysis not found
- **500 Internal Server Error**: Processing errors

All errors include descriptive messages for debugging.


## Integration

### Frontend Integration

The API is designed to work with the Ethical Analysis Plugin:

```javascript
// Example frontend integration
const response = await fetch('/analysis/create', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        process_name: processId,
        file_name: fileName,
        description: processDescription,
        bpmn_xml: bpmnXmlContent
    })
});
```

### Plugin Communication

The API expects:
- Process ID as `process_name`
- File name as `file_name` 
- BPMN XML content for analysis
- Process description for context