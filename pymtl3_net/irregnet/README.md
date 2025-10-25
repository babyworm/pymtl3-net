# IrregNet - Irregular Network Topology Support

Irregular (custom) network topology support for PyMTL3-Net with automatic converter insertion.

## Features

- **YAML-based topology specification**: Easy to create and modify
- **Automatic ClockConverter insertion**: Handles clock domain crossings
- **Automatic WidthConverter insertion**: Handles data width mismatches
- **NetworkX integration**: For analysis and visualization
- **Comprehensive validation**: Ensures topology correctness

## Quick Start

```python
from pymtl3_net.irregnet import TopologyLoader

# Load topology with auto-converter insertion
loader = TopologyLoader('my_topology.yml')

# Get NetworkX graph
G = loader.get_networkx_graph()

# Get configuration with inserted converters
config = loader.get_config()

print(f"Nodes: {len(loader.nodes)}")
print(f"Edges: {len(loader.edges)}")
```

## Example

See `examples/small/` for complete examples including:
- mobile_soc.yml - Smartphone SoC
- automotive_adas.yml - ADAS system
- drone_controller.yml - Flight controller
- And more...

## Documentation

See `examples/IRREGULAR_TOPOLOGY_GUIDE.md` for comprehensive documentation.

## Testing

```bash
# Test topology loader
python3 test_topology_loader.py

# Verify complete tool flow
cd examples
python3 verify_tool_flow.py
```
