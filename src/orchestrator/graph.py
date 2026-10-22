"""
Explicit Dependency Graph (DAG) for SDLC Orchestration.
Supports sequential and parallel paths with synchronization, entry/exit gates, and topological scheduling.
"""

from __future__ import annotations
import networkx as nx
from typing import Any, Callable, Dict, List, Optional, Set
from pydantic import BaseModel, ConfigDict, Field
from src.orchestrator.state import SDLCPhase, TaskStatus

class GateCondition(BaseModel):
    name: str
    description: str
    required_artifacts: List[str] = Field(default_factory=list)
    validator_func_name: Optional[str] = None

class DAGNode(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    name: str
    phase: SDLCPhase
    description: str
    dependencies: List[str] = Field(default_factory=list)
    entry_gate: Optional[GateCondition] = None
    exit_gate: Optional[GateCondition] = None
    is_hitl_checkpoint: bool = False
    hitl_prompt: Optional[str] = None
    max_retries: int = 2
    allow_parallel: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ExecutionGraph:
    """
    Explicit Directed Acyclic Graph (DAG) representing the stateful SDLC workflow.
    Validates acyclicity, manages execution layers for concurrency, and tracks gates.
    """
    def __init__(self, name: str = "SDLC_Pipeline"):
        self.name = name
        self.nodes: Dict[str, DAGNode] = {}
        self.graph = nx.DiGraph()

    def add_node(self, node: DAGNode) -> ExecutionGraph:
        if node.id in self.nodes:
            raise ValueError(f"Node '{node.id}' already exists in graph.")
        self.nodes[node.id] = node
        self.graph.add_node(node.id, data=node)
        for dep in node.dependencies:
            self.graph.add_edge(dep, node.id)
        return self

    def add_dependency(self, from_node_id: str, to_node_id: str) -> None:
        if from_node_id not in self.nodes:
            raise ValueError(f"Upstream node '{from_node_id}' does not exist.")
        if to_node_id not in self.nodes:
            raise ValueError(f"Downstream node '{to_node_id}' does not exist.")
        self.graph.add_edge(from_node_id, to_node_id)
        if from_node_id not in self.nodes[to_node_id].dependencies:
            self.nodes[to_node_id].dependencies.append(from_node_id)

    def validate(self) -> None:
        """Validate DAG: check acyclicity, existence of all dependencies."""
        if not nx.is_directed_acyclic_graph(self.graph):
            cycles = list(nx.simple_cycles(self.graph))
            raise ValueError(f"Cyclic dependency detected in execution graph: {cycles}")
        for node_id, node in self.nodes.items():
            for dep in node.dependencies:
                if dep not in self.nodes:
                    raise ValueError(f"Node '{node_id}' depends on missing node '{dep}'")

    def get_topological_order(self) -> List[str]:
        self.validate()
        return list(nx.topological_sort(self.graph))

    def get_execution_layers(self) -> List[List[str]]:
        """
        Calculates execution layers (stages of nodes that can run concurrently in parallel).
        Layer 0 nodes have 0 dependencies. Layer N depends only on nodes in layers < N.
        This provides parallel execution with synchronization barriers!
        """
        self.validate()
        layers: List[List[str]] = []
        in_degree = dict(self.graph.in_degree())
        current_layer = [n for n, deg in in_degree.items() if deg == 0]
        
        visited: Set[str] = set(current_layer)
        while current_layer:
            layers.append(sorted(current_layer))
            next_layer: List[str] = []
            for node in current_layer:
                for successor in self.graph.successors(node):
                    if successor not in visited:
                        # Check if all predecessors are visited
                        preds = list(self.graph.predecessors(successor))
                        if all(p in visited for p in preds):
                            visited.add(successor)
                            next_layer.append(successor)
            current_layer = next_layer
        return layers

    def get_upstream_nodes(self, node_id: str) -> List[str]:
        """All direct ancestors."""
        return list(self.graph.predecessors(node_id))

    def get_all_downstream_nodes(self, node_id: str) -> List[str]:
        """All descendants affected if this node changes (re-planning blast radius)."""
        return list(nx.descendants(self.graph, node_id))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "nodes": {nid: n.model_dump() for nid, n in self.nodes.items()},
            "edges": list(self.graph.edges()),
            "layers": self.get_execution_layers()
        }
