# Irregular Topology Guide for PyMTL3-Net

## Overview

This guide explains how to create and use irregular (custom) network topologies in PyMTL3-Net. The tool automatically handles clock domain crossings and data width mismatches by inserting appropriate converters.

## Tool Flow

```
User YAML → TopologyLoader → Auto-Converter Insertion → Validation → PyMTL3 Network
```

### 1. Create Topology YAML

Users define their custom topology in YAML format with nodes and edges:

```yaml
network: 'Irregular'
num_nodes: 20

nodes:
  - id: 0
    type: "Initiator"
    name: "CPU_Core0"
    avg_throughput: 2.0
    max_throughput: 4.0
    latency_requirement: 20
    priority: 0

  - id: 1
    type: "NIU"
    name: "CPU_NIU"
    width: 64
    clock_domain: "fast"

  - id: 2
    type: "Router"
    name: "Main_Router"
    width: 128
    clock_domain: "slow"
    num_ports: 5

graph:
  edges:
    - src: 0
      dst: 1
      width: 64
      latency: 1

    - src: 1
      dst: 2  # Clock crossing: fast→slow, Width mismatch: 64→128
      width: 64
      latency: 2
```

### 2. Load with TopologyLoader

The `TopologyLoader` automatically detects and fixes issues:

```python
from pymtl3_net.irregnet import TopologyLoader

# Load with auto-converter insertion
loader = TopologyLoader('my_topology.yml', auto_insert_converters=True)

# Loader automatically inserted:
# - ClockConverter for fast→slow crossing
# - WidthConverter for 64→128 width change
```

### 3. Automatic Converter Insertion

The tool automatically inserts converters when needed:

#### Clock Domain Crossings
When two nodes with different clock domains are connected:
```
NIU(fast) → Router(slow)
```
Becomes:
```
NIU(fast) → ClockConverter(fast→slow) → Router(slow)
```

#### Width Mismatches
When data widths don't match:
```
Router(64-bit) → Router(128-bit)
```
Becomes:
```
Router(64-bit) → WidthConverter(64→128) → Router(128-bit)
```

#### Combined Issues
Both clock and width issues:
```
NIU(fast, 32-bit) → Router(slow, 64-bit)
```
Becomes:
```
NIU(fast, 32-bit) → ClockConverter → WidthConverter → Router(slow, 64-bit)
```

## Supported Node Types

### 1. Initiator
Traffic generators (CPUs, GPUs, etc.)
- `avg_throughput`: Average bandwidth requirement
- `max_throughput`: Peak bandwidth
- `latency_requirement`: Maximum acceptable latency
- `priority`: QoS priority level
- `traffic_pattern`: "bursty", "streaming", "uniform"

### 2. Target
Memory targets (DRAM, SRAM, Flash, etc.)
- `max_bandwidth`: Maximum supported bandwidth
- `latency`: Access latency
- `size`: Capacity in GB
- `type_detail`: Memory technology

### 3. NIU (Network Interface Unit)
Connects initiators/targets to the network
- `width`: Data width in bits
- `clock_domain`: Clock domain name

### 4. Router
Packet routing nodes
- `width`: Data width
- `clock_domain`: Clock domain
- `num_ports`: Number of ports

### 5. Arbiter
N:1 arbitration (max 4:1)
- `num_inputs`: Number of input ports
- `width`: Data width
- `policy`: "priority", "round_robin", "weighted"

### 6. Decoder
1:N decoding (max 1:4)
- `num_outputs`: Number of output ports
- `width`: Data width

### 7. ClockConverter
Clock domain crossing (auto-inserted)
- `width`: Data width
- `src_clock_domain`: Source clock domain
- `dst_clock_domain`: Destination clock domain

### 8. WidthConverter
Data width conversion (auto-inserted)
- `src_width`: Source data width
- `dst_width`: Destination data width
- `clock_domain`: Operating clock domain

## Examples

All examples in `examples/small/` demonstrate the complete tool flow:

### mobile_soc.yml (33 nodes)
- 8 initiators, 3 targets, 11 NIUs
- Multiple clock domains (fast, slow)
- Mixed data widths (32, 64, 128-bit)
- **Auto-inserted**: 2 ClockConverters, 2 WidthConverters

### automotive_adas.yml (27 nodes)
- ADAS system with sensors and AI processors
- **Auto-inserted**: 1 ClockConverter, 5 WidthConverters

### drone_controller.yml (26 nodes)
- Real-time flight control system
- Ultra-fast control, fast video, slow peripherals
- **Auto-inserted**: 2 ClockConverters, 6 WidthConverters

## Verification

Use the verification script to test your topology:

```bash
cd examples
python3 verify_tool_flow.py
```

This will:
1. Load all small examples
2. Show auto-converter insertion
3. Validate connectivity and constraints
4. Report any issues

## Validation Script

Use `validate_topologies.py` to check for issues:

```bash
cd examples
python3 validate_topologies.py
```

Checks for:
- Node count accuracy
- Port overflow on routers/arbiters/decoders
- Width consistency
- Clock domain crossings
- Initiator→NIU and NIU→Target connections

## Best Practices

### 1. Start Simple
Begin with small topologies (8 initiators, 3 targets) and expand.

### 2. Define Clock Domains Clearly
```yaml
constraints:
  clock_domains:
    - name: "fast"
      frequency: 2000  # MHz
    - name: "slow"
      frequency: 1000
```

### 3. Let Auto-Insertion Handle Converters
Don't manually add ClockConverter/WidthConverter unless you have specific requirements. The tool will insert them optimally.

### 4. Use Consistent Widths
Prefer power-of-2 widths (32, 64, 128, 256) for efficiency.

### 5. Validate Early
Run verification after creating your YAML to catch issues early.

## Python API

### Basic Usage

```python
from pymtl3_net.irregnet import TopologyLoader

# Load topology
loader = TopologyLoader('my_topology.yml')

# Get NetworkX graph for analysis
G = loader.get_networkx_graph()

# Get updated configuration with auto-inserted converters
config = loader.get_config()

# Save updated YAML
loader.save_yaml('my_topology_with_converters.yml')
```

### Disable Auto-Insertion

```python
# Load without auto-insertion (use only manual converters)
loader = TopologyLoader('my_topology.yml', auto_insert_converters=False)
```

### Inspect Converters

```python
loader = TopologyLoader('my_topology.yml')

# Find all auto-inserted converters
cdcs = [n for n in loader.nodes if n.type == 'ClockConverter']
wcs = [n for n in loader.nodes if n.type == 'WidthConverter']

print(f"Inserted {len(cdcs)} ClockConverters")
print(f"Inserted {len(wcs)} WidthConverters")

for cdc in cdcs:
    src_clk = cdc.attributes['src_clock_domain']
    dst_clk = cdc.attributes['dst_clock_domain']
    print(f"  {cdc.name}: {src_clk} → {dst_clk}")
```

## Visualization

All examples include:
- **Static PNG**: `examples/visualizations/small/<name>.png`
- **Interactive HTML**: `examples/visualizations/interactive/small/<name>.html`

View the interactive visualization to:
- Click nodes to see attributes
- Click edges to see connections
- Search for specific nodes
- Zoom and pan the topology

## Performance Test Results

| Example | Auto-Insertion | Converters Added | Validation |
|---------|---------------|------------------|------------|
| mobile_soc.yml | ✓ | 0 (already optimal) | ✓ PASS |
| automotive_adas.yml | ✓ | 5 WidthConverters | ✓ PASS |
| drone_controller.yml | ✓ | 6 WidthConverters | ✓ PASS |
| gaming_console.yml | ✓ | 2 WidthConverters | ✓ PASS |
| home_assistant.yml | ✓ | 1 WidthConverter | ✓ PASS |
| iot_device.yml | ✓ | 5 WidthConverters | ✓ PASS |

## Troubleshooting

### "Clock crossing without ClockConverter"
Enable auto-insertion or manually add a ClockConverter between the nodes.

### "Width mismatch"
Enable auto-insertion or manually add a WidthConverter.

### "Router port overflow"
Increase `num_ports` on the router node.

### "Target receives from Router (not NIU)"
Either:
- Add a NIU between Router and Target, or
- Set `niu_entry_only: false` in constraints

## Future Work

- [ ] IrregularNetworkRTL implementation for full PyMTL3 simulation
- [ ] Automatic routing table generation
- [ ] Performance analysis and optimization
- [ ] Power estimation integration

## References

- PyMTL3 documentation: https://pymtl3.readthedocs.io/
- NetworkX documentation: https://networkx.org/
- opt.md: NoC synthesis optimization guide
