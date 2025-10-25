#!/usr/bin/env python3
"""
Generate visual report for all NoC topology examples
"""

import yaml
import networkx as nx
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from pathlib import Path
from collections import Counter
import json

# Node type colors
TYPE_COLORS = {
    'Initiator': '#FF6B6B',      # Red
    'Target': '#4ECDC4',         # Teal
    'NIU': '#FFD93D',            # Yellow
    'Router': '#95E1D3',         # Mint
    'Arbiter': '#A8E6CF',        # Light green
    'Decoder': '#F38181',        # Salmon
    'WidthConverter': '#C7CEEA', # Lavender
    'ClockConverter': '#FFEAA7'  # Light yellow
}

def load_graph_from_yaml(filepath):
    """Load graph from YAML file"""
    with open(filepath, 'r') as f:
        config = yaml.safe_load(f)

    G = nx.DiGraph()

    # Add nodes
    for node_def in config.get('nodes', []):
        node_id = node_def['id']
        G.add_node(node_id, **node_def)

    # Add edges
    for edge_def in config.get('graph', {}).get('edges', []):
        src = edge_def['src']
        dst = edge_def['dst']
        edge_attrs = {k: v for k, v in edge_def.items() if k not in ['src', 'dst']}
        G.add_edge(src, dst, **edge_attrs)

    return G, config

def analyze_graph(G, config):
    """Analyze graph and return statistics"""
    stats = {}

    # Basic stats
    stats['num_nodes'] = G.number_of_nodes()
    stats['num_edges'] = G.number_of_edges()

    # Node type distribution
    node_types = nx.get_node_attributes(G, 'type')
    type_counts = Counter(node_types.values())
    stats['node_types'] = dict(type_counts)

    # Initiators and Targets
    stats['num_initiators'] = type_counts.get('Initiator', 0)
    stats['num_targets'] = type_counts.get('Target', 0)
    stats['num_nius'] = type_counts.get('NIU', 0)
    stats['num_routers'] = type_counts.get('Router', 0)

    # Connectivity
    if G.number_of_nodes() > 0:
        stats['avg_degree'] = sum(dict(G.degree()).values()) / G.number_of_nodes()
        stats['max_degree'] = max(dict(G.degree()).values()) if G.number_of_nodes() > 0 else 0
    else:
        stats['avg_degree'] = 0
        stats['max_degree'] = 0

    # Clock domains
    clock_domains = config.get('constraints', {}).get('clock_domains', [])
    stats['num_clock_domains'] = len(clock_domains)

    # QoS allocations
    bw_allocs = config.get('constraints', {}).get('bandwidth_allocation', [])
    stats['num_qos_flows'] = len(bw_allocs)

    return stats

def visualize_topology(G, config, output_path, scale='small'):
    """Visualize topology and save to file"""
    if G.number_of_nodes() == 0:
        # Create empty placeholder
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.text(0.5, 0.5, 'Large-scale template\n(Visualization available on request)',
                ha='center', va='center', fontsize=14)
        ax.axis('off')
        plt.tight_layout()
        plt.savefig(output_path, dpi=100, bbox_inches='tight')
        plt.close()
        return

    # Figure size based on scale
    if scale == 'small':
        figsize = (12, 10)
        node_size = 800
        font_size = 8
    elif scale == 'medium':
        figsize = (16, 14)
        node_size = 600
        font_size = 7
    else:  # large
        figsize = (20, 18)
        node_size = 400
        font_size = 6

    fig, ax = plt.subplots(figsize=figsize)

    # Layout
    if G.number_of_nodes() < 30:
        pos = nx.spring_layout(G, seed=42, k=2, iterations=50)
    else:
        pos = nx.spring_layout(G, seed=42, k=1.5, iterations=30)

    # Node colors by type
    node_types = nx.get_node_attributes(G, 'type')
    node_colors = [TYPE_COLORS.get(node_types.get(node, 'Router'), '#CCCCCC')
                   for node in G.nodes()]

    # Draw nodes
    nx.draw_networkx_nodes(G, pos, node_color=node_colors,
                          node_size=node_size, alpha=0.9, ax=ax)

    # Draw labels (only for small graphs)
    if G.number_of_nodes() < 40:
        labels = {}
        for node in G.nodes():
            name = G.nodes[node].get('name', f'N{node}')
            node_type = G.nodes[node].get('type', '?')
            labels[node] = f"{name}\n[{node_type}]"

        nx.draw_networkx_labels(G, pos, labels, font_size=font_size,
                               font_weight='bold', ax=ax)
    else:
        # Just node IDs for large graphs
        nx.draw_networkx_labels(G, pos, font_size=font_size, ax=ax)

    # Draw edges
    edge_widths = []
    for u, v in G.edges():
        width = G[u][v].get('width', 64)
        edge_widths.append(max(0.5, width / 64))

    nx.draw_networkx_edges(G, pos, width=edge_widths, alpha=0.6,
                          edge_color='gray', arrows=True,
                          arrowsize=10 if scale == 'small' else 5,
                          ax=ax)

    # Legend
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=color, label=node_type)
                      for node_type, color in TYPE_COLORS.items()
                      if node_type in node_types.values()]

    ax.legend(handles=legend_elements, loc='upper left', fontsize=10)

    ax.set_title(f"Topology: {output_path.stem}", fontsize=16, fontweight='bold')
    ax.axis('off')
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

def generate_html_report(all_stats, output_path):
    """Generate HTML report"""
    html = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NoC Topology Visual Report</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }

        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
        }

        .header p {
            font-size: 1.1rem;
            opacity: 0.9;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }

        .summary {
            background: white;
            border-radius: 10px;
            padding: 2rem;
            margin-bottom: 2rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }

        .summary h2 {
            color: #667eea;
            margin-bottom: 1rem;
            font-size: 1.8rem;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-top: 1rem;
        }

        .stat-card {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 1.5rem;
            border-radius: 8px;
            text-align: center;
        }

        .stat-card .value {
            font-size: 2rem;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 0.5rem;
        }

        .stat-card .label {
            font-size: 0.9rem;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .scale-section {
            margin-bottom: 3rem;
        }

        .scale-section h2 {
            color: #764ba2;
            font-size: 2rem;
            margin-bottom: 1.5rem;
            padding-bottom: 0.5rem;
            border-bottom: 3px solid #764ba2;
        }

        .examples-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(450px, 1fr));
            gap: 2rem;
        }

        .example-card {
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.3s, box-shadow 0.3s;
        }

        .example-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 15px rgba(0,0,0,0.2);
        }

        .example-card img {
            width: 100%;
            height: 300px;
            object-fit: contain;
            background: #f9f9f9;
            border-bottom: 1px solid #eee;
        }

        .example-info {
            padding: 1.5rem;
        }

        .example-info h3 {
            color: #333;
            margin-bottom: 0.5rem;
            font-size: 1.3rem;
        }

        .example-info .description {
            color: #666;
            margin-bottom: 1rem;
            font-size: 0.95rem;
        }

        .example-stats {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.5rem;
            font-size: 0.85rem;
        }

        .example-stat {
            background: #f5f5f5;
            padding: 0.5rem;
            border-radius: 4px;
            display: flex;
            justify-content: space-between;
        }

        .example-stat .stat-label {
            color: #666;
        }

        .example-stat .stat-value {
            font-weight: bold;
            color: #667eea;
        }

        .node-types {
            margin-top: 1rem;
            padding-top: 1rem;
            border-top: 1px solid #eee;
        }

        .node-types-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.3rem;
            font-size: 0.8rem;
        }

        .node-type-item {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .node-type-color {
            width: 12px;
            height: 12px;
            border-radius: 3px;
        }

        .footer {
            background: #333;
            color: white;
            text-align: center;
            padding: 2rem;
            margin-top: 3rem;
        }

        .toc {
            background: white;
            border-radius: 10px;
            padding: 2rem;
            margin-bottom: 2rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }

        .toc h2 {
            color: #667eea;
            margin-bottom: 1rem;
        }

        .toc ul {
            list-style: none;
            padding-left: 1rem;
        }

        .toc li {
            margin: 0.5rem 0;
        }

        .toc a {
            color: #764ba2;
            text-decoration: none;
            transition: color 0.3s;
        }

        .toc a:hover {
            color: #667eea;
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>NoC Topology Visual Report</h1>
        <p>30개의 Network-on-Chip 토폴로지 예제 시각화</p>
        <p style="font-size: 0.9rem; margin-top: 1rem;">생성일: 2025-10-22</p>
    </div>

    <div class="container">
"""

    # Overall summary
    total_nodes = sum(s['stats']['num_nodes'] for s in all_stats.values())
    total_edges = sum(s['stats']['num_edges'] for s in all_stats.values())
    total_initiators = sum(s['stats']['num_initiators'] for s in all_stats.values())
    total_targets = sum(s['stats']['num_targets'] for s in all_stats.values())

    html += f"""
        <div class="summary">
            <h2>📊 전체 통계</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="value">{len(all_stats)}</div>
                    <div class="label">Total Examples</div>
                </div>
                <div class="stat-card">
                    <div class="value">{total_nodes:,}</div>
                    <div class="label">Total Nodes</div>
                </div>
                <div class="stat-card">
                    <div class="value">{total_edges:,}</div>
                    <div class="label">Total Edges</div>
                </div>
                <div class="stat-card">
                    <div class="value">{total_initiators}</div>
                    <div class="label">Total Initiators</div>
                </div>
                <div class="stat-card">
                    <div class="value">{total_targets}</div>
                    <div class="label">Total Targets</div>
                </div>
            </div>
        </div>

        <div class="toc">
            <h2>📑 목차</h2>
            <ul>
                <li><a href="#small">Small-Scale Examples (10)</a></li>
                <li><a href="#medium">Medium-Scale Examples (10)</a></li>
                <li><a href="#large">Large-Scale Examples (10)</a></li>
            </ul>
        </div>
"""

    # Generate sections for each scale
    for scale in ['small', 'medium', 'large']:
        scale_stats = {k: v for k, v in all_stats.items() if v['scale'] == scale}

        if not scale_stats:
            continue

        scale_titles = {
            'small': 'Small-Scale Examples',
            'medium': 'Medium-Scale Examples',
            'large': 'Large-Scale Examples'
        }

        html += f"""
        <div class="scale-section" id="{scale}">
            <h2>{scale_titles[scale]} ({len(scale_stats)}개)</h2>
            <div class="examples-grid">
"""

        for name, data in sorted(scale_stats.items()):
            stats = data['stats']

            # Node types breakdown
            node_types_html = ""
            for ntype, count in sorted(stats.get('node_types', {}).items()):
                color = TYPE_COLORS.get(ntype, '#CCCCCC')
                node_types_html += f"""
                    <div class="node-type-item">
                        <div class="node-type-color" style="background: {color};"></div>
                        <span>{ntype}: {count}</span>
                    </div>
"""

            html += f"""
                <div class="example-card">
                    <img src="visualizations/{scale}/{name}.png" alt="{name}">
                    <div class="example-info">
                        <h3>{name.replace('_', ' ').title()}</h3>
                        <div class="example-stats">
                            <div class="example-stat">
                                <span class="stat-label">Nodes:</span>
                                <span class="stat-value">{stats['num_nodes']}</span>
                            </div>
                            <div class="example-stat">
                                <span class="stat-label">Edges:</span>
                                <span class="stat-value">{stats['num_edges']}</span>
                            </div>
                            <div class="example-stat">
                                <span class="stat-label">Initiators:</span>
                                <span class="stat-value">{stats['num_initiators']}</span>
                            </div>
                            <div class="example-stat">
                                <span class="stat-label">Targets:</span>
                                <span class="stat-value">{stats['num_targets']}</span>
                            </div>
                            <div class="example-stat">
                                <span class="stat-label">Routers:</span>
                                <span class="stat-value">{stats['num_routers']}</span>
                            </div>
                            <div class="example-stat">
                                <span class="stat-label">Avg Degree:</span>
                                <span class="stat-value">{stats['avg_degree']:.1f}</span>
                            </div>
                        </div>
                        <div class="node-types">
                            <div class="node-types-grid">
                                {node_types_html}
                            </div>
                        </div>
                    </div>
                </div>
"""

        html += """
            </div>
        </div>
"""

    html += """
    </div>

    <div class="footer">
        <p>🤖 Generated with Claude Code</p>
        <p style="margin-top: 0.5rem; font-size: 0.9rem;">PyMTL3-net NoC Synthesis Examples</p>
    </div>
</body>
</html>
"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

def main():
    """Main function"""
    examples_dir = Path('.')
    output_dir = Path('visualizations')
    output_dir.mkdir(exist_ok=True)

    # Create scale directories
    for scale in ['small', 'medium', 'large']:
        (output_dir / scale).mkdir(exist_ok=True)

    all_stats = {}

    # Process all examples
    for scale in ['small', 'medium', 'large']:
        scale_dir = examples_dir / scale

        if not scale_dir.exists():
            continue

        for yaml_file in sorted(scale_dir.glob('*.yml')):
            print(f"Processing: {yaml_file}")

            try:
                G, config = load_graph_from_yaml(yaml_file)
                stats = analyze_graph(G, config)

                # Generate visualization
                output_path = output_dir / scale / f"{yaml_file.stem}.png"
                visualize_topology(G, config, output_path, scale)

                all_stats[yaml_file.stem] = {
                    'scale': scale,
                    'stats': stats
                }

                print(f"  ✓ Generated: {output_path}")
                print(f"    Nodes: {stats['num_nodes']}, Edges: {stats['num_edges']}")

            except Exception as e:
                print(f"  ✗ Error: {e}")
                continue

    # Generate HTML report
    html_path = output_dir / 'report.html'
    generate_html_report(all_stats, html_path)
    print(f"\n✅ HTML report generated: {html_path}")

    # Save stats as JSON
    stats_path = output_dir / 'stats.json'
    with open(stats_path, 'w') as f:
        json.dump(all_stats, f, indent=2)
    print(f"✅ Stats saved: {stats_path}")

    print(f"\n📊 Summary:")
    print(f"  Total examples: {len(all_stats)}")
    print(f"  Small: {len([s for s in all_stats.values() if s['scale'] == 'small'])}")
    print(f"  Medium: {len([s for s in all_stats.values() if s['scale'] == 'medium'])}")
    print(f"  Large: {len([s for s in all_stats.values() if s['scale'] == 'large'])}")

if __name__ == '__main__':
    main()
