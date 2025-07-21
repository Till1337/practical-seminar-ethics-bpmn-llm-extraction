const path = require('path');

module.exports = {
  entry: './client/index.js',
  output: {
    path: path.resolve(__dirname, 'build/plugin'),
    filename: 'client.js',
    library: 'EthicalHeatmapPlugin',
    libraryTarget: 'umd',
    umdNamedDefine: true
  },
  module: {
    rules: [
      {
        test: /\.js$/,
        exclude: /node_modules/,
        use: {
          loader: 'babel-loader',
          options: {
            presets: ['@babel/preset-env']
          }
        }
      },
      {
        test: /\.css$/,
        use: ['style-loader', 'css-loader']
      },
      {
        test: /\.json$/,
        type: 'json'
      }
    ]
  },
  resolve: {
    extensions: ['.js', '.json']
  },
  devtool: 'source-map',
  stats: {
    modules: false,
    children: false,
    chunks: false,
    chunkModules: false,
    warnings: false,
    errors: true,
    errorDetails: false,
    assets: false,
    entrypoints: false,
    publicPath: false,
    timings: false,
    version: false,
    hash: false,
    builtAt: false,
    colors: true
  }
};