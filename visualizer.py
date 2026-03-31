import json
import os

# 1. Configuration: Edge Colors based on 'kind' found in owlapy_graph.json
EDGE_COLORS = {
    "contains": "#888888",     # Grey - Structural
    "imports": "#4682B4",      # SteelBlue - Dependencies
    "inherits": "#32CD32",     # LimeGreen - Class Hierarchy
    "calls": "#FF4500",        # OrangeRed - Function execution
    "default": "#AAAAAA"       # LightGrey
}

NODE_COLORS = {
    "module": "#E91E63",       # Pink
    "class": "#2196F3",        # Blue
    "function": "#4CAF50",     # Green
    "method": "#FFEB3B",       # Yellow
    "default": "#9E9E9E"       # Grey
}

def generate_visualization(json_path, output_html="codegraph.html"):
    # Load the data
    with open(json_path, 'r') as f:
        data = json.load(f)

    raw_nodes = data.get('nodes', {})
    raw_edges = data.get('edges', [])

    # Map original IDs to vis.js numeric IDs
    node_list = []
    id_map = {}
    for i, (original_id, info) in enumerate(raw_nodes.items()):
        id_map[original_id] = i
        node_list.append({
            "id": i,
            "label": info.get('name', original_id),
            "title": f"Path: {info.get('file_path')}\nType: {info.get('kind')}",
            "group": info.get('kind', 'default'),
            "color": NODE_COLORS.get(info.get('kind'), NODE_COLORS["default"]),
            "code": info.get('code', '') # Store code for the sidebar
        })

    # Prepare Edges
    edge_list = []
    for i, edge in enumerate(raw_edges):
        src = edge.get('source_id')
        tgt = edge.get('target_id')
        kind = edge.get('kind', 'default')
        
        if src in id_map and tgt in id_map:
            edge_list.append({
                "id": i,
                "from": id_map[src],
                "to": id_map[tgt],
                "color": {"color": EDGE_COLORS.get(kind, EDGE_COLORS["default"])},
                "arrows": {"to": {"enabled": True, "scaleFactor": 0.5}},
                "title": f"Relationship: {kind}",
                "smooth": {"type": "curvedCW", "roundness": 0.2} # Prevents overlap on bidirectional edges
            })

    # HTML Template with vis.js and UI logic
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Owlapy Code Explorer</title>
        <script type="text/javascript" src="https://unpkg.com/vis-network@9.1.2/dist/vis-network.min.js"></script>
        <link href="https://unpkg.com/vis-network@9.1.2/dist/vis-network.min.css" rel="stylesheet" type="text/css" />
        <style>
            body {{ font-family: sans-serif; background: #1a1a1a; color: #eee; margin: 0; display: flex; }}
            #container {{ flex-grow: 1; height: 100vh; position: relative; }}
            #mynetwork {{ width: 100%; height: 100%; }}
            #sidebar {{ width: 400px; background: #252525; border-left: 1px solid #444; padding: 15px; overflow-y: auto; height: 100vh; }}
            pre {{ background: #000; padding: 10px; border-radius: 4px; overflow-x: auto; font-size: 12px; color: #adff2f; }}
            .controls {{ position: absolute; top: 10px; left: 10px; z-index: 10; background: rgba(0,0,0,0.7); padding: 10px; border-radius: 5px; }}
            h2, h3 {{ margin-top: 0; color: #2196F3; }}
        </style>
    </head>
    <body>
        <div id="container">
            <div class="controls">
                <label>Node Limit:</label>
                <input type="range" id="sizeSlider" min="1" max="{len(node_list)}" value="{min(100, len(node_list))}" oninput="updateGraph()">
                <span id="sliderVal">{min(100, len(node_list))}</span>
            </div>
            <div id="mynetwork"></div>
        </div>
        <div id="sidebar">
            <h2>Inspector</h2>
            <p>Click a node to view properties and source code.</p>
            <div id="details"></div>
        </div>

        <script type="text/javascript">
            const allNodes = {json.dumps(node_list)};
            const allEdges = {json.dumps(edge_list)};
            let network = null;

            function updateGraph() {{
                const limit = document.getElementById('sizeSlider').value;
                document.getElementById('sliderVal').innerText = limit;
                
                const nodesSubset = allNodes.slice(0, limit);
                const nodeIds = new Set(nodesSubset.map(n => n.id));
                const edgesSubset = allEdges.filter(e => nodeIds.has(e.from) && nodeIds.has(e.to));

                const data = {{ 
                    nodes: new vis.DataSet(nodesSubset), 
                    edges: new vis.DataSet(edgesSubset) 
                }};

                const options = {{
                    nodes: {{ font: {{ color: '#ffffff' }}, borderWidth: 2, shadow: true }},
                    edges: {{ width: 2, hoverWidth: 4 }},
                    physics: {{
                        solver: 'forceAtlas2Based',
                        forceAtlas2Based: {{ gravitationalConstant: -50, springLength: 100, springConstant: 0.08 }},
                        stabilization: {{ iterations: 100 }}
                    }},
                    interaction: {{ hover: true, tooltipDelay: 200 }}
                }};

                if (network) network.destroy();
                network = new vis.Network(document.getElementById('mynetwork'), data, options);

                network.on("click", function (params) {{
                    if (params.nodes.length > 0) {{
                        const node = allNodes.find(n => n.id === params.nodes[0]);
                        const details = document.getElementById('details');
                        details.innerHTML = `
                            <h3>${{node.label}}</h3>
                            <p><b>Type:</b> ${{node.group}}</p>
                            <p><b>Metadata:</b> ${{node.title.replace('\\n', '<br>')}}</p>
                            ${{node.code ? '<b>Source Code:</b><pre>' + node.code + '</pre>' : '<i>No source available</i>'}}
                        `;
                    }}
                }});
            }}

            updateGraph();
        </script>
    </body>
    </html>
    """

    with open(output_html, "w") as f:
        f.write(html_template)
    
    print(f"Visualization generated: {{os.path.abspath(output_html)}}")

if __name__ == "__main__":
    # Ensure owlapy_graph.json is in the same directory
    generate_visualization("owlapy_graph.json")