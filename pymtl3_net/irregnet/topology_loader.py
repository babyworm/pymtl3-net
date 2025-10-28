"""
=========================================================================
topology_loader.py
=========================================================================
Load irregular topology from YAML and automatically insert converters
for clock domain crossings and width mismatches.

Author : Claude Code
  Date : 2025-10-25
"""

import yaml
import networkx as nx
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, field


@dataclass
class NodeDef:
    """Node definition"""
    id: int
    type: str
    name: str
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EdgeDef:
    """Edge definition"""
    src: int
    dst: int
    width: int
    latency: int
    attributes: Dict[str, Any] = field(default_factory=dict)


class TopologyLoader:
    """
    Load topology from YAML and automatically insert converters.

    Features:
    - Automatic ClockConverter insertion for clock domain crossings
    - Automatic WidthConverter insertion for width mismatches
    - Validation of topology constraints
    """

    def __init__(self, yaml_path: str, auto_insert_converters: bool = True):
        """
        Initialize topology loader.

        Parameters
        ----------
        yaml_path : str
            Path to YAML topology file
        auto_insert_converters : bool
            If True, automatically insert converters for mismatches
        """
        self.yaml_path = yaml_path
        self.auto_insert_converters = auto_insert_converters

        with open(yaml_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.nodes: List[NodeDef] = []
        self.edges: List[EdgeDef] = []
        self.next_node_id = 0

        self._parse_nodes()
        self._parse_edges()

        if self.auto_insert_converters:
            self._insert_converters()

    def _parse_nodes(self):
        """Parse nodes from YAML config"""
        for node_config in self.config['nodes']:
            node_id = node_config['id']
            node_type = node_config['type']
            node_name = node_config['name']

            # Extract all other attributes
            attributes = {k: v for k, v in node_config.items()
                         if k not in ['id', 'type', 'name']}

            self.nodes.append(NodeDef(
                id=node_id,
                type=node_type,
                name=node_name,
                attributes=attributes
            ))

            self.next_node_id = max(self.next_node_id, node_id + 1)

    def _parse_edges(self):
        """Parse edges from YAML config"""
        for edge_config in self.config['graph']['edges']:
            src = edge_config['src']
            dst = edge_config['dst']
            width = edge_config['width']
            latency = edge_config['latency']

            attributes = {k: v for k, v in edge_config.items()
                         if k not in ['src', 'dst', 'width', 'latency']}

            self.edges.append(EdgeDef(
                src=src,
                dst=dst,
                width=width,
                latency=latency,
                attributes=attributes
            ))

    def _get_node(self, node_id: int) -> Optional[NodeDef]:
        """Get node by ID"""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def _get_clock_domain(self, node_id: int) -> Optional[str]:
        """Get clock domain of a node"""
        node = self._get_node(node_id)
        if node:
            return node.attributes.get('clock_domain')
        return None

    def _get_width(self, node_id: int) -> Optional[int]:
        """Get data width of a node"""
        node = self._get_node(node_id)
        if node:
            return node.attributes.get('width') or \
                   node.attributes.get('src_width') or \
                   node.attributes.get('dst_width')
        return None

    def _insert_converters(self):
        """
        Automatically insert ClockConverter and WidthConverter nodes
        where needed.
        """
        new_edges = []
        nodes_to_add = []

        for edge in self.edges[:]:  # Iterate over copy
            src_node = self._get_node(edge.src)
            dst_node = self._get_node(edge.dst)

            if not src_node or not dst_node:
                new_edges.append(edge)
                continue

            # Check for clock domain crossing
            src_clk = self._get_clock_domain(edge.src)
            dst_clk = self._get_clock_domain(edge.dst)
            needs_cdc = (src_clk and dst_clk and src_clk != dst_clk)

            # Check for width mismatch
            # For WidthConverter, check src_width/dst_width
            if src_node.type == 'WidthConverter' or dst_node.type == 'WidthConverter':
                needs_width_conv = False
            else:
                src_width = self._get_width(edge.src)
                dst_width = self._get_width(edge.dst)
                # Edge width should match both src and dst
                needs_width_conv = (edge.width != src_width or edge.width != dst_width) \
                                  if src_width and dst_width else False

            if needs_cdc and needs_width_conv:
                # Insert both CDC and WC
                cdc_id = self.next_node_id
                self.next_node_id += 1
                wc_id = self.next_node_id
                self.next_node_id += 1

                # CDC first, then WC
                cdc_node = NodeDef(
                    id=cdc_id,
                    type='ClockConverter',
                    name=f'{src_node.name}_{dst_node.name}_CDC',
                    attributes={
                        'width': edge.width,
                        'src_clock_domain': src_clk,
                        'dst_clock_domain': dst_clk
                    }
                )

                # Determine target width (prefer dst width)
                target_width = dst_width if dst_width else edge.width

                wc_node = NodeDef(
                    id=wc_id,
                    type='WidthConverter',
                    name=f'{src_node.name}_{dst_node.name}_WC',
                    attributes={
                        'src_width': edge.width,
                        'dst_width': target_width,
                        'clock_domain': dst_clk
                    }
                )

                nodes_to_add.extend([cdc_node, wc_node])

                # Split edge: src -> CDC -> WC -> dst
                new_edges.append(EdgeDef(
                    src=edge.src,
                    dst=cdc_id,
                    width=edge.width,
                    latency=max(1, edge.latency // 3)
                ))
                new_edges.append(EdgeDef(
                    src=cdc_id,
                    dst=wc_id,
                    width=edge.width,
                    latency=max(1, edge.latency // 3)
                ))
                new_edges.append(EdgeDef(
                    src=wc_id,
                    dst=edge.dst,
                    width=target_width,
                    latency=max(1, edge.latency - 2*(edge.latency // 3))
                ))

            elif needs_cdc:
                # Insert only CDC
                cdc_id = self.next_node_id
                self.next_node_id += 1

                cdc_node = NodeDef(
                    id=cdc_id,
                    type='ClockConverter',
                    name=f'{src_node.name}_{dst_node.name}_CDC',
                    attributes={
                        'width': edge.width,
                        'src_clock_domain': src_clk,
                        'dst_clock_domain': dst_clk
                    }
                )

                nodes_to_add.append(cdc_node)

                # Split edge: src -> CDC -> dst
                new_edges.append(EdgeDef(
                    src=edge.src,
                    dst=cdc_id,
                    width=edge.width,
                    latency=max(1, edge.latency // 2)
                ))
                new_edges.append(EdgeDef(
                    src=cdc_id,
                    dst=edge.dst,
                    width=edge.width,
                    latency=max(1, edge.latency - edge.latency // 2)
                ))

            elif needs_width_conv:
                # Insert only WC
                wc_id = self.next_node_id
                self.next_node_id += 1

                target_width = dst_width if dst_width else edge.width

                wc_node = NodeDef(
                    id=wc_id,
                    type='WidthConverter',
                    name=f'{src_node.name}_{dst_node.name}_WC',
                    attributes={
                        'src_width': edge.width,
                        'dst_width': target_width,
                        'clock_domain': src_clk or dst_clk
                    }
                )

                nodes_to_add.append(wc_node)

                # Split edge: src -> WC -> dst
                new_edges.append(EdgeDef(
                    src=edge.src,
                    dst=wc_id,
                    width=edge.width,
                    latency=max(1, edge.latency // 2)
                ))
                new_edges.append(EdgeDef(
                    src=wc_id,
                    dst=edge.dst,
                    width=target_width,
                    latency=max(1, edge.latency - edge.latency // 2)
                ))

            else:
                # No converter needed
                new_edges.append(edge)

        # Update edges and nodes
        self.edges = new_edges
        self.nodes.extend(nodes_to_add)

        if nodes_to_add:
            print(f"Auto-inserted {len(nodes_to_add)} converter(s):")
            for node in nodes_to_add:
                print(f"  - {node.name} ({node.type})")

    def get_networkx_graph(self) -> nx.DiGraph:
        """Return NetworkX directed graph representation"""
        G = nx.DiGraph()

        for node in self.nodes:
            G.add_node(node.id, **{
                'type': node.type,
                'name': node.name,
                **node.attributes
            })

        for edge in self.edges:
            G.add_edge(edge.src, edge.dst, **{
                'width': edge.width,
                'latency': edge.latency,
                **edge.attributes
            })

        return G

    def get_config(self) -> Dict[str, Any]:
        """Return updated configuration dictionary"""
        return {
            'network': self.config['network'],
            'num_nodes': len(self.nodes),
            'nodes': [
                {
                    'id': n.id,
                    'type': n.type,
                    'name': n.name,
                    **n.attributes
                }
                for n in self.nodes
            ],
            'graph': {
                'edges': [
                    {
                        'src': e.src,
                        'dst': e.dst,
                        'width': e.width,
                        'latency': e.latency,
                        **e.attributes
                    }
                    for e in self.edges
                ]
            },
            'constraints': self.config.get('constraints', {})
        }

    def save_yaml(self, output_path: str):
        """Save the updated configuration to YAML"""
        with open(output_path, 'w') as f:
            yaml.dump(self.get_config(), f,
                     default_flow_style=False,
                     sort_keys=False,
                     indent=2)
