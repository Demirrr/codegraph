# CodeGraph Visualization

This project visualizes the CodeGraph framework using an interactive HTML interface. The graph dynamically displays nodes and edges, with nodes colored based on their type (`kind`) and labeled with their `qualified_name`.

## Features
- **Dynamic Node Movement**: Nodes move dynamically, creating an engaging visualization.
- **Node Coloring**: Nodes are colored based on their type (`kind`).
- **Interactive Details**: Click on a node to view its details.

## Preview
![Graph Visualization](graph_preview.gif)

## How to Use
1. Run the `visualizer.py` script to generate the HTML file:
   ```bash
   python visualizer.py
   ```
2. Open the generated `codegraph_visualization.html` file in your browser.

## Generate Graph GIF
To generate a GIF of the graph visualization:
1. Install Puppeteer:
   ```bash
   npm install puppeteer
   ```
2. Run the Puppeteer script:
   ```bash
   node capture_graph.js
   ```
3. The GIF will be saved as `graph_preview.gif` in the project directory.

## Example
Below is a preview of the dynamic graph visualization:

![Graph Visualization](graph_preview.gif)
