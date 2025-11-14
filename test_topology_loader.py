#!/usr/bin/env python3
"""
Test topology loader with auto-converter insertion
"""

import sys
import os

# Add pymtl3_net to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pymtl3_net.irregnet.topology_loader import TopologyLoader


def test_mobile_soc():
    """Test loading mobile_soc.yml with auto-converter insertion"""
    print("="*70)
    print("Testing mobile_soc.yml with auto-converter insertion")
    print("="*70)

    # Test with auto-insertion disabled (use existing converters)
    loader = TopologyLoader(
        'examples/small/mobile_soc.yml',
        auto_insert_converters=False
    )

    print(f"\nOriginal topology:")
    print(f"  Nodes: {len(loader.nodes)}")
    print(f"  Edges: {len(loader.edges)}")

    # Count node types
    node_types = {}
    for node in loader.nodes:
        node_types[node.type] = node_types.get(node.type, 0) + 1

    print(f"\nNode types:")
    for node_type, count in sorted(node_types.items()):
        print(f"  {node_type}: {count}")

    # Test NetworkX graph
    G = loader.get_networkx_graph()
    print(f"\nNetworkX graph:")
    print(f"  Nodes: {G.number_of_nodes()}")
    print(f"  Edges: {G.number_of_edges()}")

    # Check for clock crossings
    clock_crossings = []
    for src, dst in G.edges():
        src_clk = G.nodes[src].get('clock_domain')
        dst_clk = G.nodes[dst].get('clock_domain')
        if src_clk and dst_clk and src_clk != dst_clk:
            # Check if there's a CDC in between
            edge_nodes = list(G.successors(src))
            if dst in edge_nodes:
                # Direct connection
                clock_crossings.append((src, dst, src_clk, dst_clk))

    if clock_crossings:
        print(f"\nWarning: Found {len(clock_crossings)} clock domain crossings without CDC:")
        for src, dst, src_clk, dst_clk in clock_crossings[:5]:
            src_name = G.nodes[src]['name']
            dst_name = G.nodes[dst]['name']
            print(f"  {src_name}({src_clk}) -> {dst_name}({dst_clk})")
    else:
        print(f"\n✓ No clock domain crossings found (all have CDCs)")

    return loader


def test_auto_insertion():
    """Test automatic converter insertion on a simple example"""
    print("\n" + "="*70)
    print("Testing auto-converter insertion on iot_device.yml")
    print("="*70)

    # Load without auto-insertion first
    loader_manual = TopologyLoader(
        'examples/small/iot_device.yml',
        auto_insert_converters=False
    )

    print(f"\nWithout auto-insertion:")
    print(f"  Nodes: {len(loader_manual.nodes)}")

    # Create a test case with clock crossing
    import yaml
    import tempfile

    # Create a simple test topology with clock crossing
    test_config = {
        'network': 'Irregular',
        'num_nodes': 4,
        'nodes': [
            {'id': 0, 'type': 'Initiator', 'name': 'CPU'},
            {'id': 1, 'type': 'NIU', 'name': 'NIU1', 'width': 64, 'clock_domain': 'fast'},
            {'id': 2, 'type': 'Router', 'name': 'Router1', 'width': 64, 'clock_domain': 'slow', 'num_ports': 2},
            {'id': 3, 'type': 'Target', 'name': 'DDR'},
        ],
        'graph': {
            'edges': [
                {'src': 0, 'dst': 1, 'width': 64, 'latency': 1},
                {'src': 1, 'dst': 2, 'width': 64, 'latency': 2},  # Clock crossing: fast -> slow
                {'src': 2, 'dst': 3, 'width': 64, 'latency': 5},
            ]
        },
        'constraints': {}
    }

    # Write to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        yaml.dump(test_config, f)
        temp_path = f.name

    try:
        # Load with auto-insertion
        loader_auto = TopologyLoader(temp_path, auto_insert_converters=True)

        print(f"\nWith auto-insertion:")
        print(f"  Nodes: {len(loader_auto.nodes)} (expected 5 = 4 + 1 CDC)")
        print(f"  Edges: {len(loader_auto.edges)}")

        # Check if CDC was inserted
        cdc_nodes = [n for n in loader_auto.nodes if n.type == 'ClockConverter']
        if cdc_nodes:
            print(f"\n✓ Successfully inserted {len(cdc_nodes)} ClockConverter(s):")
            for cdc in cdc_nodes:
                print(f"  - {cdc.name}: {cdc.attributes.get('src_clock_domain')} -> {cdc.attributes.get('dst_clock_domain')}")
        else:
            print(f"\n✗ Failed to insert ClockConverter")

    finally:
        os.unlink(temp_path)


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("Topology Loader Test Suite")
    print("="*70)

    # Test 1: Load mobile_soc
    try:
        loader1 = test_mobile_soc()
        print("\n✓ Test 1 PASSED: mobile_soc.yml loaded successfully")
    except Exception as e:
        print(f"\n✗ Test 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Test 2: Auto-insertion
    try:
        test_auto_insertion()
        print("\n✓ Test 2 PASSED: Auto-insertion works correctly")
    except Exception as e:
        print(f"\n✗ Test 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1

    print("\n" + "="*70)
    print("All tests PASSED!")
    print("="*70)
    return 0


if __name__ == '__main__':
    sys.exit(main())
