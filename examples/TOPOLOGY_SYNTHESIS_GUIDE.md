# NoC Topology Synthesis Guide

## Overview

This guide explains how to **automatically generate** NoC topologies from high-level specifications. Users only specify what they need (Initiators, Targets, Traffic), and the tool automatically generates the complete topology.

## Two Approaches

### Approach 1: Manual Topology (Old Way) ❌
Users manually define **everything**:
- Initiators, Targets, NIUs, Routers, Arbiters, Decoders
- All connections and edges
- Clock domains, widths, latencies
- Converters for clock/width mismatches

**Problem**: Too complex, error-prone, requires deep NoC expertise.

### Approach 2: Automatic Synthesis (New Way) ✅
Users only specify **requirements**:
- Initiators (CPUs, GPUs, etc.)
- Targets (DRAM, Cache, Flash)
- Traffic requirements (bandwidth, latency)

**Tool automatically generates**:
- NIUs for each initiator/target
- Full crossbar or optimized topology
- Routers with correct port counts
- Clock domain assignments
- Data width calculations
- Converters for mismatches

## Quick Start

### Step 1: Create Simple Specification

Create a YAML file with only high-level requirements:

```yaml
# simple_soc.yml
initiators:
  - name: CPU0
    type: CPU
    avg_throughput: 2.0    # GB/s
    max_throughput: 4.0
    latency_req: 20        # cycles
    priority: 0

  - name: GPU
    type: GPU
    avg_throughput: 8.0
    max_throughput: 16.0
    latency_req: 50
    priority: 1

targets:
  - name: DDR4_Memory
    type: DRAM
    max_bandwidth: 25.6    # GB/s
    latency: 100
    size: 4                # GB

  - name: L3_Cache
    type: SRAM
    max_bandwidth: 50.0
    latency: 10
    size: 0.032            # 32 MB

traffic_flows:
  - src: CPU0
    dst: DDR4_Memory
    bandwidth: 1.0         # GB/s required
    max_latency: 120
    priority: 0

  - src: GPU
    dst: DDR4_Memory
    bandwidth: 8.0
    max_latency: 150
    priority: 1

constraints:
  clock_domains:
    - {name: fast, frequency: 2000}
    - {name: slow, frequency: 1000}

  optimize_for: bandwidth
```

### Step 2: Generate Topology

```python
from pymtl3_net.irregnet.topology_generator import generate_topology

# One-line topology generation!
gen = generate_topology(
    spec_path='simple_soc.yml',
    output_path='simple_soc_generated.yml',
    optimize=True
)
```

### Step 3: Load with Auto-Converter Insertion

```python
from pymtl3_net.irregnet import TopologyLoader

# Load and auto-insert converters
loader = TopologyLoader('simple_soc_generated.yml',
                       auto_insert_converters=True)

# Ready to use!
G = loader.get_networkx_graph()
```

## What Gets Generated?

### Input: Simple Specification
- 4 initiators
- 3 targets
- 7 traffic flows
- **Total: ~30 lines of YAML**

### Output: Complete Topology
- 4 Initiators
- 3 Targets
- 7 NIUs (auto-created)
- 1 Crossbar Router (256-bit, 7 ports)
- 15 nodes total
- 14 edges
- **Full connectivity: 4 × 3**

### After Auto-Converter Insertion
- +6 WidthConverters (auto-inserted)
- 21 nodes total
- 20 edges
- **Ready for PyMTL3 simulation**

## Comparison

| Aspect | Manual (Old) | Auto-Synthesis (New) |
|--------|-------------|---------------------|
| **User Input** | 300+ lines YAML | ~50 lines YAML |
| **Expertise Required** | High (NoC expert) | Low (system architect) |
| **Errors** | Many (manual connections) | Few (auto-generated) |
| **NIU Creation** | Manual | Automatic |
| **Router Sizing** | Manual calculation | Automatic (based on BW) |
| **Clock Domains** | Manual assignment | Automatic (based on BW) |
| **Data Widths** | Manual calculation | Automatic (based on BW) |
| **Converters** | Manual insertion | Automatic insertion |
| **Optimization** | Manual | Automatic (BW-based) |
| **Time to Create** | Hours | Minutes |

## Examples

### Example 1: Simple SoC (4 initiators, 3 targets)

**Input Specification**: 30 lines
```yaml
initiators: [CPU0, CPU1, GPU, ISP]
targets: [DDR4, L3_Cache, Flash]
traffic_flows: 7 flows
```

**Generated Topology**:
- 15 nodes (4 Init + 3 Tgt + 7 NIU + 1 Router)
- 14 edges
- Full 4×3 crossbar connectivity
- After auto-converters: 21 nodes

**Bandwidth Analysis**:
- Required: 15.5 GB/s
- Capacity: 77.6 GB/s
- Utilization: 20%

### Example 2: Server SoC (16 initiators, 8 targets)

**Input Specification**: 120 lines
```yaml
initiators: [8 CPUs, 2 AI_Accels, 4 I/O, 2 DMA]
targets: [4 DDR4, 2 HBM, L3_Cache, NVMe]
traffic_flows: 30 flows
```

**Generated Topology**:
- 49 nodes (16 Init + 8 Tgt + 24 NIU + 1 Router)
- 48 edges
- Full 16×8 crossbar connectivity
- Crossbar: 512-bit wide, 24 ports

**Bandwidth Analysis**:
- Required: 309.5 GB/s
- Capacity: 721.4 GB/s
- Utilization: 43%
- High-BW flows identified: 13 (including AI→HBM at 100 GB/s each)

## Automatic Features

### 1. Data Width Calculation

The tool automatically calculates required data widths:

```
width (bits) = bandwidth (GB/s) × 8 × 1000 / frequency (MHz)
```

Then rounds up to power-of-2: 32, 64, 128, 256, 512 bits.

**Example**:
- GPU (16 GB/s @ 2000 MHz) → 64-bit
- AI Accelerator (40 GB/s @ 3000 MHz) → 128-bit
- HBM (256 GB/s @ 3000 MHz) → 512-bit

### 2. Clock Domain Assignment

Based on bandwidth requirements:
- High bandwidth (>10 GB/s) → `fast` clock domain
- Medium bandwidth (2-10 GB/s) → `fast` clock domain
- Low bandwidth (<2 GB/s) → `slow` clock domain

### 3. Full Crossbar Generation

Creates a central crossbar router with:
- Width = max(all_widths)
- Ports = num_initiators + num_targets
- All initiators can reach all targets

### 4. Future Optimizations

Coming soon:
- **Shared links**: Group low-BW flows through arbiters
- **Dedicated paths**: High-BW flows get direct connections
- **Hierarchical topology**: Multi-level routers for >32 nodes
- **Power optimization**: Gate unused paths
- **Area optimization**: Share resources where possible

## Validation

After generation, always validate:

```bash
# Validate generated topology
cd examples
python3 validate_topologies.py simple_specs/simple_soc_generated.yml

# Verify complete tool flow
python3 verify_tool_flow.py
```

## Complete Workflow

```
1. User writes simple spec (Initiators + Targets + Traffic)
   ↓
2. TopologyGenerator creates full crossbar
   ↓
3. Optimizer adjusts based on bandwidth
   ↓
4. Saves complete topology YAML
   ↓
5. TopologyLoader adds converters
   ↓
6. Validation ensures correctness
   ↓
7. Ready for PyMTL3 simulation
```

## File Locations

**Input Specifications**:
- `examples/simple_specs/simple_soc.yml` - 4 initiators, 3 targets
- `examples/simple_specs/server_soc.yml` - 16 initiators, 8 targets

**Generated Topologies**:
- `examples/simple_specs/simple_soc_generated.yml`
- `examples/simple_specs/server_soc_generated.yml`

**Tools**:
- `pymtl3_net/irregnet/topology_generator.py` - Main generator
- `pymtl3_net/irregnet/topology_loader.py` - Loader with auto-converters
- `test_topology_generator.py` - Test suite

## Python API

### Generate Topology

```python
from pymtl3_net.irregnet.topology_generator import TopologyGenerator

# Create generator
gen = TopologyGenerator('my_spec.yml')

# Generate full crossbar
gen.generate_full_crossbar()

# Optimize
gen.optimize_bandwidth()

# Save
gen.save_topology('my_topology.yml')

# Get summary
gen.print_summary()
```

### Access Generated Nodes/Edges

```python
# Get all nodes
for node in gen.nodes:
    print(f"{node['name']}: {node['type']}")

# Get all edges
for edge in gen.edges:
    print(f"{edge['src']} → {edge['dst']}: {edge['width']}-bit")

# Get configuration dict
config = gen.get_topology_config()
```

## Best Practices

### 1. Start with Requirements
Focus on WHAT you need, not HOW to build it:
- Which initiators?
- Which targets?
- How much bandwidth?
- What latency?

### 2. Let the Tool Handle Details
Don't manually calculate:
- Data widths ✗
- Clock domains ✗
- NIU placements ✗
- Router sizing ✗

The tool does this automatically and correctly.

### 3. Validate Generated Topology
Always run validation after generation:
```bash
python3 validate_topologies.py my_topology.yml
```

### 4. Iterate on Requirements
If bandwidth is too low:
- Increase target bandwidth capacity
- Add more targets
- Increase clock frequency

The tool will automatically adjust widths and routing.

## Troubleshooting

### "Bandwidth utilization > 100%"
**Solution**: Increase target bandwidth or add more targets.

### "Generated crossbar too large (>32 ports)"
**Solution**: Coming soon - hierarchical topology generation.

### "Clock domain mismatches after generation"
**Solution**: Use TopologyLoader with `auto_insert_converters=True`.

## Future Enhancements

- [ ] Hierarchical topology for large systems (>32 nodes)
- [ ] Arbiter insertion for shared paths
- [ ] Decoder insertion for multi-target access
- [ ] Power-aware optimization
- [ ] Area-aware optimization
- [ ] Custom topology templates (mesh, torus, etc.)
- [ ] Traffic pattern analysis and replay
- [ ] Performance estimation before generation

## Summary

**Old Way**: User manually creates 300+ line YAML with all details.

**New Way**: User creates 50-line YAML with requirements, tool generates everything.

**Result**: 10× faster, fewer errors, better optimization!

---

For detailed examples, see:
- `examples/simple_specs/` - Input specifications
- `test_topology_generator.py` - Usage examples
- `IRREGULAR_TOPOLOGY_GUIDE.md` - Low-level topology details
