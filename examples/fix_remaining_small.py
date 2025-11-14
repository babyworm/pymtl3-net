#!/usr/bin/env python3
"""
Automatically fix clock crossings in remaining small examples
Based on validation warnings
"""

import yaml
import sys

# Mapping of file to clock crossing fixes
FIXES = {
    'small/iot_device.yml': {
        # Warning: Router0(slow) → Router1(fast)
        'cdc': {'src': 'Router0', 'dst': 'Router1', 'src_id': None, 'dst_id': None, 'width': 64}
    },
    'small/medical_device.yml': {
        # Warning: Peripheral_Router(slow) → Sensor_Router(fast)
        'cdc': {'src': 'Peripheral_Router', 'dst': 'Sensor_Router', 'src_id': None, 'dst_id': None, 'width': 16}
    },
    'small/network_switch.yml': {
        # Warning: CPU_NIU(slow) → Switching_Fabric(fast)
        'cdc': {'src': 'CPU_NIU', 'dst': 'Switching_Fabric', 'src_id': None, 'dst_id': None, 'width': 32}
    },
    'small/smart_camera.yml': {
        # Warning: Audio_NIU(slow) → Memory_Router(fast)
        'cdc': {'src': 'Audio_NIU', 'dst': 'Memory_Router', 'src_id': None, 'dst_id': None, 'width': 64}
    },
    'small/wearable.yml': {
        # Warning: Sensor_Router(ultra_slow) → Main_Router(slow)
        'cdc': {'src': 'Sensor_Router', 'dst': 'Main_Router', 'src_id': None, 'dst_id': None, 'width': 32}
    }
}

def fix_file(filepath):
    """Fix clock crossings in a single file"""
    print(f"Fixing {filepath}...")

    with open(filepath, 'r') as f:
        config = yaml.safe_load(f)

    nodes = config['nodes']
    edges = config['graph']['edges']

    # Find node IDs by name
    node_map = {n['name']: n['id'] for n in nodes}

    fix_info = FIXES.get(filepath, {}).get('cdc')
    if not fix_info:
        print(f"  No fix defined for {filepath}")
        return

    src_name = fix_info['src']
    dst_name = fix_info['dst']

    if src_name not in node_map or dst_name not in node_map:
        print(f"  ERROR: Could not find {src_name} or {dst_name}")
        return

    src_id = node_map[src_name]
    dst_id = node_map[dst_name]

    # Find the edge
    edge_to_fix = None
    for i, edge in enumerate(edges):
        if edge['src'] == src_id and edge['dst'] == dst_id:
            edge_to_fix = (i, edge)
            break

    if not edge_to_fix:
        print(f"  ERROR: Could not find edge from {src_name}({src_id}) to {dst_name}({dst_id})")
        return

    edge_idx, edge = edge_to_fix

    # Find src and dst nodes to get clock domains
    src_node = next(n for n in nodes if n['id'] == src_id)
    dst_node = next(n for n in nodes if n['id'] == dst_id)

    # Add ClockConverter node
    new_cdc_id = config['num_nodes']
    cdc_node = {
        'id': new_cdc_id,
        'type': 'ClockConverter',
        'name': f'{src_name}_{dst_name}_CDC',
        'width': edge['width'],
        'src_clock_domain': src_node['clock_domain'],
        'dst_clock_domain': dst_node['clock_domain']
    }

    # Find where to insert (before Targets)
    target_idx = next(i for i, n in enumerate(nodes) if n['type'] == 'Target')
    nodes.insert(target_idx, cdc_node)

    # Update num_nodes
    config['num_nodes'] += 1

    # Update the edge to go through CDC
    old_latency = edge['latency']
    edges[edge_idx] = {
        'src': src_id,
        'dst': new_cdc_id,
        'width': edge['width'],
        'latency': max(1, old_latency // 2)
    }
    edges.insert(edge_idx + 1, {
        'src': new_cdc_id,
        'dst': dst_id,
        'width': edge['width'],
        'latency': max(2, old_latency - old_latency // 2)
    })

    # Write back
    with open(filepath, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False, indent=2)

    print(f"  ✓ Fixed: Added CDC node {new_cdc_id}, updated edge {src_id}→{dst_id}")

if __name__ == '__main__':
    for filepath in FIXES.keys():
        try:
            fix_file(filepath)
        except Exception as e:
            print(f"ERROR fixing {filepath}: {e}")
            import traceback
            traceback.print_exc()
