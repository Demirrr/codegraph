import json
import os

graph_json_path = "owlapy_graph.json"
with open(graph_json_path, "r") as f:
    data = json.load(f)

nodes = data.get("nodes", {})
edges = data.get("edges", [])

# Define colors for different kinds of nodes
kind_colors = {
    "module": "#97C2FC",
    "function": "#FFA07A",
    "class": "#90EE90",
    "method": "#FFD700",
    "default": "#D3D3D3"
}

# Prepare node and edge lists for JS
node_list = []
node_id_map = {}
for idx, (node_id, node_data) in enumerate(nodes.items()):
    node_id_map[node_id] = idx
    label = node_data.get("qualified_name", node_id)
    kind = node_data.get("kind", "default")
    color = kind_colors.get(kind, kind_colors["default"])
    node_list.append({
        "id": idx,
        "label": label,
        "title": json.dumps(node_data, indent=2),
        "shape": "dot",
        "size": 15,
        "color": color
    })

edge_list = []
for edge in edges:
    src = edge.get('source_id')
    tgt = edge.get('target_id')
    if src in node_id_map and tgt in node_id_map:
        edge_list.append({
            "from": node_id_map[src],
            "to": node_id_map[tgt]
        })

output_html = "owlapy_graph_visualization.html"

html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Owlapy Graph Visualization</title>
    <meta charset="utf-8">
    <script type="text/javascript" src="https://unpkg.com/vis-network@9.1.2/dist/vis-network.min.js"></script>
    <link href="https://unpkg.com/vis-network@9.1.2/dist/vis-network.min.css" rel="stylesheet" type="text/css" />
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
        #nodeDetails {{
            position: absolute;
            top: 10px;
            right: 10px;
            width: 300px;
            max-height: 80vh;
            overflow-y: auto;
            background: #333;
            color: white;
            padding: 10px;
            border: 1px solid lightgray;
            border-radius: 5px;
            display: none;
        }}
        body {{ background: #222; color: white; }}
        label {{ color: white; }}
    </style>
</head>
<body>
    <div id="controls">
        <label for="sizeSlider">Number of nodes to display:</label>
        <input type="range" id="sizeSlider" min="10" max="{len(node_list)}" value="50" step="1" oninput="updateGraph()">
        <span id="sliderValue">50</span> / {len(node_list)}
        <button onclick="showAll()">Show All</button>
    </div>
    <div id="mynetwork"></div>
    <div id="nodeDetails"></div>
    <script type="text/javascript">
        const allNodes = {json.dumps(node_list)};
        const allEdges = {json.dumps(edge_list)};
        let network = null;

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
                nodes: {{
                    font: {{ color: '#FFFFFF', size: 14 }},
                    shape: 'dot',
                    size: 15
                }},
                edges: {{ color: '#AAAAAA' }},
                physics: {{ enabled: true, stabilization: false }},
                layout: {{ improvedLayout: true }}
            }};
            if (network) network.destroy();
            network = new vis.Network(document.getElementById('mynetwork'), data, options);

            network.on('click', function (params) {{
                if (params.nodes.length > 0) {{
                    const nodeId = params.nodes[0];
                    const nodeData = allNodes.find(node => node.id === nodeId);
                    if (nodeData) {{
                        const detailsDiv = document.getElementById('nodeDetails');
                        detailsDiv.innerHTML = `<h3>Node Details</h3><pre>${{nodeData.title}}</pre>`;
                        detailsDiv.style.display = 'block';
                    }}
                }} else {{
                    document.getElementById('nodeDetails').style.display = 'none';
                }}
            }});
        }}

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

print(f"Visualization generated: {os.path.abspath(output_html)}")
