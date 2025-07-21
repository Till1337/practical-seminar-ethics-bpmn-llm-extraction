import { domify } from 'min-dom';

class FilePicker {
  constructor(onFileSelect) {
    this.onFileSelect = onFileSelect;
    this._createUI();
  }

  _createUI() {
    this._container = domify(`
      <div class="file-picker-container">
        <div class="file-picker-modal">
          <div class="file-picker-header">
            <span class="file-picker-title">Choose BPMN file</span>
            <button class="file-picker-close" title="Close">×</button>
          </div>
          <div class="file-picker-content">
            <label class="file-picker-label" for="file-input">BPMN File:</label>
            <input type="file" id="file-input" accept=".bpmn,.xml" />
            <div class="file-info" style="display:none;"></div>
            <label class="file-picker-label" for="description-input" style="margin-top:10px;">Description (optional):</label>
            <textarea id="description-input" placeholder="Enter a description of the process..." rows="3"></textarea>
            <div class="file-picker-actions">
              <button class="file-picker-btn file-picker-btn-primary" id="analyze-btn" disabled>Analyze Process</button>
              <button class="file-picker-btn file-picker-btn-secondary" id="cancel-btn">Cancel</button>
            </div>
          </div>
        </div>
      </div>
    `);
    this._bindEvents();
  }

  _bindEvents() {
    const fileInput = this._container.querySelector('#file-input');
    const descriptionInput = this._container.querySelector('#description-input');
    const analyzeBtn = this._container.querySelector('#analyze-btn');
    const cancelBtn = this._container.querySelector('#cancel-btn');
    const closeBtn = this._container.querySelector('.file-picker-close');

    fileInput.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (file) {
        this._validateAndReadFile(file);
      } else {
        this._selectedFile = null;
        this._updateAnalyzeButton();
        this._showFileInfo();
      }
    });

    descriptionInput.addEventListener('input', () => {
      this._updateAnalyzeButton();
    });

    analyzeBtn.addEventListener('click', () => {
      this._handleAnalyze();
    });

    cancelBtn.addEventListener('click', () => {
      this.hide();
    });

    closeBtn.addEventListener('click', () => {
      this.hide();
    });
  }

  _validateAndReadFile(file) {
    if (!file.name.toLowerCase().endsWith('.bpmn') && !file.name.toLowerCase().endsWith('.xml')) {
      alert('Please select a valid BPMN file (.bpmn or .xml)');
      this._selectedFile = null;
      this._updateAnalyzeButton();
      this._showFileInfo();
      return;
    }
    const reader = new FileReader();
    reader.onload = (e) => {
      const content = e.target.result;
      this._selectedFile = {
        name: file.name,
        content: content,
        size: file.size
      };
      this._updateAnalyzeButton();
      this._showFileInfo();
    };
    reader.onerror = () => {
      alert('Error reading file. Please try again.');
      this._selectedFile = null;
      this._updateAnalyzeButton();
      this._showFileInfo();
    };
    reader.readAsText(file);
  }

  _showFileInfo() {
    const fileInfo = this._container.querySelector('.file-info');
    if (!this._selectedFile) {
      fileInfo.style.display = 'none';
      fileInfo.innerHTML = '';
      return;
    }
    fileInfo.style.display = 'block';
    fileInfo.innerHTML = `
      <div class="file-info-item"><strong>File:</strong> ${this._selectedFile.name}</div>
      <div class="file-info-item"><strong>Size:</strong> ${(this._selectedFile.size / 1024).toFixed(1)} KB</div>
    `;
  }

  _updateAnalyzeButton() {
    const analyzeBtn = this._container.querySelector('#analyze-btn');
    analyzeBtn.disabled = !this._selectedFile;
  }

  _handleAnalyze() {
    if (!this._selectedFile) {
      alert('Please select a file first.');
      return;
    }
    const descriptionInput = this._container.querySelector('#description-input');
    const description = descriptionInput.value.trim() || 'BPMN diagram analysis';
    
    let processId = null;
    let processName = null;
    try {
      const parser = new DOMParser();
      const xmlDoc = parser.parseFromString(this._selectedFile.content, 'text/xml');
      const processElem = xmlDoc.querySelector('bpmn\\:process, process');
      if (processElem && processElem.getAttribute('id')) {
        processId = processElem.getAttribute('id');
        processName = processId.replace(/_\d+$/, '');
        if (processName === processId) {
          processName = processId.replace(/[0-9]+$/, '');
        }
        if (processName === processId) {
          processName = 'Process';
        }
      }
    } catch (e) {
      // Ignore parsing errors, use fallback
    }
    if (!processId) {
      processId = this._selectedFile.name.replace(/\.(bpmn|xml)$/i, '');
      processName = processId;
    }
    
    this.onFileSelect({
      processName: processName,
      fileName: processId,
      description: description,
      bpmnXml: this._selectedFile.content
    });
    this.hide();
  }

  show() {
    const existing = document.querySelector('.file-picker-container');
    if (existing) {
      existing.remove();
    }
    document.body.appendChild(this._container);
    this._container.querySelector('#file-input').value = '';
    this._container.querySelector('#description-input').value = '';
    this._selectedFile = null;
    this._updateAnalyzeButton();
    this._showFileInfo();
  }

  hide() {
    if (this._container.parentNode) {
      this._container.parentNode.removeChild(this._container);
    }
  }
}

export default FilePicker; 