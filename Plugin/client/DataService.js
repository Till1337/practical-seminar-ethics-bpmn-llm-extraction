/**
 * DataService handles fetching and caching ethical analysis data
 */
function importAll(r, suffix) {
  const dataMap = new Map();
  const regex = new RegExp(`\\.\\/(.+)${suffix}$`);
  r.keys().forEach(key => {
    const match = key.match(regex);
    if (match && match[1]) {
      const processId = match[1];
      dataMap.set(processId, r(key));
    }
  });
  return dataMap;
}

const valueExtractionMap = importAll(require.context('./resources/prompt-results/value-extraction', false, /_results\.json$/), '_results\\.json');
const judgeDataMap = importAll(require.context('./resources/prompt-results/judge_results', false, /_judge_results\.json$/), '_judge_results\\.json');

const API_BASE_URL = 'http://localhost:8000';

const TECHNIQUE_NAME_MAPPING = {
  'Zero-Shot': 'zero_shot',
  'Few-Shot': 'few_shot',
  'Contrastive CoT': 'contrastive_cot',
  'Universal Self-Consistency': 'universal_self_consistency',
  'Chain of Verification': 'chain_of_verification',
  'Tree of Thoughts': 'tree_of_thoughts'
};

const TECHNIQUE_DISPLAY_MAPPING = {
  'zero_shot': 'Zero-Shot',
  'few_shot': 'Few-Shot',
  'contrastive_cot': 'Contrastive CoT',
  'universal_self_consistency': 'Universal Self-Consistency',
  'chain_of_verification': 'Chain of Verification',
  'tree_of_thoughts': 'Tree of Thoughts'
};

function transformEthicalData(results) {
  const ethicalAnalysis = {};
  results.forEach(r => {
    const tech = r.prompting_technique;
    if (!ethicalAnalysis[tech]) {
      ethicalAnalysis[tech] = {};
    }
    if (!ethicalAnalysis[tech][r.step_name]) {
      ethicalAnalysis[tech][r.step_name] = {};
    }
    ethicalAnalysis[tech][r.step_name][r.ethical_value] = {
      score: r.score,
      explanation: r.explanation,
      quotes: r.quotes,
    };
  });
  return { ethicalAnalysis };
}

function transformLocalData(localData) {
  if (!localData || !localData.ethicalAnalysis) {
    return { ethicalAnalysis: {} };
  }

  const transformedAnalysis = {};
  
  for (const localTechnique in localData.ethicalAnalysis) {
    const apiTechnique = TECHNIQUE_NAME_MAPPING[localTechnique] || localTechnique;
    transformedAnalysis[apiTechnique] = localData.ethicalAnalysis[localTechnique];
  }
  
  return { ethicalAnalysis: transformedAnalysis };
}

function transformJudgeData(results) {
  const judgeData = {};
  results.forEach(r => {
    const tech = r.method;
    if (!judgeData[tech]) {
      judgeData[tech] = { step_evaluations: [] };
    }
    judgeData[tech].step_evaluations.push({
      step_name: r.step_name,
      score: r.score,
      strengths: r.strengths,
      weaknesses: r.weaknesses,
      missed_concerns: r.missed_concerns,
      invalid_concerns: r.invalid_concerns,
      overall_feedback: r.overall_feedback,
      improvement_suggestions: r.improvement_suggestions,
    });
  });
  return judgeData;
}

function transformLocalJudgeData(localJudgeData) {
  return transformJudgeData(localJudgeData);
}

class DataService {
  constructor() {
    this._localData = valueExtractionMap;
    this._localJudgeData = judgeDataMap;
    this._apiDataCache = new Map();
    this._apiJudgeDataCache = new Map();
    this._availableProcessIds = Array.from(valueExtractionMap.keys());
    this.API_BASE_URL = API_BASE_URL;
    

  }

  async getEthicalDataForModel(modelId) {
    if (this._apiDataCache.has(modelId)) {
      return this._apiDataCache.get(modelId);
    }

    try {
      const response = await fetch(`${API_BASE_URL}/analysis/${modelId}`);
      
      if (response.ok) {
        const results = await response.json();
        const transformedData = transformEthicalData(results);
        this._apiDataCache.set(modelId, transformedData);
        return transformedData;
      }
      
      if (response.status === 404) {
        console.log(`No data found on API for ${modelId}, falling back to local data`);
      } else {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
    } catch (error) {
      console.warn(`API call failed for '${modelId}'. Error: ${error.message}. Using local fallback.`);
    }

    if (this._localData.has(modelId)) {
      const localData = this._localData.get(modelId);
      return transformLocalData(localData);
    }

    return { ethicalAnalysis: {} };
  }

  async getJudgeDataForModel(modelId) {
    if (this._apiJudgeDataCache.has(modelId)) {
      return this._apiJudgeDataCache.get(modelId);
    }

    try {
      const response = await fetch(`${API_BASE_URL}/evaluation/${modelId}`);
      
      if (response.ok) {
        const results = await response.json();
        const transformedData = transformJudgeData(results);
        this._apiJudgeDataCache.set(modelId, transformedData);
        return transformedData;
      }
      
      if (response.status === 404) {
        console.log(`No judge evaluation found on API for model '${modelId}'.`);
      } else {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
    } catch (error) {
      console.warn(`API call for judge data failed for '${modelId}'. Error: ${error.message}.`);
    }
    
    if (this._localJudgeData.has(modelId)) {
      const localJudgeData = this._localJudgeData.get(modelId);
      return transformLocalJudgeData(localJudgeData);
    }

    return null;
  }

  async createAnalysis(bpmnId, description, bpmnXml = null, processName = null) {
    const timeoutPromise = new Promise((resolve) => {
      setTimeout(() => {
        this._showTimeoutMessage();
        resolve('timeout');
      }, 30000);
    });

    const apiRequestPromise = this._makeCreateAnalysisRequest(bpmnId, description, bpmnXml, processName);

    try {
      const result = await Promise.race([apiRequestPromise, timeoutPromise]);
      
      if (result === 'timeout') {
        this._showTimeoutMessage();
        return await apiRequestPromise;
      }
      
      return result;
    } catch (error) {
      console.error(`Failed to create analysis for ${bpmnId}:`, error);
      throw error;
    }
  }

  async _makeCreateAnalysisRequest(bpmnId, description, bpmnXml = null, processName = null) {
    const requestBody = {
      process_name: processName || bpmnId,
      file_name: bpmnId,
      description: description,
    };

    if (bpmnXml) {
      requestBody.bpmn_xml = bpmnXml;
    }

    const response = await fetch(`${API_BASE_URL}/analysis/create`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      const errorBody = await response.text();
      let errorMessage = `HTTP error! status: ${response.status}`;
      
      try {
        const errorJson = JSON.parse(errorBody);
        errorMessage = errorJson.detail || errorMessage;
      } catch (e) {
        errorMessage += `, body: ${errorBody}`;
      }
      
      if (response.status === 400 && errorMessage.includes('BPMN XML content is required')) {
        throw new Error('Failed to extract BPMN XML from the diagram. Please try refreshing the page and try again.');
      }
      
      throw new Error(errorMessage);
    }

    const results = await response.json();
    return results;
  }

  _showTimeoutMessage() {
    let messageBox = document.getElementById('ethical-analysis-timeout-message');
    if (!messageBox) {
      messageBox = document.createElement('div');
      messageBox.id = 'ethical-analysis-timeout-message';
      messageBox.style.cssText = `
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: white;
        border: 1px solid #ccc;
        border-radius: 8px;
        padding: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,.15);
        z-index: 10000;
        max-width: 400px;
        font: 13px/1.4 var(--font-ui, inherit);
        font-family: inherit;
      `;
      
      messageBox.innerHTML = `
        <div style="margin-bottom: 12px;">
          <h4 style="margin: 0 0 8px; font-size: 16px; border-bottom: 1px solid #eee; padding-bottom: 6px; color: #2c3e50;">
            Analysis in Progress
          </h4>
        </div>
        <p style="margin: 0 0 12px; line-height: 1.4;">
          Your ethical analysis request is taking longer than expected to complete. 
          This is normal for complex processes and multiple analysis techniques.
        </p>
        <p style="margin: 0 0 15px; line-height: 1.4; font-weight: bold; color: #666;">
          Please wait up to 30 minutes before refreshing the data. 
          The analysis will continue running in the background.
        </p>
        <div style="text-align: center;">
          <button id="ethical-analysis-timeout-close" style="
            background: #4caf50;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            transition: background-color 0.2s;
          " onmouseover="this.style.background='#45a049'" onmouseout="this.style.background='#4caf50'">
            OK, I understand
          </button>
        </div>
      `;
      
      document.body.appendChild(messageBox);
      
      document.getElementById('ethical-analysis-timeout-close').addEventListener('click', () => {
        this._clearTimeoutMessage();
        this._hideCreateLoading();
      });
    } else {
      messageBox.style.display = 'block';
    }
  }

  _clearTimeoutMessage() {
    const messageBox = document.getElementById('ethical-analysis-timeout-message');
    if (messageBox) {
      messageBox.remove();
    }
  }

  _hideCreateLoading() {
    const createLoader = document.querySelector('.loader-create');
    if (createLoader) {
      createLoader.style.display = 'none';
    }
    
    const mainLoader = document.querySelector('.loader');
    if (mainLoader) {
      mainLoader.style.display = 'none';
    }
    
    const selectFileBtn = document.querySelector('#select-file-btn');
    if (selectFileBtn) {
      selectFileBtn.disabled = false;
    }
  }

  _showSuccessMessage() {
    let successBox = document.getElementById('ethical-analysis-success-message');
    if (!successBox) {
      successBox = document.createElement('div');
      successBox.id = 'ethical-analysis-success-message';
      successBox.style.cssText = `
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: white;
        border: 1px solid #ccc;
        border-radius: 8px;
        padding: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,.15);
        z-index: 10000;
        max-width: 400px;
        font: 13px/1.4 var(--font-ui, inherit);
        font-family: inherit;
      `;
      
      successBox.innerHTML = `
        <div style="margin-bottom: 12px;">
          <h4 style="margin: 0 0 8px; font-size: 16px; border-bottom: 1px solid #eee; padding-bottom: 6px; color: #2c3e50;">
            ✓ Analysis Complete
          </h4>
        </div>
        <p style="margin: 0 0 15px; line-height: 1.4;">
          Your ethical analysis has been completed successfully! 
          You can now refresh the data to view the results.
        </p>
        <div style="text-align: center;">
          <button id="ethical-analysis-success-close" style="
            background: #4caf50;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            transition: background-color 0.2s;
          " onmouseover="this.style.background='#45a049'" onmouseout="this.style.background='#4caf50'">
            OK
          </button>
        </div>
      `;
      
      document.body.appendChild(successBox);
      
      setTimeout(() => {
        this._clearSuccessMessage();
      }, 5000);
      
      document.getElementById('ethical-analysis-success-close').addEventListener('click', () => {
        this._clearSuccessMessage();
      });
    } else {
      successBox.style.display = 'block';
    }
  }

  _clearSuccessMessage() {
    const successBox = document.getElementById('ethical-analysis-success-message');
    if (successBox) {
      successBox.remove();
    }
  }

  getAvailableProcessIds() {
    return this._availableProcessIds;
  }
}

export default {
  __init__: ['dataService'],
  dataService: ['type', DataService],
};
