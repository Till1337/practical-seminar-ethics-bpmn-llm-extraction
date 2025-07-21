import { domify, delegate } from 'min-dom';
import h337 from 'heatmap.js';

import { generateFlowHeatPoints, isTaskElement, getElementProcess } from './HeatmapGenerator';
import FilePicker from './FilePicker';

const DEFAULTS = {
  PROMPTING_STRATEGY: 'zero_shot',
  ETHICAL_VALUE: 'responsibility',
};

const ALL_PROMPTING_TECHNIQUES = [
  { value: 'zero_shot', label: 'Zero-Shot' },
  { value: 'few_shot', label: 'Few-Shot' },
  { value: 'contrastive_cot', label: 'Contrastive CoT' },
  { value: 'universal_self_consistency', label: 'Universal Self-Consistency' },
  { value: 'chain_of_verification', label: 'Chain of Verification' },
  { value: 'tree_of_thoughts', label: 'Tree of Thoughts' }
];

const ALL_ETHICAL_VALUES = [
  { value: 'transparency', label: 'Transparency' },
  { value: 'responsibility', label: 'Responsibility' },
  { value: 'accountability', label: 'Accountability' },
  { value: 'fairness', label: 'Fairness' },
  { value: 'well_being', label: 'Well-being' },
  { value: 'human_autonomy', label: 'Human Autonomy' },
  { value: 'solidarity', label: 'Solidarity' },
  { value: 'diversity_and_inclusion', label: 'Diversity & Inclusion' },
  { value: 'privacy', label: 'Privacy' },
  { value: 'sustainability', label: 'Sustainability' },
  { value: 'trust', label: 'Trust' }
];

const HEATMAP_CONFIG = {
  maxOpacity: 0.75,
  minOpacity: 0.05,
  blur: 0.85,
  gradient: {
    0.1: 'rgba(0, 100, 255, 0.2)',
    0.3: 'royalblue',
    0.5: 'cyan',
    0.7: '#39ff14',
    0.85: 'yellow',
    0.95: 'orange',
    1.0: '#ff1100',
  },
};

const TRAFFIC_LIGHT_CONFIG = {
  RED: { min: 1, max: 2, color: '#ff0000', label: 'Poor' },
  YELLOW: { min: 2.1, max: 3.5, color: '#ffff00', label: 'Adequate' },
  GREEN: { min: 3.6, max: 5, color: '#00ff00', label: 'Good' }
};

function getTrafficLightIndicator(score) {
  if (typeof score !== 'number' || score < 1 || score > 5) {
    return { color: '#999999', label: 'N/A', symbol: '○' };
  }
  
  if (score >= TRAFFIC_LIGHT_CONFIG.GREEN.min && score <= TRAFFIC_LIGHT_CONFIG.GREEN.max) {
    return { 
      color: TRAFFIC_LIGHT_CONFIG.GREEN.color, 
      label: TRAFFIC_LIGHT_CONFIG.GREEN.label, 
      symbol: '●' 
    };
  } else if (score >= TRAFFIC_LIGHT_CONFIG.YELLOW.min && score <= TRAFFIC_LIGHT_CONFIG.YELLOW.max) {
    return { 
      color: TRAFFIC_LIGHT_CONFIG.YELLOW.color, 
      label: TRAFFIC_LIGHT_CONFIG.YELLOW.label, 
      symbol: '●' 
    };
  } else {
    return { 
      color: TRAFFIC_LIGHT_CONFIG.RED.color, 
      label: TRAFFIC_LIGHT_CONFIG.RED.label, 
      symbol: '●' 
    };
  }
}

function HeatmapModule(eventBus, canvas, elementRegistry, editorActions, dataService) {
  this._eventBus = eventBus;
  this._canvas = canvas;
  this._elementRegistry = elementRegistry;
  this._editorActions = editorActions;
  this._dataService = dataService;

  this._isOn = false;
  this._heatmap = null;
  this._heatmapLayer = null;
  this._ui = {};
  this._isLoading = false;

  this._selectedProcessId = null;
  this._selectedEthical = DEFAULTS.ETHICAL_VALUE;
  this._promptingStrategy = DEFAULTS.PROMPTING_STRATEGY;
  this._ethicalData = null;
  this._judgeData = null;

  this._filePicker = new FilePicker((fileData) => {
    this._handleFileSelection(fileData);
  });

  editorActions.register('toggleEthicalHeatmap', () => {
    this._toggle();
  });

  editorActions.register('refreshEthicalData', () => {
    this._refreshData();
  });

  eventBus.on('import.done', () => this._init());
}

HeatmapModule.$inject = ['eventBus', 'canvas', 'elementRegistry', 'editorActions', 'dataService'];

HeatmapModule.prototype._init = function () {
  this._addUI();
  this._bindEvents();
  this._populateProcesses();
  this._updateUIState();
};

HeatmapModule.prototype._addUI = function () {
  const container = this._canvas.getContainer();

  this._ui.toggleButton = domify(`
    <button class="ethical-heatmap-toggle-btn" title="Toggle ethical heatmap">
      <span class="heatmap-icon"></span> Ethical Heatmap
    </button>`);

  const promptingOptions = ALL_PROMPTING_TECHNIQUES.map(tech => 
    `<option value="${tech.value}">${tech.label}</option>`
  ).join('');

  const ethicalOptions = ALL_ETHICAL_VALUES.map(value => 
    `<option value="${value.value}">${value.label}</option>`
  ).join('');

  this._ui.panel = domify(`
    <div class="heatmap-panel" style="display: none;">
      <div class="heatmap-panel-row">
        <label for="process-select">Process:</label>
        <select id="process-select"></select>
        <div class="loader" style="display: none;"></div>
      </div>
      <div class="standard-controls">
        <div class="heatmap-panel-row">
          <label for="prompting-strategy-select">Prompting Technique:</label>
          <select id="prompting-strategy-select">
            ${promptingOptions}
          </select>
        </div>
        <div class="heatmap-panel-row">
          <label for="ethical-value-select">Ethical Value:</label>
          <select id="ethical-value-select">
            ${ethicalOptions}
          </select>
        </div>
        <div class="data-status" id="data-status"></div>
        <div class="heatmap-panel-row legend">
          <div class="legend-item">
            <span>Low</span>
            <div class="gradient-bar"></div>
            <span>High</span>
          </div>
        </div>
      </div>
      <hr class="divider" />
      <div class="heatmap-panel-row create-analysis-section">
        <label>Create new analysis:</label>
        <p class="description-help">Select a BPMN file to generate a new heatmap analysis.</p>
        <button id="select-file-btn">Select BPMN File</button>
        <div class="loader-create" style="display: none;"></div>
      </div>
      <div class="heatmap-panel-row refresh-section" style="display: none;">
        <p class="success-message">Analysis created successfully!</p>
        <button id="refresh-data-btn-success">Refresh Data</button>
      </div>
    </div>`);

  this._ui.tooltip = domify('<div class="heatmap-tooltip"></div>');

  container.appendChild(this._ui.toggleButton);
  container.appendChild(this._ui.panel);
  container.appendChild(this._ui.tooltip);
};

HeatmapModule.prototype._bindEvents = function () {
  this._ui.toggleButton.onclick = () => this._toggle();

  this._ui.panel.querySelector('#process-select').onchange = (e) => {
    this._selectedProcessId = e.target.value;
    this._loadDataForProcess(this._selectedProcessId);
  };
  this._ui.panel.querySelector('#prompting-strategy-select').onchange = (e) => {
    this._promptingStrategy = e.target.value;
    this._updateEthicalValueOptions();
    this._render();
  };
  this._ui.panel.querySelector('#ethical-value-select').onchange = (e) => {
    this._selectedEthical = e.target.value;
    this._render();
  };

  this._ui.panel.querySelector('#select-file-btn').onclick = () => {
    this._filePicker.show();
  };
  this._ui.panel.querySelector('#refresh-data-btn-success').onclick = () => {
    this._refreshData();
  };

  const container = this._canvas.getContainer();
  delegate.bind(container, '.djs-element:not(.djs-connection)', 'mouseover', (e) => {
    if (!this._isOn) return;
    const el = this._elementRegistry.get(e.delegateTarget.dataset.elementId);
    if (el && isTaskElement(el)) this._showTip(el, e);
  });
  delegate.bind(container, '.djs-element:not(.djs-connection)', 'mouseout', () => this._hideTip());
  delegate.bind(container, '.djs-element:not(.djs-connection)', 'mousemove', (e) => {
    if (this._ui.tooltip.style.display === 'block') this._moveTip(e);
  });

  const debouncedRender = () => {
    if (this._isOn) {
      setTimeout(() => this._render(), 50);
    }
  };
  this._eventBus.on(['elements.changed', 'canvas.viewbox.changed'], debouncedRender);
  this._eventBus.on('import.done', () => this._populateProcesses());
};

HeatmapModule.prototype._setLoading = function (loading, type = 'main') {
  this._isLoading = loading;
  const loader = type === 'create' ? this._ui.panel.querySelector('.loader-create') : this._ui.panel.querySelector('.loader');
  const button = type === 'create' ? this._ui.panel.querySelector('#select-file-btn') : null;
  const statusElement = this._ui.panel.querySelector('#data-status');

  if (loader) {
    loader.style.display = loading ? 'inline-block' : 'none';
  }
  if (button) {
    button.disabled = loading;
  }
  if (statusElement) {
    if (loading) {
      statusElement.textContent = 'Loading data...';
      statusElement.className = 'data-status loading';
    } else {
      statusElement.textContent = '';
      statusElement.className = 'data-status';
    }
  }
};

HeatmapModule.prototype._updateDataStatus = function (dataSource, hasData) {
  const statusElement = this._ui.panel.querySelector('#data-status');
  if (!statusElement) return;

  if (!hasData) {
    statusElement.textContent = 'No data available';
    statusElement.className = 'data-status error';
  } else if (dataSource === 'api') {
    statusElement.textContent = 'Data from API';
    statusElement.className = 'data-status success';
  } else if (dataSource === 'local') {
    statusElement.textContent = 'Data from local files';
    statusElement.className = 'data-status';
  } else {
    statusElement.textContent = '';
    statusElement.className = 'data-status';
  }
};

HeatmapModule.prototype._refreshData = async function () {
  if (!this._selectedProcessId) {
    alert('Please select a process first.');
    return;
  }

  this._dataService._apiDataCache.delete(this._selectedProcessId);
  this._dataService._apiJudgeDataCache.delete(this._selectedProcessId);

  this._setLoading(true);
  try {
    await this._loadDataForProcess(this._selectedProcessId);
  } catch (error) {
    console.error('Failed to refresh data:', error);
    alert('Failed to refresh data. Please check the console for details.');
  } finally {
    this._setLoading(false);
  }
};

HeatmapModule.prototype._loadDataForProcess = async function (processId) {
  if (!processId) {
    this._ethicalData = null;
    this._judgeData = null;
    this._updatePanelLayout();
    this._updateEthicalValueOptions();
    this._updatePromptingTechniqueOptions();
    this._updateDataStatus(null, false);
    this._render();
    return;
  }

  this._setLoading(true);
  let dataSource = null;
  let hasData = false;
  
  try {
    this._ethicalData = await this._dataService.getEthicalDataForModel(processId);
    this._judgeData = await this._dataService.getJudgeDataForModel(processId);
    
    hasData = this._ethicalData && this._ethicalData.ethicalAnalysis && Object.keys(this._ethicalData.ethicalAnalysis).length > 0;
    
    if (hasData) {
      if (this._dataService._apiDataCache.has(processId)) {
        dataSource = 'api';
      } else {
        dataSource = 'local';
      }
    }
  } catch (error) {
    console.error('Failed to load data for process', processId, error);
    alert(`Failed to load analysis data from the API. Please ensure the API is running and accessible at ${this._dataService.API_BASE_URL}.`);
    this._ethicalData = null;
    this._judgeData = null;
  } finally {
    this._updatePanelLayout();
    this._updateEthicalValueOptions();
    this._updatePromptingTechniqueOptions();
    this._updateDataStatus(dataSource, hasData);
    this._render();
    this._setLoading(false);
  }
};

HeatmapModule.prototype._populateProcesses = function () {
  const processSelect = this._ui.panel.querySelector('#process-select');
  processSelect.innerHTML = '';

  const rootElements = this._canvas.getRootElement().businessObject.$parent.rootElements || [];
  const collaborations = rootElements.filter(root => root.$type === 'bpmn:Collaboration');
  let processes = [];

  if (collaborations.length > 0) {
    processes = collaborations.flatMap(collab => (collab.participants || []).map(p => p.processRef).filter(Boolean));
  } else {
    processes = rootElements.filter(root => root.$type === 'bpmn:Process');
  }

  const uniqueProcesses = Array.from(new Map(processes.map(p => [p.id, p])).values());

  if (uniqueProcesses.length > 0) {
    uniqueProcesses.forEach((p) => {
      const participant = this._elementRegistry.find((part) => part.type === 'bpmn:Participant' && part.businessObject.processRef === p);
      const name = participant ? `${participant.businessObject.name} (${p.id})` : p.id;
      const displayName = name.length > 35 ? `${name.slice(0, 32)}...` : name;
      const option = domify(`<option value="${p.id}" title="${name}">${displayName}</option>`);
      processSelect.appendChild(option);
    });

    const firstProcessId = uniqueProcesses.length > 0 ? uniqueProcesses[0].id : null;
    const currentSelectedExists = uniqueProcesses.some((p) => p.id === this._selectedProcessId);

    if (!this._selectedProcessId || !currentSelectedExists) {
      this._selectedProcessId = firstProcessId;
    }

    processSelect.value = this._selectedProcessId;
    this._loadDataForProcess(this._selectedProcessId);
  }
};

HeatmapModule.prototype._updateUIState = function () {
  this._ui.toggleButton.classList.toggle('active', this._isOn);
  this._ui.panel.style.display = this._isOn ? 'block' : 'none';

  if (this._isOn) {
    this._updatePanelLayout();
  }
};

HeatmapModule.prototype._updatePanelLayout = function () {
  const hasData = this._ethicalData && this._ethicalData.ethicalAnalysis && Object.keys(this._ethicalData.ethicalAnalysis).length > 0;
  const standardControls = this._ui.panel.querySelector('.standard-controls');
  const createAnalysisSection = this._ui.panel.querySelector('.create-analysis-section');

  if (hasData) {
    standardControls.style.display = 'block';
    createAnalysisSection.style.display = 'none';
  } else {
    standardControls.style.display = 'none';
    createAnalysisSection.style.display = 'flex';
  }

  const refreshSection = this._ui.panel.querySelector('.refresh-section');
  refreshSection.style.display = 'none';
};

HeatmapModule.prototype._updateEthicalValueOptions = function () {
  const ethicalValueSelect = this._ui.panel.querySelector('#ethical-value-select');
  const currentEthicalValue = this._selectedEthical;
  const availableValues = new Set();

  if (this._ethicalData && this._ethicalData.ethicalAnalysis) {
    const analysis = this._ethicalData.ethicalAnalysis[this._promptingStrategy];
    if (analysis) {
      for (const taskName in analysis) {
        for (const ethicalValue in analysis[taskName]) {
          availableValues.add(ethicalValue);
        }
      }
    }
  }

  for (const option of ethicalValueSelect.options) {
    const isAvailable = availableValues.size === 0 || availableValues.has(option.value);
    option.disabled = !isAvailable;
    
    if (option.disabled) {
      option.style.color = '#999';
      option.style.fontStyle = 'italic';
    } else {
      option.style.color = '';
      option.style.fontStyle = '';
    }
  }

  const currentOption = ethicalValueSelect.querySelector(`option[value="${currentEthicalValue}"]`);
  if (!this._selectedEthical || (currentOption && currentOption.disabled)) {
    const firstEnabledOption = ethicalValueSelect.querySelector('option:not([disabled])');
    if (firstEnabledOption) {
      this._selectedEthical = firstEnabledOption.value;
      ethicalValueSelect.value = this._selectedEthical;
    } else {
      this._selectedEthical = null;
      ethicalValueSelect.value = '';
    }
  }
};

HeatmapModule.prototype._updatePromptingTechniqueOptions = function () {
  const promptingSelect = this._ui.panel.querySelector('#prompting-strategy-select');
  const currentStrategy = this._promptingStrategy;
  const availableTechniques = new Set();

  if (this._ethicalData && this._ethicalData.ethicalAnalysis) {
    for (const technique in this._ethicalData.ethicalAnalysis) {
      const analysis = this._ethicalData.ethicalAnalysis[technique];
      if (analysis && Object.keys(analysis).length > 0) {
        availableTechniques.add(technique);
      }
    }
  }

  for (const option of promptingSelect.options) {
    const isAvailable = availableTechniques.size === 0 || availableTechniques.has(option.value);
    option.disabled = !isAvailable;
    
    if (option.disabled) {
      option.style.color = '#999';
      option.style.fontStyle = 'italic';
    } else {
      option.style.color = '';
      option.style.fontStyle = '';
    }
  }

  const currentOption = promptingSelect.querySelector(`option[value="${currentStrategy}"]`);
  if (currentOption && currentOption.disabled) {
    const firstEnabledOption = promptingSelect.querySelector('option:not([disabled])');
    if (firstEnabledOption) {
      this._promptingStrategy = firstEnabledOption.value;
      promptingSelect.value = this._promptingStrategy;
    }
  }
};

HeatmapModule.prototype._toggle = function () {
  this._isOn = !this._isOn;
  this._ui.toggleButton.classList.toggle('active', this._isOn);
  this._ui.panel.style.display = this._isOn ? 'block' : 'none';

  if (this._isOn) {
    this._ensureHeatmap();
    this._populateProcesses();
    this._updateUIState();
    this._render();
  } else {
    this._destroyHeatmap();
  }
};

HeatmapModule.prototype._ensureHeatmap = function () {
  if (this._heatmap) return;

  this._heatmapLayer = domify('<div class="ethical-heatmap-layer"></div>');
  this._canvas.getContainer().appendChild(this._heatmapLayer);

  this._heatmap = h337.create({
    container: this._heatmapLayer,
    ...HEATMAP_CONFIG,
  });
};

HeatmapModule.prototype._destroyHeatmap = function () {
  if (this._heatmapLayer) {
    this._heatmapLayer.remove();
    this._heatmapLayer = null;
    this._heatmap = null;
  }
};

HeatmapModule.prototype._render = function () {
  if (!this._isOn || !this._heatmap || this._isLoading) {
    if (this._heatmap) {
      this._heatmap.setData({ max: 1, min: 0, data: [] });
    }
    return;
  }

  const { width, height } = this._canvas.getContainer().getBoundingClientRect();

  this._heatmapLayer.style.width = `${width}px`;
  this._heatmapLayer.style.height = `${height}px`;

  const renderer = this._heatmap._renderer;
  if (renderer.canvas.width !== width || renderer.canvas.height !== height) {
    renderer.setDimensions(width, height);
  }

  const dataPoints = generateFlowHeatPoints(this._elementRegistry, {
    canvas: this._canvas,
    promptingStrategy: this._promptingStrategy,
    selectedEthical: this._selectedEthical,
    selectedProcessId: this._selectedProcessId,
    ethicalData: this._ethicalData,
  });

  const maxVal = 6.0;
  this._heatmap.setData({ max: maxVal, min: 0, data: dataPoints });
};

HeatmapModule.prototype._showTip = function (el, event) {
  const process = getElementProcess(el);
  if (!process || process.id !== this._selectedProcessId || !this._ethicalData) {
    return this._hideTip();
  }

  const stepName = el.businessObject.name;
  if (!stepName) return this._hideTip();

  const stepEthics = this._ethicalData?.ethicalAnalysis?.[this._promptingStrategy]?.[stepName];
  if (!stepEthics) {
    return this._hideTip();
  }

  const valueObj = stepEthics[this._selectedEthical];
  if (!valueObj) return this._hideTip();

  const score = valueObj.score;
  const explanation = valueObj.explanation || 'No explanation available.';
  const cls = score > 7 ? 'high' : score > 4 ? 'medium' : 'low';

  let judgeScoreText = '';
  if (this._judgeData && this._judgeData[this._promptingStrategy]) {
    const stepEval = this._judgeData[this._promptingStrategy].step_evaluations.find(
      (evaluation) => evaluation.step_name === stepName
    );
    if (stepEval && typeof stepEval.score === 'number') {
      const trafficLight = getTrafficLightIndicator(stepEval.score);
      judgeScoreText = `<p>Judge Score: <span class="score" style="color: ${trafficLight.color}; background: rgba(${trafficLight.color === '#ff0000' ? '255,0,0' : trafficLight.color === '#ffff00' ? '255,255,0' : trafficLight.color === '#00ff00' ? '0,255,0' : '153,153,153'}, 0.2);">${trafficLight.symbol} ${trafficLight.label}</span></p>`;
    }
  }

  this._ui.tooltip.innerHTML = `
    <h4>${stepName}</h4>
    <p>Strategy: ${this._promptingStrategy}</p>
    <p>Risk (${this._selectedEthical}): <span class="score ${cls}">${score.toFixed(1)}</span></p>
    ${judgeScoreText}
    <hr>
    <p class="explanation"><b>Explanation:</b> ${explanation}</p>`;
  this._ui.tooltip.style.display = 'block';
  this._moveTip(event);
};

HeatmapModule.prototype._hideTip = function () {
  this._ui.tooltip.style.display = 'none';
};

HeatmapModule.prototype._moveTip = function (evt) {
  const containerBounds = this._canvas.getContainer().getBoundingClientRect();
  this._ui.tooltip.style.left = `${evt.clientX - containerBounds.left + 15}px`;
  this._ui.tooltip.style.top = `${evt.clientY - containerBounds.top + 15}px`;
};

HeatmapModule.prototype._handleFileSelection = async function (fileData) {
  if (!fileData || !fileData.bpmnXml) {
    alert('No BPMN content found in the selected file.');
    return;
  }

  this._setLoading(true, 'create');
  try {
    const result = await this._dataService.createAnalysis(
      fileData.fileName, 
      fileData.description,
      fileData.bpmnXml,
      fileData.processName
    );
    
    this._dataService._clearTimeoutMessage();
    this._dataService._showSuccessMessage();
    this._dataService._hideCreateLoading();
    
    this._ui.panel.querySelector('.create-analysis-section').style.display = 'none';
    this._ui.panel.querySelector('.refresh-section').style.display = 'flex';
    this._setLoading(false, 'create');
    this._populateProcesses();
  } catch (error) {
    console.error('Failed to create analysis:', error);
    
    this._dataService._clearTimeoutMessage();
    this._dataService._hideCreateLoading();
    
    this._setLoading(false, 'create');
    let errorMessage = 'Failed to create analysis.';
    if (error.message && error.message.includes('BPMN XML content is required')) {
      errorMessage = 'The selected file does not contain valid BPMN XML content.';
    } else if (error.message && error.message.includes('Could not extract BPMN XML')) {
      errorMessage = 'Could not process the selected file. Please ensure it contains valid BPMN XML.';
    } else {
      errorMessage = error.message || 'An unexpected error occurred while creating the analysis.';
    }
    alert(errorMessage);
  }
};

export default {
  __init__: ['heatmapModule'],
  heatmapModule: ['type', HeatmapModule],
};