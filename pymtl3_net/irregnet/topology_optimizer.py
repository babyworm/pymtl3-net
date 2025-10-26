"""
=========================================================================
topology_optimizer.py
=========================================================================
Constraint-based multi-objective topology optimization.

Key Principles:
1. Connectivity (traffic_flows) = HARD CONSTRAINTS - never violated
2. Optimization = Choose best IMPLEMENTATION for each flow
3. Multi-objective: throughput, latency, area with configurable weights

Author : Claude Code
  Date : 2025-10-26
"""

from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from enum import Enum
import itertools


class FlowImplementation(Enum):
    """Different ways to implement a single flow"""
    DIRECT = "direct"              # Dedicated router, shortest path
    CROSSBAR = "crossbar"          # Through central crossbar
    SHARED_ROUTER = "shared"       # Through shared router
    ARBITER = "arbiter"            # Via arbiter (for low-BW)


@dataclass
class ImplementationOption:
    """A specific implementation choice for a flow"""
    flow_id: Tuple[str, str]  # (src, dst)
    impl_type: FlowImplementation

    # Cost metrics
    throughput_score: float  # Higher is better (0-1)
    latency_cycles: int      # Lower is better
    area_cost: float         # Arbitrary units, lower is better

    # Resource usage
    needs_dedicated_router: bool = False
    needs_arbiter: bool = False
    uses_crossbar: bool = False

    # Compatibility
    conflicts_with: List[Tuple[str, str]] = None  # Other flows that conflict

    def __post_init__(self):
        if self.conflicts_with is None:
            self.conflicts_with = []


class TopologyOptimizer:
    """
    Multi-objective topology optimizer respecting connectivity constraints.

    Given:
    - Required connectivity (traffic flows)
    - Performance requirements (bandwidth, latency)
    - Optimization weights

    Finds:
    - Best implementation for each flow
    - Optimal router/arbiter placement
    - Minimized cost while meeting all constraints
    """

    def __init__(self, flows: List[Dict], weights: Dict[str, float]):
        """
        Parameters
        ----------
        flows : List[Dict]
            Traffic flow requirements (connectivity constraints)
        weights : Dict[str, float]
            Optimization weights: throughput, latency, area
        """
        self.flows = flows
        self.weights = {
            'throughput': weights.get('throughput', 0.6),
            'latency': weights.get('latency', 0.3),
            'area': weights.get('area', 0.1)
        }

        # Normalize weights to sum to 1.0
        total = sum(self.weights.values())
        self.weights = {k: v/total for k, v in self.weights.items()}

        # Implementation options for each flow
        self.flow_options: Dict[Tuple[str, str], List[ImplementationOption]] = {}

        # Selected implementation for each flow
        self.selected_impl: Dict[Tuple[str, str], ImplementationOption] = {}

    def generate_implementation_options(self):
        """
        For each flow, generate all possible implementation options.

        Each flow can be implemented via:
        1. Direct path (dedicated router) - best perf, highest area
        2. Crossbar - medium perf, medium area
        3. Shared router - medium perf, medium area
        4. Arbiter + crossbar (low-BW only) - lower perf, lowest area
        """
        for flow in self.flows:
            flow_id = (flow['src'], flow['dst'])
            bandwidth = flow['bandwidth']
            max_latency = flow['max_latency']

            options = []

            # Option 1: Direct/Dedicated path
            # Best for high-BW flows (>= 50 GB/s)
            if bandwidth >= 50.0:
                options.append(ImplementationOption(
                    flow_id=flow_id,
                    impl_type=FlowImplementation.DIRECT,
                    throughput_score=1.0,  # No contention
                    latency_cycles=2,      # Shortest path
                    area_cost=100.0,       # Dedicated router costs area
                    needs_dedicated_router=True
                ))

            # Option 2: Through crossbar
            # Good for medium-BW flows (5-50 GB/s)
            options.append(ImplementationOption(
                flow_id=flow_id,
                impl_type=FlowImplementation.CROSSBAR,
                throughput_score=0.7,  # Some contention
                latency_cycles=4,      # Crossbar + routing
                area_cost=5.0,         # Amortized over many flows
                uses_crossbar=True
            ))

            # Option 3: Via arbiter (low-BW only)
            # Best for low-BW flows (< 5 GB/s)
            if bandwidth < 5.0:
                options.append(ImplementationOption(
                    flow_id=flow_id,
                    impl_type=FlowImplementation.ARBITER,
                    throughput_score=0.5,  # Arbitration overhead
                    latency_cycles=6,      # Arbiter + crossbar
                    area_cost=2.0,         # Arbiter is small
                    needs_arbiter=True,
                    uses_crossbar=True
                ))

            self.flow_options[flow_id] = options

    def compute_cost(self, impl: ImplementationOption, flow: Dict) -> float:
        """
        Compute weighted cost for an implementation option.

        Lower cost is better.
        """
        # Throughput penalty (0-1, normalized)
        # If required BW > capacity, high penalty
        required_bw = flow['bandwidth']
        throughput_penalty = 1.0 - impl.throughput_score

        # Latency penalty (0-1, normalized)
        max_latency = flow['max_latency']
        latency_penalty = impl.latency_cycles / max_latency
        latency_penalty = min(latency_penalty, 1.0)  # Cap at 1.0

        # Area penalty (normalized by max area)
        area_penalty = impl.area_cost / 100.0  # Normalize by max area

        # Weighted sum
        cost = (self.weights['throughput'] * throughput_penalty +
                self.weights['latency'] * latency_penalty +
                self.weights['area'] * area_penalty)

        return cost

    def select_best_implementations(self):
        """
        Select best implementation for each flow using greedy algorithm.

        Strategy:
        1. Sort flows by bandwidth (high to low)
        2. For each flow, select lowest-cost option
        3. Update shared resource capacity

        This is a greedy approximation. For optimal solution,
        would need ILP solver.
        """
        # Sort flows by bandwidth (prioritize high-BW flows)
        sorted_flows = sorted(self.flows, key=lambda f: f['bandwidth'], reverse=True)

        # Track resource usage
        crossbar_load = 0.0  # Total BW through crossbar
        crossbar_capacity = 500.0  # GB/s (example)

        for flow in sorted_flows:
            flow_id = (flow['src'], flow['dst'])
            options = self.flow_options[flow_id]

            # Evaluate cost for each option
            costs = [(self.compute_cost(opt, flow), opt) for opt in options]

            # Filter out infeasible options
            feasible = []
            for cost, opt in costs:
                # Check crossbar capacity
                if opt.uses_crossbar:
                    if crossbar_load + flow['bandwidth'] > crossbar_capacity:
                        continue  # Crossbar overloaded

                feasible.append((cost, opt))

            if not feasible:
                # Fallback: must use dedicated path
                dedicated = next(opt for opt in options
                               if opt.impl_type == FlowImplementation.DIRECT)
                self.selected_impl[flow_id] = dedicated
                print(f"  ! {flow_id[0]}→{flow_id[1]}: Forced DIRECT (crossbar full)")
            else:
                # Select lowest cost
                best_cost, best_impl = min(feasible, key=lambda x: x[0])
                self.selected_impl[flow_id] = best_impl

                # Update resource usage
                if best_impl.uses_crossbar:
                    crossbar_load += flow['bandwidth']

                print(f"  ✓ {flow_id[0]}→{flow_id[1]}: {best_impl.impl_type.value} "
                      f"(cost={best_cost:.3f}, BW={flow['bandwidth']:.1f} GB/s)")

    def get_optimization_summary(self) -> Dict[str, Any]:
        """Return summary of optimization decisions"""
        impl_counts = {}
        total_area = 0
        avg_latency = 0
        crossbar_flows = 0

        for flow_id, impl in self.selected_impl.items():
            impl_type = impl.impl_type.value
            impl_counts[impl_type] = impl_counts.get(impl_type, 0) + 1
            total_area += impl.area_cost
            avg_latency += impl.latency_cycles
            if impl.uses_crossbar:
                crossbar_flows += 1

        return {
            'implementation_distribution': impl_counts,
            'total_area_cost': total_area,
            'average_latency': avg_latency / len(self.selected_impl) if self.selected_impl else 0,
            'crossbar_utilization': crossbar_flows,
            'dedicated_paths': impl_counts.get('direct', 0),
            'arbiter_groups': impl_counts.get('arbiter', 0)
        }

    def print_summary(self):
        """Print optimization summary"""
        summary = self.get_optimization_summary()

        print("\n" + "="*70)
        print("OPTIMIZATION SUMMARY")
        print("="*70)

        print(f"\nImplementation Distribution:")
        for impl_type, count in summary['implementation_distribution'].items():
            print(f"  {impl_type}: {count} flows")

        print(f"\nResource Usage:")
        print(f"  Total area cost: {summary['total_area_cost']:.1f}")
        print(f"  Average latency: {summary['average_latency']:.1f} cycles")
        print(f"  Crossbar flows: {summary['crossbar_utilization']}")
        print(f"  Dedicated paths: {summary['dedicated_paths']}")

        print(f"\nOptimization Weights:")
        print(f"  Throughput: {self.weights['throughput']:.2f}")
        print(f"  Latency: {self.weights['latency']:.2f}")
        print(f"  Area: {self.weights['area']:.2f}")


def optimize_topology(flows: List[Dict],
                     weights: Dict[str, float] = None) -> TopologyOptimizer:
    """
    Main optimization function.

    Parameters
    ----------
    flows : List[Dict]
        Traffic flow requirements (connectivity constraints)
    weights : Dict[str, float], optional
        Optimization weights: throughput, latency, area

    Returns
    -------
    TopologyOptimizer
        Optimizer with selected implementations
    """
    if weights is None:
        weights = {'throughput': 0.6, 'latency': 0.3, 'area': 0.1}

    print("="*70)
    print("Constraint-Based Topology Optimization")
    print("="*70)
    print(f"\nConnectivity constraints: {len(flows)} flows (MUST preserve all)")

    # Create optimizer
    optimizer = TopologyOptimizer(flows, weights)

    # Generate implementation options
    print(f"\nGenerating implementation options...")
    optimizer.generate_implementation_options()

    total_options = sum(len(opts) for opts in optimizer.flow_options.values())
    print(f"  Total options: {total_options} across {len(flows)} flows")

    # Select best implementations
    print(f"\nSelecting best implementations (greedy algorithm)...")
    optimizer.select_best_implementations()

    # Print summary
    optimizer.print_summary()

    return optimizer
