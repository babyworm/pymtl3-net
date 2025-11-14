#!/usr/bin/env python3
"""
Test topology generator with simple specification
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pymtl3_net.irregnet.topology_generator import generate_topology
from pymtl3_net.irregnet.topology_loader import TopologyLoader


def test_simple_soc():
    """Test generating topology from simple specification"""
    print("\n" + "="*70)
    print("TEST: Generate topology from simple_soc.yml")
    print("="*70)

    # Generate topology
    gen = generate_topology(
        spec_path='examples/simple_specs/simple_soc.yml',
        output_path='examples/simple_specs/simple_soc_generated.yml',
        optimize=True
    )

    print("\n" + "="*70)
    print("TEST: Load generated topology with auto-converter insertion")
    print("="*70)

    # Load the generated topology with auto-converter insertion
    loader = TopologyLoader(
        'examples/simple_specs/simple_soc_generated.yml',
        auto_insert_converters=True
    )

    print(f"\nAfter auto-converter insertion:")
    print(f"  Nodes: {len(loader.nodes)} (was {len(gen.nodes)})")
    print(f"  Edges: {len(loader.edges)} (was {len(gen.edges)})")

    # Count converters
    cdc_count = sum(1 for n in loader.nodes if n.type == 'ClockConverter')
    wc_count = sum(1 for n in loader.nodes if n.type == 'WidthConverter')

    if cdc_count > 0 or wc_count > 0:
        print(f"\n  Auto-inserted converters:")
        if cdc_count > 0:
            print(f"    ClockConverter: {cdc_count}")
        if wc_count > 0:
            print(f"    WidthConverter: {wc_count}")

    # Validate
    G = loader.get_networkx_graph()
    print(f"\n  NetworkX graph:")
    print(f"    Nodes: {G.number_of_nodes()}")
    print(f"    Edges: {G.number_of_edges()}")

    # Check connectivity
    import networkx as nx
    if nx.is_weakly_connected(G):
        print(f"    ✓ Graph is connected")
    else:
        print(f"    ✗ Graph has disconnected components")
        return False

    print(f"\n✓ TEST PASSED: Simple SoC topology generated and validated")
    return True


def main():
    """Run all tests"""
    print("="*70)
    print("Topology Generator Test Suite")
    print("="*70)

    try:
        result = test_simple_soc()
        if result:
            print("\n" + "="*70)
            print("ALL TESTS PASSED!")
            print("="*70)
            print("\nGenerated topology file:")
            print("  examples/simple_specs/simple_soc_generated.yml")
            print("\nNext steps:")
            print("  1. Inspect the generated topology")
            print("  2. Visualize with vis.js")
            print("  3. Run performance simulation")
            return 0
        else:
            print("\n" + "="*70)
            print("TESTS FAILED")
            print("="*70)
            return 1

    except Exception as e:
        print(f"\n✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
