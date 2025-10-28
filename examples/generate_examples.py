#!/usr/bin/env python3
"""
Generate remaining NoC example files programmatically
"""

import yaml
from pathlib import Path

def create_medium_example_2():
    """Datacenter NIC - 14 Initiators, 6 Targets"""
    return {
        'network': 'Irregular',
        'num_nodes': 48,
        'nodes': [
            # Initiators (14)
            *[{'id': i, 'type': 'Initiator', 'name': f'RX_Queue{i}',
               'avg_throughput': 5.0, 'max_throughput': 10.0,
               'latency_requirement': 15, 'priority': 0, 'traffic_pattern': 'bursty'}
              for i in range(8)],
            *[{'id': i+8, 'type': 'Initiator', 'name': f'TX_Queue{i}',
               'avg_throughput': 5.0, 'max_throughput': 10.0,
               'latency_requirement': 15, 'priority': 0, 'traffic_pattern': 'bursty'}
              for i in range(4)],
            {'id': 12, 'type': 'Initiator', 'name': 'RDMA_Engine',
             'avg_throughput': 20.0, 'max_throughput': 40.0,
             'latency_requirement': 10, 'priority': 0, 'traffic_pattern': 'streaming'},
            {'id': 13, 'type': 'Initiator', 'name': 'Crypto_Offload',
             'avg_throughput': 8.0, 'max_throughput': 16.0,
             'latency_requirement': 30, 'priority': 1, 'traffic_pattern': 'bursty'},
            # NIUs (14)
            *[{'id': i+14, 'type': 'NIU', 'name': f'RX{i}_NIU',
               'width': 128, 'clock_domain': 'fast'} for i in range(8)],
            *[{'id': i+22, 'type': 'NIU', 'name': f'TX{i}_NIU',
               'width': 128, 'clock_domain': 'fast'} for i in range(4)],
            {'id': 26, 'type': 'NIU', 'name': 'RDMA_NIU', 'width': 256, 'clock_domain': 'fast'},
            {'id': 27, 'type': 'NIU', 'name': 'Crypto_NIU', 'width': 128, 'clock_domain': 'fast'},
            # Routers (4)
            {'id': 28, 'type': 'Router', 'name': 'RX_Router', 'width': 128, 'clock_domain': 'fast', 'num_ports': 5},
            {'id': 29, 'type': 'Router', 'name': 'TX_Router', 'width': 128, 'clock_domain': 'fast', 'num_ports': 5},
            {'id': 30, 'type': 'Router', 'name': 'Mem_Router', 'width': 256, 'clock_domain': 'fast', 'num_ports': 4},
            {'id': 31, 'type': 'Router', 'name': 'Stats_Router', 'width': 64, 'clock_domain': 'slow', 'num_ports': 3},
            # Arbiters (3)
            {'id': 32, 'type': 'Arbiter', 'name': 'RX_Arbiter', 'num_inputs': 4, 'width': 128, 'clock_domain': 'fast', 'policy': 'round_robin'},
            {'id': 33, 'type': 'Arbiter', 'name': 'TX_Arbiter', 'num_inputs': 4, 'width': 128, 'clock_domain': 'fast', 'policy': 'round_robin'},
            {'id': 34, 'type': 'Arbiter', 'name': 'Mem_Arbiter', 'num_inputs': 3, 'width': 256, 'clock_domain': 'fast', 'policy': 'priority'},
            # Decoders (1)
            {'id': 35, 'type': 'Decoder', 'name': 'Buffer_Decoder', 'num_outputs': 4, 'width': 256, 'clock_domain': 'fast'},
            # Target NIUs (6)
            *[{'id': i+36, 'type': 'NIU', 'name': f'Mem{i}_NIU',
               'width': 256, 'clock_domain': 'fast'} for i in range(6)],
            # Targets (6)
            {'id': 42, 'type': 'Target', 'name': 'RX_Buffer', 'max_bandwidth': 100.0, 'latency': 10, 'size': 1, 'type_detail': 'SRAM'},
            {'id': 43, 'type': 'Target', 'name': 'TX_Buffer', 'max_bandwidth': 100.0, 'latency': 10, 'size': 1, 'type_detail': 'SRAM'},
            {'id': 44, 'type': 'Target', 'name': 'Desc_Memory', 'max_bandwidth': 50.0, 'latency': 15, 'size': 0.128, 'type_detail': 'SRAM'},
            {'id': 45, 'type': 'Target', 'name': 'Stats_Counter', 'max_bandwidth': 10.0, 'latency': 5, 'size': 0.016, 'type_detail': 'SRAM'},
            {'id': 46, 'type': 'Target', 'name': 'Flow_Table', 'max_bandwidth': 30.0, 'latency': 8, 'size': 0.256, 'type_detail': 'TCAM'},
            {'id': 47, 'type': 'Target', 'name': 'Config_Flash', 'max_bandwidth': 1.0, 'latency': 200, 'size': 0.128, 'type_detail': 'Flash'},
        ],
        'graph': {'edges': [
            # Initiator → NIU (14 edges)
            *[{'src': i, 'dst': i+14, 'width': 128, 'latency': 1} for i in range(14)],
            # RX paths
            *[{'src': i+14, 'dst': 32, 'width': 128, 'latency': 1} for i in range(4)],
            *[{'src': i+18, 'dst': 32, 'width': 128, 'latency': 1} for i in range(4)],
            {'src': 32, 'dst': 28, 'width': 128, 'latency': 2},
            # TX paths
            *[{'src': i+22, 'dst': 33, 'width': 128, 'latency': 1} for i in range(4)],
            {'src': 33, 'dst': 29, 'width': 128, 'latency': 2},
            # Special paths
            {'src': 26, 'dst': 30, 'width': 256, 'latency': 1},
            {'src': 27, 'dst': 28, 'width': 128, 'latency': 1},
            # Router → Arbiter
            {'src': 28, 'dst': 34, 'width': 256, 'latency': 1},
            {'src': 29, 'dst': 34, 'width': 256, 'latency': 1},
            {'src': 30, 'dst': 34, 'width': 256, 'latency': 1},
            # Arbiter → Decoder
            {'src': 34, 'dst': 35, 'width': 256, 'latency': 2},
            # Decoder → Target NIUs
            *[{'src': 35, 'dst': i+36, 'width': 256, 'latency': 1} for i in range(4)],
            # Router → Stats
            {'src': 28, 'dst': 31, 'width': 64, 'latency': 2},
            {'src': 31, 'dst': 38, 'width': 64, 'latency': 1},
            {'src': 31, 'dst': 41, 'width': 64, 'latency': 1},
            # Target NIUs → Targets
            {'src': 36, 'dst': 42, 'width': 256, 'latency': 2},
            {'src': 37, 'dst': 43, 'width': 256, 'latency': 2},
            {'src': 38, 'dst': 44, 'width': 256, 'latency': 3},
            {'src': 39, 'dst': 45, 'width': 256, 'latency': 2},
            {'src': 40, 'dst': 46, 'width': 256, 'latency': 3},
            {'src': 41, 'dst': 47, 'width': 256, 'latency': 10},
        ]},
        'constraints': {
            'niu_entry_only': True,
            'clock_domains': [
                {'name': 'fast', 'frequency': 2000},
                {'name': 'slow', 'frequency': 500},
            ],
            'enforce_width_match': False,
            'max_end_to_end_latency': 250,
            'bandwidth_allocation': [
                {'initiator': 0, 'target': 42, 'guaranteed_bw': 5.0, 'max_latency': 25, 'priority': 0},
                {'initiator': 8, 'target': 43, 'guaranteed_bw': 5.0, 'max_latency': 25, 'priority': 0},
                {'initiator': 12, 'target': 42, 'guaranteed_bw': 20.0, 'max_latency': 20, 'priority': 0},
                {'initiator': 13, 'target': 44, 'guaranteed_bw': 8.0, 'max_latency': 50, 'priority': 1},
            ],
            'validate_bandwidth': True,
            'validate_latency': True,
        }
    }

# Create the example
example = create_medium_example_2()

# Save to file
output_path = Path('/home/user/pymtl3-net/examples/medium/datacenter_nic.yml')
with open(output_path, 'w') as f:
    yaml.dump(example, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

print(f"Created: {output_path}")
print(f"Total nodes: {len(example['nodes'])}")
print(f"Total edges: {len(example['graph']['edges'])}")
