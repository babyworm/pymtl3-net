"""
=========================================================================
topology_generator.py
=========================================================================
Generate NoC topology from simple high-level specification.

Users only specify:
- Initiators (traffic generators)
- Targets (memory/peripherals)
- Traffic requirements (bandwidth, latency)

The tool automatically generates:
- NIUs for each initiator/target
- Full crossbar or optimized topology
- Routers, Arbiters, Decoders as needed
- Proper clock domains and data widths

Author : Claude Code
  Date : 2025-10-26
"""

import yaml
import networkx as nx
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, field
import math


@dataclass
class Initiator:
    """Traffic generator specification"""
    name: str
    type: str
    avg_throughput: float  # GB/s
    max_throughput: float
    latency_req: int       # cycles
    priority: int


@dataclass
class Target:
    """Memory/peripheral target specification"""
    name: str
    type: str
    max_bandwidth: float   # GB/s
    latency: int           # cycles
    size: float            # GB


@dataclass
class TrafficFlow:
    """Traffic requirement between initiator and target"""
    src: str               # Initiator name
    dst: str               # Target name
    bandwidth: float       # GB/s guaranteed
    max_latency: int       # cycles
    priority: int


class TopologyGenerator:
    """
    Generate NoC topology from high-level specification.

    Strategy:
    1. Create NIUs for all initiators and targets
    2. Generate full crossbar connectivity
    3. Optimize based on bandwidth requirements
    4. Insert routers/arbiters/decoders as needed
    """

    def __init__(self, spec_path: str):
        """Load specification from YAML"""
        with open(spec_path, 'r') as f:
            self.spec = yaml.safe_load(f)

        # Parse specification
        self.initiators = self._parse_initiators()
        self.targets = self._parse_targets()
        self.traffic_flows = self._parse_traffic_flows()
        self.constraints = self.spec.get('constraints', {})

        # Generated topology
        self.nodes = []
        self.edges = []
        self.node_id = 0

        # Node name to ID mapping
        self.node_map = {}

    def _parse_initiators(self) -> List[Initiator]:
        """Parse initiator specifications"""
        result = []
        for init_spec in self.spec.get('initiators', []):
            result.append(Initiator(
                name=init_spec['name'],
                type=init_spec['type'],
                avg_throughput=init_spec['avg_throughput'],
                max_throughput=init_spec['max_throughput'],
                latency_req=init_spec['latency_req'],
                priority=init_spec['priority']
            ))
        return result

    def _parse_targets(self) -> List[Target]:
        """Parse target specifications"""
        result = []
        for tgt_spec in self.spec.get('targets', []):
            result.append(Target(
                name=tgt_spec['name'],
                type=tgt_spec['type'],
                max_bandwidth=tgt_spec['max_bandwidth'],
                latency=tgt_spec['latency'],
                size=tgt_spec['size']
            ))
        return result

    def _parse_traffic_flows(self) -> List[TrafficFlow]:
        """Parse traffic flow requirements"""
        result = []
        for flow_spec in self.spec.get('traffic_flows', []):
            result.append(TrafficFlow(
                src=flow_spec['src'],
                dst=flow_spec['dst'],
                bandwidth=flow_spec['bandwidth'],
                max_latency=flow_spec['max_latency'],
                priority=flow_spec['priority']
            ))
        return result

    def _add_node(self, node_type: str, name: str, **attributes) -> int:
        """Add a node and return its ID"""
        node_id = self.node_id
        self.node_id += 1

        self.nodes.append({
            'id': node_id,
            'type': node_type,
            'name': name,
            **attributes
        })

        self.node_map[name] = node_id
        return node_id

    def _add_edge(self, src_id: int, dst_id: int, width: int, latency: int):
        """Add an edge"""
        self.edges.append({
            'src': src_id,
            'dst': dst_id,
            'width': width,
            'latency': latency
        })

    def _get_clock_domain(self, node_type: str, throughput: float = 0) -> str:
        """Determine clock domain based on node type and throughput"""
        # High-bandwidth nodes go to fast clock domain
        if throughput > 10.0:  # > 10 GB/s
            return 'fast'
        else:
            return 'slow' if throughput < 2.0 else 'fast'

    def _calculate_width(self, bandwidth: float, frequency: float) -> int:
        """Calculate required data width in bits for given bandwidth"""
        # bandwidth (GB/s) = width (bits) * frequency (MHz) / 8 / 1000
        # width = bandwidth * 8 * 1000 / frequency

        required_bits = bandwidth * 8 * 1000 / frequency

        # Round up to nearest power of 2: 32, 64, 128, 256
        for width in [32, 64, 128, 256, 512]:
            if width >= required_bits:
                return width
        return 512

    def generate_full_crossbar(self):
        """
        Generate full crossbar topology.

        Structure:
        - Each Initiator → NIU → Crossbar Router → NIU → Target
        - Full connectivity (every initiator can reach every target)
        """
        print("Generating full crossbar topology...")

        default_width = self.constraints.get('default_data_width', 64)
        default_freq = 2000  # MHz

        # Get clock domains
        clock_domains = {cd['name']: cd['frequency']
                        for cd in self.constraints.get('clock_domains', [])}

        # 1. Create Initiator nodes and their NIUs
        print(f"\nCreating {len(self.initiators)} initiators...")
        for init in self.initiators:
            # Add Initiator node
            init_id = self._add_node(
                'Initiator',
                init.name,
                avg_throughput=init.avg_throughput,
                max_throughput=init.max_throughput,
                latency_requirement=init.latency_req,
                priority=init.priority,
                traffic_pattern='bursty'
            )

            # Add NIU for this initiator
            clk_domain = self._get_clock_domain('Initiator', init.max_throughput)
            freq = clock_domains.get(clk_domain, default_freq)
            width = self._calculate_width(init.max_throughput, freq)

            niu_id = self._add_node(
                'NIU',
                f'{init.name}_NIU',
                width=width,
                clock_domain=clk_domain
            )

            # Connect Initiator → NIU
            self._add_edge(init_id, niu_id, width, 1)

            print(f"  {init.name} → {init.name}_NIU ({width}-bit, {clk_domain})")

        # 2. Create Target nodes and their NIUs
        print(f"\nCreating {len(self.targets)} targets...")
        for tgt in self.targets:
            # Add Target node
            tgt_id = self._add_node(
                'Target',
                tgt.name,
                max_bandwidth=tgt.max_bandwidth,
                latency=tgt.latency,
                size=tgt.size,
                type_detail=tgt.type
            )

            # Add NIU for this target
            clk_domain = self._get_clock_domain('Target', tgt.max_bandwidth)
            freq = clock_domains.get(clk_domain, default_freq)
            width = self._calculate_width(tgt.max_bandwidth, freq)

            niu_id = self._add_node(
                'NIU',
                f'{tgt.name}_NIU',
                width=width,
                clock_domain=clk_domain
            )

            # Connect NIU → Target
            self._add_edge(niu_id, tgt_id, width, tgt.latency // 10)

            print(f"  {tgt.name}_NIU → {tgt.name} ({width}-bit, {clk_domain})")

        # 3. Create central crossbar router
        print(f"\nCreating central crossbar router...")

        # Calculate max width needed for crossbar
        max_width = max(
            [self._calculate_width(init.max_throughput, default_freq)
             for init in self.initiators] +
            [self._calculate_width(tgt.max_bandwidth, default_freq)
             for tgt in self.targets]
        )

        num_ports = len(self.initiators) + len(self.targets)

        router_id = self._add_node(
            'Router',
            'Crossbar',
            width=max_width,
            clock_domain='fast',
            num_ports=num_ports
        )

        print(f"  Crossbar: {max_width}-bit, {num_ports} ports")

        # 4. Connect all Initiator NIUs → Crossbar
        print(f"\nConnecting {len(self.initiators)} initiators to crossbar...")
        for init in self.initiators:
            niu_id = self.node_map[f'{init.name}_NIU']
            niu_node = next(n for n in self.nodes if n['id'] == niu_id)
            width = niu_node['width']

            self._add_edge(niu_id, router_id, width, 2)

        # 5. Connect Crossbar → all Target NIUs
        print(f"Connecting crossbar to {len(self.targets)} targets...")
        for tgt in self.targets:
            niu_id = self.node_map[f'{tgt.name}_NIU']
            niu_node = next(n for n in self.nodes if n['id'] == niu_id)
            width = niu_node['width']

            self._add_edge(router_id, niu_id, width, 2)

        print(f"\n✓ Full crossbar generated:")
        print(f"  Total nodes: {len(self.nodes)}")
        print(f"  Total edges: {len(self.edges)}")
        print(f"  Connectivity: {len(self.initiators)} initiators × {len(self.targets)} targets")

    def optimize_bandwidth(self):
        """
        Optimize topology based on bandwidth requirements.

        Strategy:
        1. Analyze traffic flows and categorize
        2. High-BW flows (>50 GB/s): Add dedicated routers
        3. Medium-BW flows (5-50 GB/s): Keep crossbar
        4. Low-BW flows (<5 GB/s): Group with arbiters
        5. Measure optimization impact
        """
        print("\n" + "="*70)
        print("Optimizing for bandwidth...")
        print("="*70)

        # Store original metrics
        original_nodes = len(self.nodes)
        original_edges = len(self.edges)
        crossbar_id = self.node_map.get('Crossbar')

        if not crossbar_id:
            print("  No crossbar found, skipping optimization")
            return

        # Analyze traffic flows
        flow_map = {}  # (src, dst) -> bandwidth
        for flow in self.traffic_flows:
            key = (flow.src, flow.dst)
            flow_map[key] = flow_map.get(key, 0) + flow.bandwidth

        # Categorize flows
        high_bw_threshold = 50.0  # GB/s - dedicated path
        low_bw_threshold = 5.0    # GB/s - shared with arbiter

        high_bw_flows = [(src, dst, bw) for (src, dst), bw in flow_map.items()
                         if bw >= high_bw_threshold]
        medium_bw_flows = [(src, dst, bw) for (src, dst), bw in flow_map.items()
                          if low_bw_threshold <= bw < high_bw_threshold]
        low_bw_flows = [(src, dst, bw) for (src, dst), bw in flow_map.items()
                        if bw < low_bw_threshold]

        print(f"\nTraffic flow categorization:")
        print(f"  High-BW (>= {high_bw_threshold} GB/s): {len(high_bw_flows)} flows")
        print(f"  Medium-BW ({low_bw_threshold}-{high_bw_threshold} GB/s): {len(medium_bw_flows)} flows")
        print(f"  Low-BW (< {low_bw_threshold} GB/s): {len(low_bw_flows)} flows")

        # Optimization 1: Add dedicated routers for high-BW flows
        if high_bw_flows:
            print(f"\n1. Adding dedicated paths for high-BW flows...")
            self._add_dedicated_paths(high_bw_flows, crossbar_id)
        else:
            print(f"\n1. No high-BW flows requiring dedicated paths")

        # Optimization 2: Group low-BW flows with arbiters
        if low_bw_flows and len(low_bw_flows) > 3:
            print(f"\n2. Grouping low-BW flows with arbiters...")
            self._add_arbiters_for_low_bw(low_bw_flows, crossbar_id)
        else:
            print(f"\n2. Too few low-BW flows to optimize")

        # Optimization 3: Remove unused crossbar connections
        print(f"\n3. Removing unused crossbar connections...")
        self._remove_unused_crossbar_connections(crossbar_id, high_bw_flows, low_bw_flows)

        # Print optimization results
        new_nodes = len(self.nodes)
        new_edges = len(self.edges)

        print(f"\n" + "="*70)
        print("OPTIMIZATION RESULTS")
        print(f"="*70)
        print(f"Nodes: {original_nodes} → {new_nodes} ({new_nodes - original_nodes:+d})")
        print(f"Edges: {original_edges} → {new_edges} ({new_edges - original_edges:+d})")

        if crossbar_id < len(self.nodes):
            crossbar = self.nodes[crossbar_id]
            old_ports = original_nodes - 1  # Approximation
            new_ports = crossbar.get('num_ports', 0)
            print(f"Crossbar ports: {old_ports} → {new_ports} ({new_ports - old_ports:+d})")

        print(f"\n✓ Bandwidth optimization complete")

    def _add_dedicated_paths(self, high_bw_flows, crossbar_id):
        """Add dedicated routers for high-bandwidth flows"""
        for src_name, dst_name, bandwidth in high_bw_flows:
            src_niu_id = self.node_map.get(f'{src_name}_NIU')
            dst_niu_id = self.node_map.get(f'{dst_name}_NIU')

            if not src_niu_id or not dst_niu_id:
                continue

            # Create dedicated router
            router_id = self._add_node(
                'Router',
                f'{src_name}_{dst_name}_Router',
                width=256,  # High-BW routers are wider
                clock_domain='fast',
                num_ports=2
            )

            # Remove old crossbar connections for this flow
            self.edges = [e for e in self.edges
                         if not ((e['src'] == src_niu_id and e['dst'] == crossbar_id) or
                                (e['src'] == crossbar_id and e['dst'] == dst_niu_id))]

            # Add dedicated path: src_NIU → dedicated_router → dst_NIU
            src_node = next(n for n in self.nodes if n['id'] == src_niu_id)
            dst_node = next(n for n in self.nodes if n['id'] == dst_niu_id)

            self._add_edge(src_niu_id, router_id, src_node['width'], 1)
            self._add_edge(router_id, dst_niu_id, dst_node['width'], 1)

            print(f"  ✓ {src_name} → {dst_name}: {bandwidth:.1f} GB/s (dedicated router)")

    def _add_arbiters_for_low_bw(self, low_bw_flows, crossbar_id):
        """Group low-bandwidth flows using arbiters"""
        # Group flows by target
        target_groups = {}
        for src_name, dst_name, bandwidth in low_bw_flows:
            if dst_name not in target_groups:
                target_groups[dst_name] = []
            target_groups[dst_name].append((src_name, bandwidth))

        max_arbiter_inputs = self.constraints.get('max_arbiter_inputs', 4)

        for dst_name, sources in target_groups.items():
            if len(sources) < 2:
                continue  # Need at least 2 sources to benefit from arbiter

            dst_niu_id = self.node_map.get(f'{dst_name}_NIU')
            if not dst_niu_id:
                continue

            # Group sources into arbiters
            for i in range(0, len(sources), max_arbiter_inputs):
                group = sources[i:i+max_arbiter_inputs]
                if len(group) < 2:
                    continue

                # Create arbiter
                arbiter_id = self._add_node(
                    'Arbiter',
                    f'{dst_name}_Arbiter_{i//max_arbiter_inputs}',
                    num_inputs=len(group),
                    width=64,
                    clock_domain='fast',
                    policy='round_robin'
                )

                # Connect sources to arbiter
                for src_name, bw in group:
                    src_niu_id = self.node_map.get(f'{src_name}_NIU')
                    if not src_niu_id:
                        continue

                    # Remove old crossbar connection
                    self.edges = [e for e in self.edges
                                 if not (e['src'] == src_niu_id and e['dst'] == crossbar_id)]

                    # Connect to arbiter
                    self._add_edge(src_niu_id, arbiter_id, 64, 1)

                # Connect arbiter to crossbar (or directly to target if possible)
                self._add_edge(arbiter_id, crossbar_id, 64, 2)

                src_names = [s[0] for s in group]
                print(f"  ✓ [{', '.join(src_names)}] → {dst_name} (via arbiter)")

    def _remove_unused_crossbar_connections(self, crossbar_id, high_bw_flows, low_bw_flows):
        """Remove crossbar connections that have been optimized away"""
        # Count connections to crossbar
        in_edges = len([e for e in self.edges if e['dst'] == crossbar_id])
        out_edges = len([e for e in self.edges if e['src'] == crossbar_id])

        # Update crossbar port count
        if crossbar_id < len(self.nodes):
            self.nodes[crossbar_id]['num_ports'] = in_edges + out_edges

        removed_flows = len(high_bw_flows) + len([f for f in low_bw_flows if len(f) > 0])
        print(f"  Removed {removed_flows} flows from crossbar")
        print(f"  Crossbar now has {in_edges} input + {out_edges} output ports")

    def get_topology_config(self) -> Dict[str, Any]:
        """Export topology as configuration dictionary"""
        return {
            'network': 'Irregular',
            'num_nodes': len(self.nodes),
            'nodes': self.nodes,
            'graph': {
                'edges': self.edges
            },
            'constraints': {
                'niu_entry_only': False,
                'clock_domains': self.constraints.get('clock_domains', []),
                'enforce_width_match': False,
                'max_end_to_end_latency': max(
                    flow.max_latency for flow in self.traffic_flows
                ) if self.traffic_flows else 200,
                'validate_bandwidth': True,
                'validate_latency': True
            }
        }

    def save_topology(self, output_path: str):
        """Save generated topology to YAML"""
        config = self.get_topology_config()

        with open(output_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False,
                     sort_keys=False, indent=2)

        print(f"\n✓ Topology saved to: {output_path}")

    def print_summary(self):
        """Print topology summary"""
        print("\n" + "="*70)
        print("TOPOLOGY GENERATION SUMMARY")
        print("="*70)

        # Count node types
        node_types = {}
        for node in self.nodes:
            node_types[node['type']] = node_types.get(node['type'], 0) + 1

        print(f"\nNode Types:")
        for ntype, count in sorted(node_types.items()):
            print(f"  {ntype:20s}: {count:3d}")

        print(f"\nConnectivity:")
        print(f"  Total edges: {len(self.edges)}")
        print(f"  Initiators: {len(self.initiators)}")
        print(f"  Targets: {len(self.targets)}")
        print(f"  Full crossbar: {len(self.initiators)} × {len(self.targets)} connectivity")

        # Calculate total bandwidth
        total_bw_req = sum(flow.bandwidth for flow in self.traffic_flows)
        total_bw_cap = sum(tgt.max_bandwidth for tgt in self.targets)

        print(f"\nBandwidth:")
        print(f"  Total required: {total_bw_req:.1f} GB/s")
        print(f"  Total capacity: {total_bw_cap:.1f} GB/s")
        print(f"  Utilization: {total_bw_req/total_bw_cap*100:.1f}%")


def generate_topology(spec_path: str, output_path: str,
                     optimize: bool = True):
    """
    Main function to generate topology from specification.

    Parameters
    ----------
    spec_path : str
        Path to simple specification YAML
    output_path : str
        Path to save generated topology
    optimize : bool
        Whether to apply bandwidth optimization
    """
    print("="*70)
    print("NoC Topology Generator")
    print("="*70)
    print(f"\nInput spec: {spec_path}")
    print(f"Output topology: {output_path}")

    # Create generator
    gen = TopologyGenerator(spec_path)

    # Generate full crossbar
    gen.generate_full_crossbar()

    # Optimize if requested
    if optimize:
        gen.optimize_bandwidth()

    # Print summary
    gen.print_summary()

    # Save topology
    gen.save_topology(output_path)

    return gen
