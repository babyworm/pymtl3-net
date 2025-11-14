#!/usr/bin/env python3
"""
Generate interactive HTML report for each NoC topology
Uses vis.js for interactive network visualization
"""

import yaml
import json
from pathlib import Path

# Node type colors (same as before)
TYPE_COLORS = {
    'Initiator': '#FF6B6B',
    'Target': '#4ECDC4',
    'NIU': '#FFD93D',
    'Router': '#95E1D3',
    'Arbiter': '#A8E6CF',
    'Decoder': '#F38181',
    'WidthConverter': '#C7CEEA',
    'ClockConverter': '#FFEAA7'
}

def load_graph_from_yaml(filepath):
    """Load graph from YAML file"""
    with open(filepath, 'r') as f:
        config = yaml.safe_load(f)
    return config

def generate_interactive_html(config, output_path, title):
    """Generate interactive HTML report for a single topology"""

    # Prepare nodes data for vis.js
    nodes_data = []
    for node_def in config.get('nodes', []):
        node_id = node_def['id']
        node_type = node_def.get('type', 'Unknown')
        node_name = node_def.get('name', f'Node_{node_id}')

        # Create tooltip with all attributes
        attrs = []
        for key, value in node_def.items():
            if key not in ['id', 'type', 'name']:
                attrs.append(f"{key}: {value}")

        tooltip = f"<b>{node_name}</b><br>Type: {node_type}"
        if attrs:
            tooltip += "<br>" + "<br>".join(attrs)

        nodes_data.append({
            'id': node_id,
            'label': node_name,
            'title': tooltip,
            'group': node_type,
            'color': TYPE_COLORS.get(node_type, '#CCCCCC'),
            'data': node_def  # Store full data for details panel
        })

    # Prepare edges data for vis.js
    edges_data = []
    for edge_def in config.get('graph', {}).get('edges', []):
        src = edge_def['src']
        dst = edge_def['dst']

        # Create edge tooltip
        attrs = []
        for key, value in edge_def.items():
            if key not in ['src', 'dst']:
                attrs.append(f"{key}: {value}")

        tooltip = f"<b>{src} → {dst}</b>"
        if attrs:
            tooltip += "<br>" + "<br>".join(attrs)

        width = edge_def.get('width', 64)
        edges_data.append({
            'from': src,
            'to': dst,
            'title': tooltip,
            'width': max(1, width / 32),
            'arrows': 'to',
            'data': edge_def  # Store full data
        })

    # QoS allocations
    qos_allocations = config.get('constraints', {}).get('bandwidth_allocation', [])

    # Statistics
    stats = {
        'total_nodes': len(nodes_data),
        'total_edges': len(edges_data),
        'num_initiators': sum(1 for n in nodes_data if n['group'] == 'Initiator'),
        'num_targets': sum(1 for n in nodes_data if n['group'] == 'Target'),
        'num_nius': sum(1 for n in nodes_data if n['group'] == 'NIU'),
        'num_routers': sum(1 for n in nodes_data if n['group'] == 'Router'),
        'num_qos_flows': len(qos_allocations)
    }

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Interactive Topology</title>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
            background: #f5f5f5;
            overflow: hidden;
        }}

        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}

        .header h1 {{
            font-size: 1.5rem;
        }}

        .header .back-btn {{
            background: rgba(255,255,255,0.2);
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 5px;
            cursor: pointer;
            text-decoration: none;
            transition: background 0.3s;
        }}

        .header .back-btn:hover {{
            background: rgba(255,255,255,0.3);
        }}

        .container {{
            display: flex;
            height: calc(100vh - 60px);
        }}

        .sidebar {{
            width: 350px;
            background: white;
            box-shadow: 2px 0 10px rgba(0,0,0,0.1);
            overflow-y: auto;
            display: flex;
            flex-direction: column;
        }}

        .sidebar-section {{
            padding: 1.5rem;
            border-bottom: 1px solid #eee;
        }}

        .sidebar-section h2 {{
            font-size: 1.2rem;
            color: #667eea;
            margin-bottom: 1rem;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.75rem;
        }}

        .stat-item {{
            background: #f5f7fa;
            padding: 0.75rem;
            border-radius: 5px;
            text-align: center;
        }}

        .stat-item .value {{
            font-size: 1.5rem;
            font-weight: bold;
            color: #667eea;
        }}

        .stat-item .label {{
            font-size: 0.75rem;
            color: #666;
            margin-top: 0.25rem;
        }}

        .legend {{
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }}

        .legend-item {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}

        .legend-color {{
            width: 20px;
            height: 20px;
            border-radius: 4px;
        }}

        .controls {{
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
        }}

        .control-btn {{
            background: #667eea;
            color: white;
            border: none;
            padding: 0.75rem;
            border-radius: 5px;
            cursor: pointer;
            font-size: 0.9rem;
            transition: background 0.3s;
        }}

        .control-btn:hover {{
            background: #5568d3;
        }}

        .control-btn.secondary {{
            background: #95a5a6;
        }}

        .control-btn.secondary:hover {{
            background: #7f8c8d;
        }}

        .search-box {{
            width: 100%;
            padding: 0.75rem;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 0.9rem;
        }}

        .search-box:focus {{
            outline: none;
            border-color: #667eea;
        }}

        .details-panel {{
            background: #f9f9f9;
            padding: 1.5rem;
            flex: 1;
            overflow-y: auto;
        }}

        .details-panel h3 {{
            color: #667eea;
            margin-bottom: 1rem;
        }}

        .details-panel pre {{
            background: white;
            padding: 1rem;
            border-radius: 5px;
            overflow-x: auto;
            font-size: 0.85rem;
            line-height: 1.5;
        }}

        .qos-flow {{
            background: white;
            padding: 0.75rem;
            border-radius: 5px;
            margin-bottom: 0.5rem;
            border-left: 3px solid #667eea;
        }}

        .qos-flow .flow-name {{
            font-weight: bold;
            margin-bottom: 0.25rem;
        }}

        .qos-flow .flow-details {{
            font-size: 0.85rem;
            color: #666;
        }}

        #network {{
            flex: 1;
            background: white;
        }}

        .filter-group {{
            margin-top: 0.5rem;
        }}

        .filter-checkbox {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin: 0.25rem 0;
        }}

        .info-message {{
            background: #e3f2fd;
            color: #1976d2;
            padding: 1rem;
            border-radius: 5px;
            margin-bottom: 1rem;
            font-size: 0.9rem;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔬 {title}</h1>
        <a href="../report.html" class="back-btn">← Back to Overview</a>
    </div>

    <div class="container">
        <div class="sidebar">
            <div class="sidebar-section">
                <h2>📊 Statistics</h2>
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="value">{stats['total_nodes']}</div>
                        <div class="label">Nodes</div>
                    </div>
                    <div class="stat-item">
                        <div class="value">{stats['total_edges']}</div>
                        <div class="label">Edges</div>
                    </div>
                    <div class="stat-item">
                        <div class="value">{stats['num_initiators']}</div>
                        <div class="label">Initiators</div>
                    </div>
                    <div class="stat-item">
                        <div class="value">{stats['num_targets']}</div>
                        <div class="label">Targets</div>
                    </div>
                    <div class="stat-item">
                        <div class="value">{stats['num_nius']}</div>
                        <div class="label">NIUs</div>
                    </div>
                    <div class="stat-item">
                        <div class="value">{stats['num_routers']}</div>
                        <div class="label">Routers</div>
                    </div>
                </div>
            </div>

            <div class="sidebar-section">
                <h2>🎨 Node Types</h2>
                <div class="legend">
"""

    # Add legend items
    node_types_in_graph = set(n['group'] for n in nodes_data)
    for node_type in sorted(node_types_in_graph):
        color = TYPE_COLORS.get(node_type, '#CCCCCC')
        count = sum(1 for n in nodes_data if n['group'] == node_type)
        html += f"""
                    <div class="legend-item">
                        <div class="legend-color" style="background: {color};"></div>
                        <span>{node_type} ({count})</span>
                    </div>
"""

    html += """
                </div>
            </div>

            <div class="sidebar-section">
                <h2>🔍 Search & Filter</h2>
                <input type="text" id="searchBox" class="search-box" placeholder="Search nodes...">
                <div class="controls">
                    <button class="control-btn" onclick="fitNetwork()">📐 Fit to Screen</button>
                    <button class="control-btn secondary" onclick="resetView()">🔄 Reset View</button>
                </div>
            </div>
"""

    # Add QoS section if available
    if qos_allocations:
        html += """
            <div class="sidebar-section">
                <h2>⚡ QoS Flows</h2>
"""
        for qos in qos_allocations[:10]:  # Show first 10
            init_id = qos['initiator']
            tgt_id = qos['target']
            bw = qos.get('guaranteed_bw', 0)
            lat = qos.get('max_latency', 0)
            priority = qos.get('priority', '-')

            # Find names
            init_name = next((n['label'] for n in nodes_data if n['id'] == init_id), f'Node {init_id}')
            tgt_name = next((n['label'] for n in nodes_data if n['id'] == tgt_id), f'Node {tgt_id}')

            html += f"""
                <div class="qos-flow">
                    <div class="flow-name">{init_name} → {tgt_name}</div>
                    <div class="flow-details">BW: {bw} GB/s | Latency: {lat} cycles | Priority: {priority}</div>
                </div>
"""

        html += """
            </div>
"""

    html += """
            <div class="sidebar-section details-panel" id="detailsPanel">
                <div class="info-message">
                    💡 Click on a node or edge to see detailed information
                </div>
            </div>
        </div>

        <div id="network"></div>
    </div>

    <script type="text/javascript">
        // Data
        const nodesData = """ + json.dumps(nodes_data, indent=8) + """;
        const edgesData = """ + json.dumps(edges_data, indent=8) + """;

        // Create network
        const container = document.getElementById('network');
        const data = {
            nodes: new vis.DataSet(nodesData),
            edges: new vis.DataSet(edgesData)
        };

        const options = {
            nodes: {
                shape: 'dot',
                size: 25,
                font: {
                    size: 14,
                    color: '#333'
                },
                borderWidth: 2,
                borderWidthSelected: 4
            },
            edges: {
                color: {
                    color: '#848484',
                    highlight: '#667eea',
                    hover: '#667eea'
                },
                smooth: {
                    type: 'continuous'
                },
                font: {
                    size: 12,
                    align: 'middle'
                }
            },
            physics: {
                enabled: true,
                barnesHut: {
                    gravitationalConstant: -8000,
                    centralGravity: 0.3,
                    springLength: 200,
                    springConstant: 0.04,
                    damping: 0.09
                },
                stabilization: {
                    iterations: 200
                }
            },
            interaction: {
                hover: true,
                tooltipDelay: 100,
                navigationButtons: true,
                keyboard: true
            }
        };

        const network = new vis.Network(container, data, options);

        // Event handlers
        network.on('click', function(params) {
            const detailsPanel = document.getElementById('detailsPanel');

            if (params.nodes.length > 0) {
                // Node clicked
                const nodeId = params.nodes[0];
                const node = nodesData.find(n => n.id === nodeId);

                detailsPanel.innerHTML = `
                    <h3>🔵 Node Details</h3>
                    <pre>${JSON.stringify(node.data, null, 2)}</pre>
                `;
            } else if (params.edges.length > 0) {
                // Edge clicked
                const edgeId = params.edges[0];
                const edge = edgesData.find(e =>
                    e.from === data.edges.get(edgeId).from &&
                    e.to === data.edges.get(edgeId).to
                );

                detailsPanel.innerHTML = `
                    <h3>➡️ Edge Details</h3>
                    <pre>${JSON.stringify(edge.data, null, 2)}</pre>
                `;
            } else {
                // Background clicked
                detailsPanel.innerHTML = `
                    <div class="info-message">
                        💡 Click on a node or edge to see detailed information
                    </div>
                `;
            }
        });

        // Search functionality
        document.getElementById('searchBox').addEventListener('input', function(e) {
            const searchTerm = e.target.value.toLowerCase();

            if (searchTerm === '') {
                network.selectNodes([]);
                return;
            }

            const matchingNodes = nodesData
                .filter(n => n.label.toLowerCase().includes(searchTerm))
                .map(n => n.id);

            network.selectNodes(matchingNodes);
            if (matchingNodes.length > 0) {
                network.focus(matchingNodes[0], {
                    scale: 1.5,
                    animation: true
                });
            }
        });

        // Helper functions
        function fitNetwork() {
            network.fit({
                animation: {
                    duration: 1000,
                    easingFunction: 'easeInOutQuad'
                }
            });
        }

        function resetView() {
            network.moveTo({
                scale: 1.0,
                animation: {
                    duration: 1000,
                    easingFunction: 'easeInOutQuad'
                }
            });
        }

        // Stabilization progress
        network.on('stabilizationProgress', function(params) {
            console.log('Stabilization progress:', params.iterations);
        });

        network.on('stabilizationIterationsDone', function() {
            console.log('Stabilization complete');
            network.setOptions({ physics: false });
        });

        // Initial fit
        setTimeout(() => fitNetwork(), 1000);
    </script>
</body>
</html>
"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

def main():
    """Generate interactive reports for all examples"""
    examples_dir = Path('.')
    output_dir = Path('visualizations/interactive')
    output_dir.mkdir(exist_ok=True)

    # Create scale directories
    for scale in ['small', 'medium', 'large']:
        (output_dir / scale).mkdir(exist_ok=True)

    count = 0

    # Process all examples
    for scale in ['small', 'medium', 'large']:
        scale_dir = examples_dir / scale

        if not scale_dir.exists():
            continue

        for yaml_file in sorted(scale_dir.glob('*.yml')):
            print(f"Generating interactive report: {yaml_file}")

            try:
                config = load_graph_from_yaml(yaml_file)
                title = yaml_file.stem.replace('_', ' ').title()

                output_path = output_dir / scale / f"{yaml_file.stem}.html"
                generate_interactive_html(config, output_path, title)

                count += 1
                print(f"  ✓ Generated: {output_path}")

            except Exception as e:
                print(f"  ✗ Error: {e}")
                continue

    print(f"\n✅ Generated {count} interactive reports")
    print(f"📂 Location: {output_dir}")

if __name__ == '__main__':
    main()
