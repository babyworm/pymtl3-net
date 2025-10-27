#!/usr/bin/env python3
"""
Comprehensive verification of constraint-based optimization
"""

import yaml
from pymtl3_net.irregnet.topology_optimizer import optimize_topology


def verify_connectivity_preserved():
    """
    핵심 검증: 모든 connectivity constraint가 보존되는가?
    """
    print("="*70)
    print("검증 1: Connectivity Constraint 보존 확인")
    print("="*70)

    with open('examples/simple_specs/ai_cluster_v2.yml') as f:
        spec = yaml.safe_load(f)

    flows = spec['traffic_flows']
    weights = spec['optimization']['weights']

    print(f"\n입력 Spec:")
    print(f"  - Traffic flows: {len(flows)}개")
    print(f"  - 이 모든 연결은 MUST 보존되어야 함\n")

    # 중요한 연결들 출력
    print("예시 connectivity constraints:")
    important_flows = [
        ('AI0', 'HBM0', 150.0),
        ('AI0', 'DDR0', 5.0),   # AI0는 HBM0 AND DDR0 둘 다!
        ('CPU0', 'DDR0', 2.0),
        ('CPU0', 'DDR1', 1.0),  # CPU0는 DDR0 AND DDR1 둘 다!
    ]

    for src, dst, bw in important_flows:
        print(f"  {src} → {dst}: {bw} GB/s")

    # Optimization 실행
    print(f"\n최적화 실행 중...")
    optimizer = optimize_topology(flows, weights)

    # 검증: 모든 flow가 구현되었는가?
    print(f"\n" + "="*70)
    print("검증 결과:")
    print("="*70)

    missing = []
    for flow in flows:
        flow_id = (flow['src'], flow['dst'])
        if flow_id not in optimizer.selected_impl:
            missing.append(flow_id)

    if missing:
        print(f"❌ FAILED: {len(missing)}개 연결이 누락됨!")
        for src, dst in missing:
            print(f"  - {src} → {dst}")
        return False
    else:
        print(f"✓ PASSED: 모든 {len(flows)}개 connectivity constraints 보존됨!")

    # 중요한 flow들 확인
    print(f"\n중요 연결 구현 확인:")
    for src, dst, bw in important_flows:
        flow_id = (src, dst)
        impl = optimizer.selected_impl[flow_id]
        print(f"  {src} → {dst}:")
        print(f"    Required: {bw} GB/s")
        print(f"    Implementation: {impl.impl_type.value}")
        print(f"    Latency: {impl.latency_cycles} cycles")

    return True


def verify_no_connection_removal():
    """
    검증: Optimization이 연결을 제거하지 않는가?
    """
    print("\n" + "="*70)
    print("검증 2: 연결 제거 없음 확인")
    print("="*70)

    with open('examples/simple_specs/ai_cluster_v2.yml') as f:
        spec = yaml.safe_load(f)

    flows = spec['traffic_flows']
    weights = spec['optimization']['weights']

    # Before optimization
    before_connectivity = set((f['src'], f['dst']) for f in flows)
    print(f"\nBefore optimization:")
    print(f"  Connectivity graph: {len(before_connectivity)}개 edge")

    # Run optimization
    optimizer = optimize_topology(flows, weights)

    # After optimization
    after_connectivity = set(optimizer.selected_impl.keys())
    print(f"\nAfter optimization:")
    print(f"  Connectivity graph: {len(after_connectivity)}개 edge")

    # Compare
    if before_connectivity == after_connectivity:
        print(f"\n✓ PASSED: Connectivity 동일 (연결 제거 없음)")
        return True
    else:
        removed = before_connectivity - after_connectivity
        added = after_connectivity - before_connectivity
        print(f"\n❌ FAILED: Connectivity 변경됨!")
        if removed:
            print(f"  제거된 연결: {removed}")
        if added:
            print(f"  추가된 연결: {added}")
        return False


def verify_multi_access():
    """
    검증: 하나의 initiator가 여러 target에 접근 가능한가?
    """
    print("\n" + "="*70)
    print("검증 3: Multi-Target Access 확인")
    print("="*70)

    with open('examples/simple_specs/ai_cluster_v2.yml') as f:
        spec = yaml.safe_load(f)

    flows = spec['traffic_flows']
    weights = spec['optimization']['weights']

    # Run optimization
    optimizer = optimize_topology(flows, weights)

    # Check AI0 can access both HBM0 and DDR0
    print(f"\nAI0의 target 접근성:")
    ai0_targets = [(dst, impl.impl_type.value)
                   for (src, dst), impl in optimizer.selected_impl.items()
                   if src == 'AI0']

    for dst, impl in ai0_targets:
        print(f"  → {dst} ({impl})")

    if len(ai0_targets) >= 2:
        print(f"✓ PASSED: AI0는 {len(ai0_targets)}개 target 접근 가능")
    else:
        print(f"❌ FAILED: AI0는 {len(ai0_targets)}개 target만 접근 (최소 2개 필요)")
        return False

    # Check CPU0 can access both DDR0 and DDR1
    print(f"\nCPU0의 target 접근성:")
    cpu0_targets = [(dst, impl.impl_type.value)
                    for (src, dst), impl in optimizer.selected_impl.items()
                    if src == 'CPU0']

    for dst, impl in cpu0_targets:
        print(f"  → {dst} ({impl})")

    if len(cpu0_targets) >= 2:
        print(f"✓ PASSED: CPU0는 {len(cpu0_targets)}개 target 접근 가능")
        return True
    else:
        print(f"❌ FAILED: CPU0는 {len(cpu0_targets)}개 target만 접근")
        return False


def verify_weight_effects():
    """
    검증: Weight가 실제로 구현 선택에 영향을 주는가?
    """
    print("\n" + "="*70)
    print("검증 4: Weight 영향 확인")
    print("="*70)

    with open('examples/simple_specs/ai_cluster_v2.yml') as f:
        spec = yaml.safe_load(f)

    flows = spec['traffic_flows']

    # Test 3 different weight profiles
    profiles = [
        {
            'name': 'Throughput 최우선',
            'weights': {'throughput': 0.8, 'latency': 0.15, 'area': 0.05}
        },
        {
            'name': 'Area 최우선',
            'weights': {'throughput': 0.3, 'latency': 0.2, 'area': 0.5}
        }
    ]

    results = []

    for profile in profiles:
        print(f"\n{profile['name']} (T:{profile['weights']['throughput']:.1f}, "
              f"L:{profile['weights']['latency']:.1f}, A:{profile['weights']['area']:.1f}):")

        optimizer = optimize_topology(flows, profile['weights'])
        summary = optimizer.get_optimization_summary()

        results.append({
            'name': profile['name'],
            'dedicated': summary['dedicated_paths'],
            'area': summary['total_area_cost']
        })

        print(f"  Dedicated paths: {summary['dedicated_paths']}")
        print(f"  Total area: {summary['total_area_cost']:.1f}")

    # Compare
    print(f"\n비교:")
    if results[0]['dedicated'] != results[1]['dedicated']:
        print(f"  Throughput 최우선: {results[0]['dedicated']} dedicated paths")
        print(f"  Area 최우선: {results[1]['dedicated']} dedicated paths")
        print(f"✓ PASSED: Weight가 구현 선택에 영향을 줌")
        return True
    else:
        print(f"❌ FAILED: Weight가 결과에 영향 없음")
        return False


def verify_implementation_options():
    """
    검증: 각 flow에 대해 여러 구현 옵션이 생성되는가?
    """
    print("\n" + "="*70)
    print("검증 5: Implementation Options 생성 확인")
    print("="*70)

    with open('examples/simple_specs/ai_cluster_v2.yml') as f:
        spec = yaml.safe_load(f)

    flows = spec['traffic_flows']
    weights = spec['optimization']['weights']

    from pymtl3_net.irregnet.topology_optimizer import TopologyOptimizer

    optimizer = TopologyOptimizer(flows, weights)
    optimizer.generate_implementation_options()

    print(f"\nImplementation options per flow:")

    # Check high-BW flow (should have multiple options)
    ai0_hbm0 = [f for f in flows if f['src'] == 'AI0' and f['dst'] == 'HBM0'][0]
    flow_id = (ai0_hbm0['src'], ai0_hbm0['dst'])
    options = optimizer.flow_options.get(flow_id, [])

    print(f"\nAI0 → HBM0 (150 GB/s):")
    for opt in options:
        print(f"  - {opt.impl_type.value}: throughput={opt.throughput_score:.1f}, "
              f"latency={opt.latency_cycles}, area={opt.area_cost:.1f}")

    if len(options) >= 2:
        print(f"✓ PASSED: {len(options)}개 구현 옵션 생성됨")
    else:
        print(f"❌ FAILED: 옵션이 {len(options)}개만 생성됨 (최소 2개 필요)")
        return False

    # Check low-BW flow (should have even more options)
    cpu0_ddr0 = [f for f in flows if f['src'] == 'CPU0' and f['dst'] == 'DDR0'][0]
    flow_id = (cpu0_ddr0['src'], cpu0_ddr0['dst'])
    options = optimizer.flow_options.get(flow_id, [])

    print(f"\nCPU0 → DDR0 (2 GB/s):")
    for opt in options:
        print(f"  - {opt.impl_type.value}: throughput={opt.throughput_score:.1f}, "
              f"latency={opt.latency_cycles}, area={opt.area_cost:.1f}")

    if len(options) >= 2:
        print(f"✓ PASSED: {len(options)}개 구현 옵션 생성됨")
        return True
    else:
        print(f"❌ FAILED: 옵션이 부족함")
        return False


def main():
    """Run all verifications"""
    print("\n" + "="*70)
    print("CONSTRAINT-BASED OPTIMIZATION 종합 검증")
    print("="*70)

    results = []

    # Test 1: Connectivity preserved
    try:
        results.append(("Connectivity 보존", verify_connectivity_preserved()))
    except Exception as e:
        print(f"\n❌ Test 1 ERROR: {e}")
        results.append(("Connectivity 보존", False))

    # Test 2: No connection removal
    try:
        results.append(("연결 제거 없음", verify_no_connection_removal()))
    except Exception as e:
        print(f"\n❌ Test 2 ERROR: {e}")
        results.append(("연결 제거 없음", False))

    # Test 3: Multi-target access
    try:
        results.append(("Multi-target access", verify_multi_access()))
    except Exception as e:
        print(f"\n❌ Test 3 ERROR: {e}")
        results.append(("Multi-target access", False))

    # Test 4: Weight effects
    try:
        results.append(("Weight 영향", verify_weight_effects()))
    except Exception as e:
        print(f"\n❌ Test 4 ERROR: {e}")
        results.append(("Weight 영향", False))

    # Test 5: Implementation options
    try:
        results.append(("구현 옵션 생성", verify_implementation_options()))
    except Exception as e:
        print(f"\n❌ Test 5 ERROR: {e}")
        results.append(("구현 옵션 생성", False))

    # Summary
    print("\n" + "="*70)
    print("검증 결과 요약")
    print("="*70)

    for name, passed in results:
        status = "✓ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {name}")

    passed = sum(1 for _, p in results if p)
    total = len(results)

    print(f"\n총 {total}개 테스트 중 {passed}개 통과")

    if passed == total:
        print("\n" + "="*70)
        print("🎉 모든 검증 통과!")
        print("="*70)
        print("\nConstraint-based optimization이 올바르게 작동합니다:")
        print("  ✓ Connectivity constraints 100% 보존")
        print("  ✓ 연결 제거 없음")
        print("  ✓ Multi-target access 가능")
        print("  ✓ Weight가 결과에 영향")
        print("  ✓ 구현 옵션 제대로 생성")
        return 0
    else:
        print(f"\n❌ {total - passed}개 테스트 실패")
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
