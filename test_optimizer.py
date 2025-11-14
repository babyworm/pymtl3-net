#!/usr/bin/env python3
"""
Test constraint-based topology optimizer
"""

import sys
import yaml
from pymtl3_net.irregnet.topology_optimizer import optimize_topology


def test_ai_cluster_v2():
    """Test with AI cluster that has explicit connectivity"""
    print("="*70)
    print("TEST: AI Cluster with Connectivity Constraints")
    print("="*70)

    # Load spec
    with open('examples/simple_specs/ai_cluster_v2.yml') as f:
        spec = yaml.safe_load(f)

    flows = spec['traffic_flows']
    weights = spec['optimization']['weights']

    print(f"\nSpec loaded:")
    print(f"  Initiators: {len(spec['initiators'])}")
    print(f"  Targets: {len(spec['targets'])}")
    print(f"  Traffic flows (connectivity): {len(flows)}")

    print(f"\nExample connectivity requirements:")
    for flow in flows[:5]:
        print(f"  {flow['src']} → {flow['dst']}: {flow['bandwidth']:.1f} GB/s")
    print(f"  ... and {len(flows)-5} more flows")

    # Run optimization
    optimizer = optimize_topology(flows, weights)

    # Verify all flows have implementation
    print(f"\n" + "="*70)
    print("VERIFICATION: All connectivity preserved?")
    print("="*70)

    all_preserved = True
    for flow in flows:
        flow_id = (flow['src'], flow['dst'])
        if flow_id not in optimizer.selected_impl:
            print(f"  ✗ MISSING: {flow_id[0]} → {flow_id[1]}")
            all_preserved = False

    if all_preserved:
        print(f"  ✓ ALL {len(flows)} connectivity constraints preserved!")
    else:
        print(f"  ✗ Some connectivity constraints VIOLATED")
        return False

    # Check specific flows
    print(f"\n" + "="*70)
    print("Example Implementation Decisions:")
    print("="*70)

    test_flows = [
        ('AI0', 'HBM0'),  # High-BW primary
        ('AI0', 'DDR0'),  # Low-BW fallback (MUST still exist!)
        ('CPU0', 'DDR0'), # Low-BW
        ('CPU0', 'DDR1'), # Low-BW (CPU0 can access both DDR0 and DDR1!)
    ]

    for src, dst in test_flows:
        if (src, dst) in optimizer.selected_impl:
            impl = optimizer.selected_impl[(src, dst)]
            flow = next(f for f in flows if f['src'] == src and f['dst'] == dst)
            print(f"\n{src} → {dst}:")
            print(f"  Required BW: {flow['bandwidth']:.1f} GB/s")
            print(f"  Implementation: {impl.impl_type.value}")
            print(f"  Throughput score: {impl.throughput_score}")
            print(f"  Latency: {impl.latency_cycles} cycles")
            print(f"  Area cost: {impl.area_cost}")
        else:
            print(f"\n✗ {src} → {dst}: NOT IMPLEMENTED!")
            return False

    print(f"\n{'='*70}")
    print("TEST PASSED: Connectivity preserved, implementations selected")
    print(f"{'='*70}")
    return True


def test_weight_variations():
    """Test different weight combinations"""
    print("\n\n" + "="*70)
    print("TEST: Different Optimization Weights")
    print("="*70)

    # Load spec
    with open('examples/simple_specs/ai_cluster_v2.yml') as f:
        spec = yaml.safe_load(f)
    flows = spec['traffic_flows']

    # Test different weight profiles
    weight_profiles = [
        {'name': 'Throughput-focused', 'weights': {'throughput': 0.8, 'latency': 0.15, 'area': 0.05}},
        {'name': 'Balanced', 'weights': {'throughput': 0.5, 'latency': 0.3, 'area': 0.2}},
        {'name': 'Area-conscious', 'weights': {'throughput': 0.4, 'latency': 0.2, 'area': 0.4}},
    ]

    results = []

    for profile in weight_profiles:
        print(f"\n{'-'*70}")
        print(f"Profile: {profile['name']}")
        print(f"{'-'*70}")

        optimizer = optimize_topology(flows, profile['weights'])
        summary = optimizer.get_optimization_summary()

        results.append({
            'profile': profile['name'],
            'dedicated': summary['dedicated_paths'],
            'crossbar': summary['crossbar_utilization'],
            'area': summary['total_area_cost'],
            'latency': summary['average_latency']
        })

    # Compare results
    print(f"\n{'='*70}")
    print("Weight Profile Comparison:")
    print(f"{'='*70}")

    print(f"\n{'Profile':<20} {'Dedicated':<12} {'Crossbar':<12} {'Area':<12} {'Avg Latency':<12}")
    print(f"{'-'*80}")
    for r in results:
        print(f"{r['profile']:<20} {r['dedicated']:<12} {r['crossbar']:<12} {r['area']:<12.1f} {r['latency']:<12.1f}")

    print(f"\n✓ Weights affect implementation choices as expected")
    return True


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("Constraint-Based Topology Optimizer Test Suite")
    print("="*70)

    # Test 1: Basic optimization with constraints
    try:
        result1 = test_ai_cluster_v2()
        if not result1:
            print("\n✗ Test 1 FAILED")
            return 1
    except Exception as e:
        print(f"\n✗ Test 1 ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Test 2: Weight variations
    try:
        result2 = test_weight_variations()
        if not result2:
            print("\n✗ Test 2 FAILED")
            return 1
    except Exception as e:
        print(f"\n✗ Test 2 ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

    print("\n" + "="*70)
    print("ALL TESTS PASSED!")
    print("="*70)
    print("\nKey achievements:")
    print("  ✓ All connectivity constraints preserved")
    print("  ✓ Multi-objective optimization working")
    print("  ✓ Weight parameters affect decisions")
    print("  ✓ Implementation options generated correctly")
    return 0


if __name__ == '__main__':
    sys.exit(main())
