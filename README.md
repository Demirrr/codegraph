# CodeGraph Visualization

This project visualizes the CodeGraph framework using an interactive HTML interface. The graph dynamically displays nodes and edges, with nodes colored based on their type (`kind`) and labeled with their `qualified_name`.

## Features
- **Dynamic Node Movement**: Nodes move dynamically, creating an engaging visualization.
- **Node Coloring**: Nodes are colored based on their type (`kind`).
- **Interactive Details**: Click on a node to view its details.

## How to use Preview
```bash
git clone https://github.com/dice-group/owlapy
python construct.py owlapy
python visualizer.py
# open codegraph_visualization.html on a browser
```

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