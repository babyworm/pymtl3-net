#!/usr/bin/env python3
"""
Verify the complete tool flow for irregular topologies:
1. Load YAML
2. Auto-insert converters for clock/width mismatches
3. Validate the resulting topology
4. Export to updated YAML

This demonstrates the proper workflow for users to create topologies.
"""

import sys
import os
import glob

# Add parent to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pymtl3_net.irregnet.topology_loader import TopologyLoader


def verify_topology(yaml_path: str, auto_insert: bool = True) -> bool:
    """
    Verify a single topology file through the complete tool flow.

    Returns True if verification passes, False otherwise.
    """
    print(f"\n{'='*70}")
    print(f"Verifying: {os.path.basename(yaml_path)}")
    print(f"{'='*70}")

    try:
        # Step 1: Load topology
        loader = TopologyLoader(yaml_path, auto_insert_converters=auto_insert)

        print(f"\n1. ✓ Topology loaded successfully")
        print(f"   Nodes: {len(loader.nodes)}")
        print(f"   Edges: {len(loader.edges)}")

        # Step 2: Check node types
        node_types = {}
        for node in loader.nodes:
            node_types[node.type] = node_types.get(node.type, 0) + 1

        print(f"\n2. ✓ Node types:")
        for node_type, count in sorted(node_types.items()):
            print(f"   {node_type:20s}: {count:3d}")

        # Step 3: Validate connectivity
        G = loader.get_networkx_graph()

        # Check for disconnected components
        import networkx as nx
        if not nx.is_weakly_connected(G):
            print(f"\n3. ⚠️  Warning: Graph has disconnected components")
            components = list(nx.weakly_connected_components(G))
            print(f"   Number of components: {len(components)}")
        else:
            print(f"\n3. ✓ Graph is connected")

        # Step 4: Check for clock crossings WITHOUT converters
        clock_crossings = []
        for src, dst in G.edges():
            src_node = G.nodes[src]
            dst_node = G.nodes[dst]
            src_clk = src_node.get('clock_domain')
            dst_clk = dst_node.get('clock_domain')

            # Check if this is a direct crossing (not through a converter)
            if src_clk and dst_clk and src_clk != dst_clk:
                # Check if dst is NOT a ClockConverter
                if dst_node.get('type') != 'ClockConverter':
                    clock_crossings.append((
                        src,
                        dst,
                        src_node.get('name'),
                        dst_node.get('name'),
                        src_clk,
                        dst_clk
                    ))

        if clock_crossings:
            print(f"\n4. ✗ Found {len(clock_crossings)} unhandled clock crossings:")
            for src, dst, src_name, dst_name, src_clk, dst_clk in clock_crossings[:5]:
                print(f"   {src_name}({src_clk}) -> {dst_name}({dst_clk})")
            if not auto_insert:
                print(f"   Note: Auto-insertion was disabled")
            return False
        else:
            print(f"\n4. ✓ No unhandled clock crossings")

        # Step 5: Check for width mismatches WITHOUT converters
        width_mismatches = []
        for src, dst, edge_data in G.edges(data=True):
            src_node = G.nodes[src]
            dst_node = G.nodes[dst]

            # Skip if dst is a WidthConverter
            if dst_node.get('type') == 'WidthConverter':
                continue

            src_width = src_node.get('width') or src_node.get('dst_width')
            dst_width = dst_node.get('width') or dst_node.get('src_width')
            edge_width = edge_data.get('width')

            if src_width and dst_width and edge_width:
                if edge_width != src_width or edge_width != dst_width:
                    width_mismatches.append((
                        src_node.get('name'),
                        dst_node.get('name'),
                        src_width,
                        dst_width,
                        edge_width
                    ))

        if width_mismatches:
            print(f"\n5. ⚠️  Found {len(width_mismatches)} potential width mismatches:")
            for src_name, dst_name, src_w, dst_w, edge_w in width_mismatches[:5]:
                print(f"   {src_name}({src_w}) -> {dst_name}({dst_w}), edge={edge_w}")
            # This is a warning, not an error
        else:
            print(f"\n5. ✓ No width mismatches detected")

        # Step 6: Summary
        print(f"\n6. ✓ Verification PASSED")

        if node_types.get('ClockConverter', 0) > 0 or node_types.get('WidthConverter', 0) > 0:
            print(f"\n   Converters inserted:")
            if node_types.get('ClockConverter', 0) > 0:
                print(f"   - ClockConverter: {node_types['ClockConverter']}")
            if node_types.get('WidthConverter', 0) > 0:
                print(f"   - WidthConverter: {node_types['WidthConverter']}")

        return True

    except Exception as e:
        print(f"\n✗ Verification FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Verify all small topology examples"""
    print("="*70)
    print("PyMTL3-Net Irregular Topology Tool Flow Verification")
    print("="*70)
    print("\nThis script demonstrates the complete tool flow:")
    print("1. User creates topology YAML (may have clock/width mismatches)")
    print("2. TopologyLoader automatically inserts converters")
    print("3. Validation ensures topology is correct")
    print("4. Ready for PyMTL3 network generation")

    # Find all small examples
    small_examples = sorted(glob.glob('small/*.yml'))

    if not small_examples:
        print("\nError: No small examples found. Run from examples/ directory.")
        return 1

    results = {}

    # Test with auto-insertion DISABLED first (to show what user provided)
    print(f"\n\n{'='*70}")
    print("Phase 1: Testing WITHOUT auto-converter insertion")
    print("(Shows the original user-provided topology)")
    print(f"{'='*70}")

    for yaml_path in small_examples[:3]:  # Test first 3
        print(f"\nTesting {yaml_path} (auto-insert=False)...")
        result = verify_topology(yaml_path, auto_insert=False)
        results[yaml_path + '_manual'] = result

    # Test with auto-insertion ENABLED
    print(f"\n\n{'='*70}")
    print("Phase 2: Testing WITH auto-converter insertion")
    print("(Shows how the tool automatically fixes issues)")
    print(f"{'='*70}")

    for yaml_path in small_examples[:5]:  # Test first 5
        print(f"\nTesting {yaml_path} (auto-insert=True)...")
        result = verify_topology(yaml_path, auto_insert=True)
        results[yaml_path + '_auto'] = result

    # Summary
    print(f"\n\n{'='*70}")
    print("VERIFICATION SUMMARY")
    print(f"{'='*70}")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    print(f"\nTotal tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")

    if passed == total:
        print(f"\n✓ All verifications PASSED!")
        print(f"\nThe tool flow is working correctly:")
        print(f"  1. YAML files can be loaded")
        print(f"  2. Converters are automatically inserted")
        print(f"  3. Topologies are properly validated")
        return 0
    else:
        print(f"\n✗ Some verifications FAILED")
        return 1


if __name__ == '__main__':
    # Change to examples directory if not already there
    if os.path.basename(os.getcwd()) != 'examples':
        examples_dir = os.path.join(os.path.dirname(__file__), '.')
        if os.path.exists(examples_dir):
            os.chdir(examples_dir)

    sys.exit(main())
