const TASK_ELEMENT_TYPES = [
  'bpmn:Task',
  'bpmn:UserTask',
  'bpmn:ServiceTask',
  'bpmn:BusinessRuleTask',
];

function isTaskElement(element) {
  return TASK_ELEMENT_TYPES.includes(element.type);
}

function getElementProcess(element) {
  let current = element;
  while (current.parent) {
    if (current.parent.type === 'bpmn:Process') {
      return current.parent;
    }
    if (current.parent.type === 'bpmn:Participant' && current.parent.businessObject.processRef) {
      return current.parent.businessObject.processRef;
    }
    current = current.parent;
  }
  return null;
}

function generateSmoothTaskHeatZone(center, bounds, score, points, zoomMultiplier) {
  const intensityMultiplier = Math.pow(score / 10, 2.5);
  const baseIntensity = 1.0 + score * 0.5;
  const baseRadiusX = Math.max(bounds.width, 60) * 0.7 * zoomMultiplier;
  const baseRadiusY = Math.max(bounds.height, 45) * 0.7 * zoomMultiplier;
  const baseGridSize = 12;
  const gridSize = Math.max(6, Math.min(18, Math.floor(baseGridSize * zoomMultiplier)));

  for (let i = 0; i < gridSize; i++) {
    for (let j = 0; j < gridSize; j++) {
      const u = (i / (gridSize - 1)) * 2 - 1;
      const v = (j / (gridSize - 1)) * 2 - 1;
      const distance = Math.sqrt(u * u + v * v);

      if (distance > 1) continue;

      const x = center.x + u * baseRadiusX;
      const y = center.y + v * baseRadiusY;
      const falloff = Math.pow(1 - distance, 2);
      const intensity = baseIntensity * intensityMultiplier * falloff;
      const jitterAmount = Math.max(3, 8 * zoomMultiplier);
      const pointRadius = Math.max(15, (25 + score * 2) * zoomMultiplier);

      points.push({
        x: Math.round(x + (Math.random() - 0.5) * jitterAmount),
        y: Math.round(y + (Math.random() - 0.5) * jitterAmount),
        value: Math.max(0.1, intensity),
        radius: pointRadius,
      });
    }
  }
}

function generateContinuousFlowCorridor(waypoints, sourceValue, targetValue, points, zoomMultiplier) {
  for (let i = 1; i < waypoints.length; i++) {
    const start = waypoints[i - 1];
    const end = waypoints[i];
    const distance = Math.hypot(end.x - start.x, end.y - start.y);

    if (distance === 0) continue;

    const baseStepDensity = 10;
    const stepDensity = Math.max(8, baseStepDensity * zoomMultiplier);
    const steps = Math.max(4, Math.floor(distance / stepDensity));

    for (let step = 0; step <= steps; step++) {
      const t = step / steps;
      const baseX = start.x + (end.x - start.x) * t;
      const baseY = start.y + (end.y - start.y) * t;
      const interpolatedScore = sourceValue + (targetValue - sourceValue) * t;
      const flowIntensity = 0.1 + (interpolatedScore / 10) * 0.4;
      const corridorWidth = Math.max(10, 20 * zoomMultiplier);
      const perpX = -(end.y - start.y) / distance;
      const perpY = (end.x - start.x) / distance;
      const offsetStep = Math.max(0.2, 0.3 / zoomMultiplier);

      for (let offset = -1; offset <= 1; offset += offsetStep) {
        const offsetX = perpX * corridorWidth * offset * 0.5;
        const offsetY = perpY * corridorWidth * offset * 0.5;
        const jitterAmount = Math.max(2, 4 * zoomMultiplier);
        const jitterX = (Math.random() - 0.5) * jitterAmount;
        const jitterY = (Math.random() - 0.5) * jitterAmount;
        const intensityModifier = Math.max(0.3, 1 - Math.abs(offset) * 0.4);

        points.push({
          x: Math.round(baseX + offsetX + jitterX),
          y: Math.round(baseY + offsetY + jitterY),
          value: Math.max(0.1, flowIntensity * intensityModifier),
          radius: Math.max(12, (20 + interpolatedScore * 1.5) * zoomMultiplier),
        });
      }
    }
  }
}

function generateSmoothFlowConnections(elementRegistry, taskData, points, viewbox, selectedProcessId) {
  elementRegistry.forEach((element) => {
    if (element.type !== 'bpmn:SequenceFlow') return;

    const sourceProcess = getElementProcess(element.source);
    if (!sourceProcess || sourceProcess.id !== selectedProcessId) return;

    const sourceData = taskData.get(element.source?.id);
    const targetData = taskData.get(element.target?.id);
    if (!sourceData || !targetData) return;

    const { zoomMultiplier } = sourceData;
    const waypoints = (element.waypoints || []).map((wp) => ({
      x: (wp.x - viewbox.x) * viewbox.scale,
      y: (wp.y - viewbox.y) * viewbox.scale,
    }));

    generateContinuousFlowCorridor(waypoints, sourceData.score, targetData.score, points, zoomMultiplier);
  });
}

function gatherTaskData(elementRegistry, config) {
  const {
    canvas,
    promptingStrategy,
    selectedEthical,
    selectedProcessId,
    ethicalData
  } = config;
  const taskData = new Map();
  if (!ethicalData) return taskData;

  const viewbox = canvas.viewbox();
  const zoomScale = Math.max(0.3, Math.min(2.0, viewbox.scale));
  const zoomMultiplier = Math.pow(zoomScale, 0.7);

  elementRegistry.forEach((element) => {
    if (!isTaskElement(element)) return;

    const process = getElementProcess(element);
    if (!process || process.id !== selectedProcessId) return;

    const stepName = element.businessObject.name;
    if (!stepName) return;

    const stepEthics = ethicalData?.ethicalAnalysis?.[promptingStrategy]?.[stepName];
    if (!stepEthics) return;

    const valueObj = stepEthics[selectedEthical];
    if (!valueObj || typeof valueObj.score !== 'number') return;

    const { x, y, width, height } = element;
    const screenX = (x - viewbox.x) * viewbox.scale;
    const screenY = (y - viewbox.y) * viewbox.scale;
    const screenWidth = width * viewbox.scale;
    const screenHeight = height * viewbox.scale;

    taskData.set(element.id, {
      score: Math.max(0.1, Math.min(10, valueObj.score)),
      center: {
        x: screenX + screenWidth / 2,
        y: screenY + screenHeight / 2,
      },
      element,
      bounds: { x: screenX, y: screenY, width: screenWidth, height: screenHeight },
      zoomMultiplier,
    });
  });

  return taskData;
}

export function generateFlowHeatPoints(elementRegistry, config) {
  if (!config.selectedProcessId) return [];

  const taskData = gatherTaskData(elementRegistry, config);
  if (taskData.size === 0) return [];

  const points = [];
  const viewbox = config.canvas.viewbox();

  generateSmoothFlowConnections(elementRegistry, taskData, points, viewbox, config.selectedProcessId);

  taskData.forEach((data) => {
    const { score, center, bounds, zoomMultiplier } = data;
    generateSmoothTaskHeatZone(center, bounds, score, points, zoomMultiplier);
  });

  return points;
}

export { isTaskElement, getElementProcess };
