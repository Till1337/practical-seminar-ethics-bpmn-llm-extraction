'use strict';

module.exports = function(electronApp, menuState) {
  return [{
    label: 'Toggle Ethical Heatmap',
    accelerator: 'CommandOrControl+Shift+E',
    enabled: function() {
      return menuState.bpmn;
    },
    action: function() {
      electronApp.emit('menu:action', 'toggleEthicalHeatmap');
    }
  }, {
    label: 'Refresh Ethical Data',
    accelerator: 'CommandOrControl+Shift+R',
    enabled: function() {
      return menuState.bpmn;
    },
    action: function() {
      electronApp.emit('menu:action', 'refreshEthicalData');
    }
  }];
};