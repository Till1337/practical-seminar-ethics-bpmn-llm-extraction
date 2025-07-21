const fs = require('fs-extra');
const path = require('path');

const projectRoot = path.resolve(__dirname, '..');
const pluginFiles = [
  'package.json',
  'index.js',
  'menu.js',
  'build/plugin/client.js',
  'plugin.css',
  'client/resources'
];

function getModelerPluginsPath() {
  const home = process.env.HOME || process.env.USERPROFILE;
  switch (process.platform) {
    case 'darwin':
      return path.join(home, 'Library/Application Support/camunda-modeler/resources/plugins');
    case 'win32':
      return path.join(home, 'AppData/Roaming/camunda-modeler/resources/plugins');
    case 'linux':
      return path.join(home, '.config/camunda-modeler/resources/plugins');
    default:
      throw new Error('Platform not supported.');
  }
}

async function deploy() {
  try {
    const modelerPluginsPath = getModelerPluginsPath();
    const targetDir = path.join(modelerPluginsPath, 'ethical-heatmap-plugin');

    console.log(`Deploying plugin to: ${targetDir}`);

    await fs.emptyDir(targetDir);

    for (const file of pluginFiles) {
      let sourcePath = path.join(projectRoot, file);
      let destFile;
      if (file === 'build/plugin/client.js') {
        destFile = 'client.js';
      } else if (file === 'client/resources') {
        destFile = 'resources';
      } else {
        destFile = file;
      }
      let destPath = path.join(targetDir, destFile);
      if (await fs.pathExists(sourcePath)) {
        await fs.copy(sourcePath, destPath);
        console.log(`Copied: ${file}`);
      } else {
        console.warn(`Warning: Source file not found: ${sourcePath}`);
      }
    }

    console.log('\nPlugin deployed successfully!');
    console.log('Please restart Camunda Modeler to see the changes.');

  } catch (err) {
    console.error('Error during deployment:', err);
    process.exit(1);
  }
}

deploy();
