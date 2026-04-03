"""Supply chain directed weighted graph model.

Pure data structures with no database or I/O dependencies.  The
``build_network_from_db`` factory converts SQLAlchemy ORM objects into the
simulation-friendly graph representation.
"""

from __future__ import annotations

import copy
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from app.simulation.scenarios import Disruption


# ---------------------------------------------------------------------------
# Graph primitives
# ---------------------------------------------------------------------------

@dataclass
class Node:
    """A location in the supply chain network."""

    id: str
    type: str  # "supplier", "port", "warehouse", "customer"
    name: str
    region: str
    capacity_per_day: float
    lat: float
    lon: float


@dataclass
class Edge:
    """A transport link between two nodes."""

    id: str
    source_id: str
    target_id: str
    transport_mode: str  # "ocean", "air", "rail", "truck"
    base_lead_time: float  # days
    lead_time_std: float
    cost_per_unit: float
    capacity_per_day: float
    reliability: float  # 0-1


# ---------------------------------------------------------------------------
# Network container
# ---------------------------------------------------------------------------

@dataclass
class SupplyChainNetwork:
    """Directed weighted graph of nodes and edges.

    Designed to be cheaply copied so each Monte-Carlo iteration can mutate
    its own copy without affecting others.
    """

    nodes: dict[str, Node] = field(default_factory=dict)
    edges: dict[str, Edge] = field(default_factory=dict)

    # Pre-built adjacency indices (populated by ``_rebuild_index``).
    _outgoing: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list), repr=False)
    _incoming: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list), repr=False)

    # ------------------------------------------------------------------
    # Index helpers
    # ------------------------------------------------------------------

    def _rebuild_index(self) -> None:
        self._outgoing = defaultdict(list)
        self._incoming = defaultdict(list)
        for eid, edge in self.edges.items():
            self._outgoing[edge.source_id].append(eid)
            self._incoming[edge.target_id].append(eid)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def copy(self) -> SupplyChainNetwork:
        """Return a deep copy suitable for mutation inside a single iteration."""
        new_nodes = {nid: copy.copy(n) for nid, n in self.nodes.items()}
        new_edges = {eid: copy.copy(e) for eid, e in self.edges.items()}
        net = SupplyChainNetwork(nodes=new_nodes, edges=new_edges)
        net._rebuild_index()
        return net

    def apply_disruption(self, disruption: Disruption) -> None:
        """Mutate this network in-place according to *disruption*."""
        severity = disruption.severity

        if disruption.type == "route_closure":
            for eid in disruption.affected_ids:
                if eid in self.edges:
                    # Effectively close: capacity -> 0, lead time -> huge
                    self.edges[eid].capacity_per_day = 0.0
                    self.edges[eid].reliability = 0.0

        elif disruption.type == "capacity_reduction":
            remaining = disruption.parameters.get("remaining_fraction", 1.0 - severity)
            for aid in disruption.affected_ids:
                if aid in self.edges:
                    self.edges[aid].capacity_per_day *= remaining
                    # Lead times grow inversely with remaining capacity
                    self.edges[aid].base_lead_time /= max(remaining, 0.05)
                    self.edges[aid].lead_time_std *= 2.0
                elif aid in self.nodes:
                    self.nodes[aid].capacity_per_day *= remaining

        elif disruption.type == "node_shutdown":
            for nid in disruption.affected_ids:
                if nid in self.nodes:
                    self.nodes[nid].capacity_per_day = 0.0
                # Also zero-out every edge touching this node
                for eid in list(self._outgoing.get(nid, [])) + list(self._incoming.get(nid, [])):
                    if eid in self.edges:
                        self.edges[eid].capacity_per_day = 0.0
                        self.edges[eid].reliability = 0.0

        elif disruption.type == "cost_increase":
            multiplier = disruption.parameters.get("cost_multiplier", 1.0 + severity)
            for aid in disruption.affected_ids:
                if aid in self.edges:
                    self.edges[aid].cost_per_unit *= multiplier
                elif aid in self.nodes:
                    # Propagate cost increase to all outgoing edges
                    for eid in self._outgoing.get(aid, []):
                        self.edges[eid].cost_per_unit *= multiplier

        # demand_spike is handled at the engine level, not here.

    def get_edges_from(self, node_id: str) -> list[Edge]:
        return [self.edges[eid] for eid in self._outgoing.get(node_id, []) if eid in self.edges]

    def get_edges_to(self, node_id: str) -> list[Edge]:
        return [self.edges[eid] for eid in self._incoming.get(node_id, []) if eid in self.edges]

    def find_alternative_paths(
        self, source_id: str, target_id: str, max_depth: int = 6
    ) -> list[list[Edge]]:
        """BFS over the graph returning all simple paths up to *max_depth* hops.

        Only considers edges with positive capacity.
        """
        results: list[list[Edge]] = []
        # queue items: (current_node, path_edges, visited_nodes)
        queue: deque[tuple[str, list[Edge], set[str]]] = deque()
        queue.append((source_id, [], {source_id}))

        while queue:
            current, path, visited = queue.popleft()
            if len(path) > max_depth:
                continue
            if current == target_id and path:
                results.append(path)
                continue
            for edge in self.get_edges_from(current):
                if edge.capacity_per_day <= 0:
                    continue
                if edge.target_id in visited:
                    continue
                queue.append((
                    edge.target_id,
                    path + [edge],
                    visited | {edge.target_id},
                ))

        return results


# ---------------------------------------------------------------------------
# Factory: DB records -> SupplyChainNetwork
# ---------------------------------------------------------------------------

def build_network_from_db(
    suppliers: list,
    routes: list,
) -> SupplyChainNetwork:
    """Build a ``SupplyChainNetwork`` from SQLAlchemy ``Supplier`` and
    ``ShippingRoute`` ORM instances.

    Graph topology:
        supplier -> origin_port -> destination_port -> US_DEMAND

    Parameters
    ----------
    suppliers:
        Iterable of ``Supplier`` ORM objects.
    routes:
        Iterable of ``ShippingRoute`` ORM objects.
    """

    nodes: dict[str, Node] = {}
    edges: dict[str, Edge] = {}

    # --- Supplier nodes ---------------------------------------------------
    for s in suppliers:
        nodes[s.id] = Node(
            id=s.id,
            type="supplier",
            name=s.name,
            region=s.region,
            capacity_per_day=float(s.capacity_units),
            lat=0.0,
            lon=0.0,
        )

    # --- Port nodes + route edges -----------------------------------------
    # We derive port nodes from the unique origin/destination ports on routes.
    port_ids: dict[str, str] = {}  # "PortName" -> node id

    def _port_node_id(port_name: str) -> str:
        safe = port_name.replace(" ", "_").upper()
        return f"PORT_{safe}"

    for r in routes:
        # Origin port node
        o_id = _port_node_id(r.origin_port)
        if o_id not in nodes:
            nodes[o_id] = Node(
                id=o_id,
                type="port",
                name=r.origin_port,
                region=r.origin_country,
                capacity_per_day=float(r.capacity_tons) * 5,  # aggregate
                lat=float(r.origin_lat),
                lon=float(r.origin_lon),
            )
        port_ids[r.origin_port] = o_id

        # Destination port node
        d_id = _port_node_id(r.destination_port)
        if d_id not in nodes:
            nodes[d_id] = Node(
                id=d_id,
                type="port",
                name=r.destination_port,
                region=r.destination_country,
                capacity_per_day=float(r.capacity_tons) * 5,
                lat=float(r.dest_lat),
                lon=float(r.dest_lon),
            )
        port_ids[r.destination_port] = d_id

        # Edge: origin_port -> destination_port (the shipping route itself)
        reliability = 1.0 - float(r.risk_score)
        edges[r.id] = Edge(
            id=r.id,
            source_id=o_id,
            target_id=d_id,
            transport_mode=r.transport_mode,
            base_lead_time=float(r.base_transit_days),
            lead_time_std=float(r.transit_variance_days),
            cost_per_unit=float(r.cost_per_kg),
            capacity_per_day=float(r.capacity_tons),
            reliability=reliability,
        )

    # --- Supplier -> nearest origin port edges ----------------------------
    # Heuristic: connect each supplier to every origin port in the same
    # country/region with a short truck/rail link.  If none match, connect
    # to *all* origin ports (fallback).
    origin_ports = {
        nid: n for nid, n in nodes.items() if n.type == "port" and nid.startswith("PORT_")
    }

    for s in suppliers:
        connected = False
        for pid, pnode in origin_ports.items():
            # Check if any route originates from this port in the same country
            same_region = pnode.region == s.country
            if same_region:
                edge_id = f"LINK_{s.id}_{pid}"
                edges[edge_id] = Edge(
                    id=edge_id,
                    source_id=s.id,
                    target_id=pid,
                    transport_mode="truck",
                    base_lead_time=max(1.0, float(s.base_lead_time_days) * 0.2),
                    lead_time_std=float(s.lead_time_variance) * 0.5,
                    cost_per_unit=float(s.cost_multiplier) * 0.10,
                    capacity_per_day=float(s.capacity_units),
                    reliability=float(s.reliability_score),
                )
                connected = True

        # Fallback: if no same-country port, connect to all origin ports
        if not connected:
            for pid, pnode in origin_ports.items():
                edge_id = f"LINK_{s.id}_{pid}"
                edges[edge_id] = Edge(
                    id=edge_id,
                    source_id=s.id,
                    target_id=pid,
                    transport_mode="truck",
                    base_lead_time=float(s.base_lead_time_days) * 0.4,
                    lead_time_std=float(s.lead_time_variance),
                    cost_per_unit=float(s.cost_multiplier) * 0.20,
                    capacity_per_day=float(s.capacity_units) * 0.5,
                    reliability=float(s.reliability_score) * 0.9,
                )

    # --- US_DEMAND customer node ------------------------------------------
    us_demand_id = "US_DEMAND"
    nodes[us_demand_id] = Node(
        id=us_demand_id,
        type="customer",
        name="US Aggregate Demand",
        region="North America",
        capacity_per_day=1e9,  # effectively unlimited
        lat=39.8283,
        lon=-98.5795,
    )

    # Connect all US/destination ports to US_DEMAND
    for nid, n in list(nodes.items()):
        if n.type == "port":
            # Connect destination ports (those that are targets of route edges)
            is_dest = any(e.target_id == nid for e in edges.values())
            if is_dest:
                edge_id = f"LAST_MILE_{nid}"
                edges[edge_id] = Edge(
                    id=edge_id,
                    source_id=nid,
                    target_id=us_demand_id,
                    transport_mode="truck",
                    base_lead_time=2.0,
                    lead_time_std=1.0,
                    cost_per_unit=0.05,
                    capacity_per_day=1e6,
                    reliability=0.98,
                )

    network = SupplyChainNetwork(nodes=nodes, edges=edges)
    network._rebuild_index()
    return network
