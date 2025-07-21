/**
 * Ethical Heatmap Plugin for Camunda Modeler
 * Visualizes ethical risks and values on BPMN diagrams
 */
module.exports = {
  name: 'Ethical Values Heatmap',
  script: './client.js',
  style: './plugin.css',
  menu: './menu.js', 
  type: 'bpmn'
};