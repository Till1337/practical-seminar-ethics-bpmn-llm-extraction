# Ethical Heatmap Plugin for Camunda Modeler

A powerful Camunda Modeler plugin that visualizes ethical risks and values directly on BPMN diagrams using interactive heatmaps. This plugin helps process designers and analysts identify potential ethical implications in their business processes.

## Features

- **Interactive Heatmap Visualization**: Overlay configurable heatmaps on BPMN diagrams to show ethical risk scores for each task
- **Multiple Analysis Techniques**: Support for various prompting strategies including Zero-Shot, Few-Shot, and advanced techniques
- **Comprehensive Ethical Values**: Analyze 11 different ethical dimensions including transparency, privacy, fairness, and sustainability
- **Real-time Data Integration**: Fetch analysis data from the Ethical Analysis API with local fallback support
- **Intuitive UI**: Clean, modern interface with tooltips, legends, and responsive controls
- **File Upload Support**: Upload BPMN files directly from the plugin for instant analysis
- **Judge Evaluation**: Compare AI analysis with human judge evaluations using traffic light indicators
- **Keyboard Shortcuts**: Quick access to plugin features via keyboard shortcuts

## Quick Start

### Prerequisites

- [Camunda Modeler](https://camunda.com/download/modeler/) (latest version)
- [Node.js](https://nodejs.org/) (v14 or higher)
- [Ethical Analysis API](../EthicalAPI) (optional, for live analysis)

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd test-eb/Plugin
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Build the plugin:**
   ```bash
   npm run build
   ```

4. **Install in Camunda Modeler:**
   
   Copy the entire `build/plugin` directory to your Camunda Modeler plugins folder:
   
   **Windows:**
   ```
   %APPDATA%/camunda-modeler/resources/plugins/
   ```
   
   **macOS:**
   ```
   ~/Library/Application Support/camunda-modeler/resources/plugins/
   ```
   
   **Linux:**
   ```
   ~/.config/camunda-modeler/resources/plugins/
   ```

5. **Restart Camunda Modeler**

## Usage

### Basic Usage

1. **Open a BPMN diagram** in Camunda Modeler
2. **Activate the plugin** by clicking **Plugins → Toggle Ethical Heatmap** or using the keyboard shortcut `Ctrl+Shift+E` (`Cmd+Shift+E` on macOS)
3. **Select your analysis parameters:**
   - Choose the process to analyze
   - Select a prompting technique
   - Pick an ethical value to visualize
4. **View the heatmap** - tasks will be colored based on their ethical risk scores
5. **Hover over tasks** to see detailed explanations and judge evaluations

### Creating New Analysis

1. **Click "Select BPMN File"** in the plugin panel
2. **Choose a BPMN file** (.bpmn or .xml format)
3. **Add an optional description** of the process
4. **Click "Analyze Process"** to submit for analysis
5. **Wait for completion** (analysis may take several minutes)
6. **Refresh the data** to view results

### Understanding the Visualization

- **Color Scale**: Blue (low risk) → Green → Yellow → Orange → Red (high risk)
- **Score Range**: 0-10 scale for ethical risk assessment
- **Judge Scores**: Traffic light indicators (● Green = Good, ● Yellow = Adequate, ● Red = Poor)
- **Tooltips**: Hover over tasks for detailed explanations and scores

### Keyboard Shortcuts

- **Toggle Ethical Heatmap**: `Ctrl+Shift+E` (Windows/Linux) or `Cmd+Shift+E` (macOS)
- **Refresh Ethical Data**: `Ctrl+Shift+R` (Windows/Linux) or `Cmd+Shift+R` (macOS)

### Using Local Data (Without API)

When not using the Ethical Analysis API, you can provide local analysis data by placing JSON files in the plugin's resources directory. These files must be present before runtime.

#### Local Data Structure

Place your analysis files in:
```
Plugin/client/resources/prompt-results/
├── value-extraction/
│   ├── process1_results.json
│   ├── process2_results.json
│   └── ...
└── judge_results/
    ├── process1_judge_results.json
    ├── process2_judge_results.json
    └── ...
```

#### Value Extraction Format

Create files named `{process_id}_results.json` in the `value-extraction` folder:

```json
{
  "ethicalAnalysis": {
    "zero_shot": {
      "Task Name 1": {
        "transparency": {
          "score": 8,
          "explanation": "This task provides clear visibility into the process..."
        },
        "privacy": {
          "score": 6,
          "explanation": "Personal data is handled with appropriate safeguards..."
        }
      },
      "Task Name 2": {
        "fairness": {
          "score": 9,
          "explanation": "This task ensures equal treatment for all users..."
        }
      }
    },
    "few_shot": {
      // Similar structure for few-shot analysis
    }
  }
}
```

#### Judge Results Format

Create files named `{process_id}_judge_results.json` in the `judge_results` folder:

```json
{
  "zero_shot": {
    "overall_scores": {
      "comprehensiveness": 4,
      "accuracy": 5,
      "specificity": 3,
      "relevance": 4,
      "actionability": 3
    },
    "step_evaluations": [
      {
        "step_name": "Task Name 1",
        "score": 4.0,
        "strengths": ["Clear explanation", "Good coverage"],
        "weaknesses": ["Could be more specific"],
        "missed_concerns": ["Data retention"],
        "invalid_concerns": []
      }
    ],
    "overall_feedback": "The analysis provides good coverage of ethical concerns...",
    "improvement_suggestions": ["Consider adding more specific recommendations..."]
  }
}
```

#### Important Notes

- **File Naming**: Use the exact process ID from your BPMN file as the prefix
- **Pre-runtime**: Files must be placed in the resources directory before building the plugin
- **JSON Format**: Ensure valid JSON syntax with proper escaping
- **Task Names**: Must exactly match the task names in your BPMN diagram
- **Fallback**: Local data is used when the API is unavailable or returns 404

## Sample BPMN Files for Testing

To help you get started, two sample BPMN files are included in the plugin:

- **test1.bpmn**: Located in `Plugin/client/resources/models/test1.bpmn`. This file is intended for testing the API integration. The corresponding analysis data for this process is already available on the API (if the API is running with the default dataset).
- **test2.bpmn**: Located in `Plugin/client/resources/models/test2.bpmn`. This file is intended for testing the local backup/fallback functionality. The corresponding analysis data for this process is provided in the local JSON files:
  - Value extraction: `Plugin/client/resources/prompt-results/value-extraction/test2_results.json`
  - Judge results: `Plugin/client/resources/prompt-results/judge_results/test2_judge_results.json`

You can use these files to quickly verify that both API and local fallback data loading are working as expected in the plugin.

## Development

### Project Structure

```
Plugin/
├── client/                    # Frontend source code
│   ├── EthicalHeatmapModule.js  # Main plugin module
│   ├── DataService.js           # API and data management
│   ├── HeatmapGenerator.js      # Heatmap rendering logic
│   ├── FilePicker.js            # File upload component
│   ├── index.js                 # Client entry point
│   └── styles/
│       └── plugin.css           # Plugin styles
├── build/                     # Built plugin files
├── scripts/
│   └── deploy.js              # Deployment script
├── index.js                   # Plugin entry point
├── menu.js                    # Menu configuration
├── package.json               # Dependencies and scripts
└── webpack.config.plugin.js   # Build configuration
```

### Available Scripts

- `npm run dev` - Build with watch mode for development
- `npm run build` - Build for production
- `npm run build:dev` - Build for development
- `npm run deploy` - Deploy to Camunda Modeler
- `npm run clean` - Clean build directory
- `npm run all` - Clean, build, and deploy

### Configuration

The plugin connects to the Ethical Analysis API by default at `http://localhost:8000`. You can modify the API endpoint in `client/DataService.js`.

## Technical Details

### Ethical Values Supported

- **Transparency**: Openness, traceability and explainability of process logic, data flows and decision criteria
- **Responsibility**: Proactive assignment of obligations, with clear remediation and oversight mechanisms
- **Accountability**: Mechanisms to hold individuals and units answerable for process outcomes
- **Fairness**: Equitable, non-discriminatory treatment of all stakeholders, with justice in allocation of benefits and burdens
- **Well-being**: Promotion of physical, mental and social well-being of participants and communities
- **Human Autonomy**: Protection of individual agency, informed consent and right to opt-out of automated decisions
- **Solidarity**: Fostering mutual support, shared responsibility and collaboration among stakeholders
- **Diversity & Inclusion**: Active inclusion of multiple perspectives and equitable opportunities for all voices
- **Privacy**: Protection of personal and sensitive data throughout the process lifecycle
- **Sustainability**: Minimizing environmental impact and promoting social sustainability of operations
- **Trust**: Building reliable, honest and transparent relationships with all stakeholders

### Prompting Techniques

- **Zero-Shot**: Direct analysis without examples
- **Few-Shot**: Analysis with limited examples
- **Contrastive CoT**: Chain-of-thought reasoning
- **Universal Self-Consistency**: Multiple reasoning paths
- **Chain of Verification**: Step-by-step verification
- **Tree of Thoughts**: Multi-branch reasoning

## Troubleshooting

### Common Issues

**Plugin not appearing in Camunda Modeler:**
- Ensure the plugin is installed in the correct directory
- Restart Camunda Modeler completely
- Check the console for error messages

**No data loading:**
- Verify the Ethical Analysis API is running
- Check network connectivity to `http://localhost:8000`
- Ensure BPMN files have proper task names

**Build errors:**
- Update Node.js to version 14 or higher
- Clear node_modules and reinstall: `rm -rf node_modules && npm install`
- Check for conflicting global packages

