#!/usr/bin/env python3
"""
Validate all NoC topology examples
"""

import yaml
from pathlib import Path
from collections import Counter

def validate_topology(filepath):
    """Validate a single topology file"""
    with open(filepath, 'r') as f:
        config = yaml.safe_load(f)

    nodes = config.get('nodes', [])
    edges = config.get('graph', {}).get('edges', [])
    constraints = config.get('constraints', {})

    issues = []
    warnings = []

    # 1. Check num_nodes
    declared_nodes = config.get('num_nodes', 0)
    actual_nodes = len(nodes)
    if declared_nodes != actual_nodes:
        issues.append(f"num_nodes mismatch: declared={declared_nodes}, actual={actual_nodes}")

    # Create node lookup
    node_map = {n['id']: n for n in nodes}

    # 2. Check Arbiter inputs
    for node in nodes:
        if node['type'] == 'Arbiter':
            expected = node.get('num_inputs', 0)
            actual = len([e for e in edges if e['dst'] == node['id']])
            if expected != actual:
                issues.append(f"Arbiter {node['name']}: expected {expected} inputs, got {actual}")

    # 3. Check Decoder outputs
    for node in nodes:
        if node['type'] == 'Decoder':
            expected = node.get('num_outputs', 0)
            actual = len([e for e in edges if e['src'] == node['id']])
            if expected != actual:
                issues.append(f"Decoder {node['name']}: expected {expected} outputs, got {actual}")

    # 4. Check Router port counts
    for node in nodes:
        if node['type'] == 'Router':
            num_ports = node.get('num_ports', 0)
            incoming = len([e for e in edges if e['dst'] == node['id']])
            outgoing = len([e for e in edges if e['src'] == node['id']])
            total = incoming + outgoing
            if total > num_ports:
                issues.append(f"Router {node['name']}: {total} connections > {num_ports} ports")

    # 5. Check width consistency
    if constraints.get('enforce_width_match', False):
        for edge in edges:
            src = node_map.get(edge['src'])
            dst = node_map.get(edge['dst'])
            edge_width = edge.get('width')

            if not src or not dst:
                continue

            # Skip converters
            if src['type'] in ['WidthConverter', 'ClockConverter']:
                continue
            if dst['type'] in ['WidthConverter', 'ClockConverter']:
                continue

            src_width = src.get('width')
            dst_width = dst.get('width')

            if src_width and edge_width and src_width != edge_width:
                issues.append(f"Width mismatch: {src['name']}({src_width}) → edge({edge_width})")

            if dst_width and edge_width and dst_width != edge_width:
                issues.append(f"Width mismatch: edge({edge_width}) → {dst['name']}({dst_width})")

    # 6. Check clock domain crossings
    for edge in edges:
        src = node_map.get(edge['src'])
        dst = node_map.get(edge['dst'])

        if not src or not dst:
            continue

        # Skip converters
        if src['type'] == 'ClockConverter' or dst['type'] == 'ClockConverter':
            continue

        src_domain = src.get('clock_domain')
        dst_domain = dst.get('clock_domain')

        if src_domain and dst_domain and src_domain != dst_domain:
            warnings.append(f"Clock crossing: {src['name']}({src_domain}) → {dst['name']}({dst_domain})")

    # 7. Check Initiator → NIU connections
    for node in nodes:
        if node['type'] == 'Initiator':
            outgoing = [e for e in edges if e['src'] == node['id']]
            if not outgoing:
                issues.append(f"Initiator {node['name']} has no connections")
            else:
                for e in outgoing:
                    dst = node_map.get(e['dst'])
                    if dst and dst['type'] != 'NIU':
                        issues.append(f"Initiator {node['name']} connects to {dst['name']} (not NIU)")

    # 8. Check Target connections
    for node in nodes:
        if node['type'] == 'Target':
            incoming = [e for e in edges if e['dst'] == node['id']]
            if not incoming:
                issues.append(f"Target {node['name']} has no connections")
            else:
                for e in incoming:
                    src = node_map.get(e['src'])
                    if src and src['type'] != 'NIU':
                        issues.append(f"Target {node['name']} receives from {src['name']} (not NIU)")

    return issues, warnings

def main():
    """Validate all examples"""
    examples_dir = Path('.')
    all_issues = {}
    all_warnings = {}

    total_files = 0
    files_with_issues = 0
    files_with_warnings = 0

    for scale in ['small', 'medium', 'large']:
        scale_dir = examples_dir / scale

        if not scale_dir.exists():
            continue

        for yaml_file in sorted(scale_dir.glob('*.yml')):
            total_files += 1
            issues, warnings = validate_topology(yaml_file)

            if issues:
                all_issues[str(yaml_file)] = issues
                files_with_issues += 1

            if warnings:
                all_warnings[str(yaml_file)] = warnings
                files_with_warnings += 1

    # Print results
    print("="*80)
    print("NoC Topology Validation Report")
    print("="*80)
    print(f"\nTotal files validated: {total_files}")
    print(f"Files with issues: {files_with_issues}")
    print(f"Files with warnings: {files_with_warnings}")
    print(f"Files OK: {total_files - files_with_issues - files_with_warnings}")

    if all_issues:
        print("\n" + "="*80)
        print("❌ ISSUES (Must Fix)")
        print("="*80)
        for filepath, issues in sorted(all_issues.items()):
            print(f"\n📁 {filepath}")
            for issue in issues:
                print(f"  ❌ {issue}")

    if all_warnings:
        print("\n" + "="*80)
        print("⚠️  WARNINGS (Review Needed)")
        print("="*80)
        for filepath, warnings in sorted(all_warnings.items()):
            print(f"\n📁 {filepath}")
            for warning in warnings:
                print(f"  ⚠️  {warning}")

    if not all_issues and not all_warnings:
        print("\n✅ All topologies validated successfully!")

    return len(all_issues)

if __name__ == '__main__':
    exit(main())
