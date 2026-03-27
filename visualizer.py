

"""
Owlapy Graph Visualizer
----------------------
This script reads a graph from 'owlapy_graph.json' and generates an interactive HTML visualization
using vis-network.js. The output is written to 'owlapy_graph_visualization.html'.
"""

import json
import os

def load_graph(json_path):
    """
    Load the graph data from a JSON file.
    Args:
        json_path (str): Path to the JSON file.
    Returns:
        tuple: (nodes dict, edges list)
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    nodes = data.get("nodes", {})
    edges = data.get("edges", [])
    return nodes, edges

def prepare_nodes(nodes):
    """
    Prepare node list and mapping for visualization.
    Args:
        nodes (dict): Node data from JSON.
    Returns:
        tuple: (node_list, node_id_map)
    """
    node_list = []
    node_id_map = {}
    for idx, (node_id, node_data) in enumerate(nodes.items()):
        node_id_map[node_id] = idx
        label = node_id.split(":")[-1]
        file = node_id.split(":")[0]
        node_list.append({
            "id": idx,
            "label": f"{label}\n({file})",
            "title": json.dumps(node_data, indent=2),
            "shape": "dot",
            "size": 15
        })
    return node_list, node_id_map

def prepare_edges(edges, node_id_map):
    """
    Prepare edge list for visualization.
    Args:
        edges (list): Edge data from JSON.
        node_id_map (dict): Mapping from node_id to index.
    Returns:
        list: List of edge dicts for visualization.
    """
    edge_list = []
    for edge in edges:
        src = edge.get('source_id')
        tgt = edge.get('target_id')
        if src in node_id_map and tgt in node_id_map:
            edge_list.append({
                "from": node_id_map[src],
                "to": node_id_map[tgt]
            })
    return edge_list

def generate_html(node_list, edge_list, output_html):
    """
    Generate the HTML visualization file.
    Args:
        node_list (list): List of node dicts.
        edge_list (list): List of edge dicts.
        output_html (str): Output HTML file path.
    """
    html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Owlapy Graph Visualization</title>
    <meta charset=\"utf-8\">
    <script type=\"text/javascript\" src=\"https://unpkg.com/vis-network@9.1.2/dist/vis-network.min.js\"></script>
    <link href=\"https://unpkg.com/vis-network@9.1.2/dist/vis-network.min.css\" rel=\"stylesheet\" type=\"text/css\" />
    <style>
        #mynetwork {{
            width: 100vw;
            height: 90vh;
            background: #222;
            border: 1px solid lightgray;
        }}
        #controls {{
            margin: 10px;
            color: white;
        }}
        body {{ background: #222; color: white; }}
        label {{ color: white; }}
    </style>
</head>
<body>
    <div id=\"controls\">
        <label for=\"sizeSlider\">Number of nodes to display:</label>
        <input type=\"range\" id=\"sizeSlider\" min=\"10\" max=\"{len(node_list)}\" value=\"50\" step=\"1\" oninput=\"updateGraph()\">
        <span id=\"sliderValue\">50</span> / {len(node_list)}
        <button onclick=\"showAll()\">Show All</button>
    </div>
    <div id=\"mynetwork\"></div>
    <script type=\"text/javascript\">
        // All nodes and edges from Python
        const allNodes = {json.dumps(node_list)};
        const allEdges = {json.dumps(edge_list)};
        let network = null;

        // Update the graph based on slider value
        function updateGraph() {{
            const slider = document.getElementById('sizeSlider');
            const n = parseInt(slider.value);
            document.getElementById('sliderValue').innerText = n;
            // Only show nodes/edges up to n
            const nodes = allNodes.slice(0, n);
            // Only show edges where both nodes are in the current set
            const nodeIds = new Set(nodes.map(x => x.id));
            const edges = allEdges.filter(e => nodeIds.has(e.from) && nodeIds.has(e.to));
            const data = {{ nodes: new vis.DataSet(nodes), edges: new vis.DataSet(edges) }};
            const options = {{
                nodes: {{ color: {{ background: '#97C2FC', border: '#2B7CE9' }} }},
                edges: {{ color: '#AAAAAA' }},
                physics: {{ enabled: true, stabilization: false }},
                layout: {{ improvedLayout: true }}
            }};
            if (network) network.destroy();
            network = new vis.Network(document.getElementById('mynetwork'), data, options);
        }}

        // Show all nodes/edges
        function showAll() {{
            document.getElementById('sizeSlider').value = allNodes.length;
            updateGraph();
        }}

        // Initial draw
        updateGraph();
    </script>
</body>
</html>
    """
    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html_template)

def main():
    """
    Main function to generate the graph visualization HTML.
    """
    graph_json_path = "owlapy_graph.json"
    output_html = "owlapy_graph_visualization.html"

    # Load graph data
    nodes, edges = load_graph(graph_json_path)

    # Prepare nodes and edges for visualization
    node_list, node_id_map = prepare_nodes(nodes)
    edge_list = prepare_edges(edges, node_id_map)

    # Generate HTML visualization
    generate_html(node_list, edge_list, output_html)

    print(f"Visualization generated: {os.path.abspath(output_html)}")

if __name__ == "__main__":
    main()
