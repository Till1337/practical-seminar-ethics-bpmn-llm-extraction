import { registerBpmnJSPlugin } from 'camunda-modeler-plugin-helpers';
import EthicalHeatmapModule from './EthicalHeatmapModule';
import DataService from './DataService';
import './styles/plugin.css';

registerBpmnJSPlugin({
  __init__: ['heatmapModule', 'dataService'],
  heatmapModule: EthicalHeatmapModule.heatmapModule,
  dataService: DataService.dataService,
});