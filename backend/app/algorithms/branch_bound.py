"""Branch-and-bound solver for fixed-start/end multi-point routing.

This module computes an order to visit a set of target nodes starting at a fixed
start node and ending at a fixed end node, minimising either total distance or
total time. It uses precomputed pairwise shortest paths and explores the search
space with simple branch-and-bound pruning. For larger target sets, the search
may fall back to a greedy heuristic to avoid combinatorial explosion.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import inf
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .shortest_path import Edge, PathResult, WeightStrategy, shortest_path


PairKey = Tuple[str, str]
PairMap = Dict[PairKey, PathResult]


@dataclass(frozen=True)
class PathOrderResult:
    route: List[str]  # sequence of node ids (as strings) including start and end
    legs: List[PathResult]  # per-pair shortest paths for consecutive nodes
    total_distance: float
    total_time: float


class BranchBoundError(RuntimeError):
    pass


def compute_pair_paths(
    edges: Iterable[Edge],
    nodes: Sequence[str],
    *,
    allowed_modes: Optional[Sequence[str] | str] = None,
    strategy: WeightStrategy | str = WeightStrategy.TIME,
) -> PairMap:
    """Precompute shortest paths for all ordered node pairs in ``nodes``."""
    pair_paths: PairMap = {}
    edge_list = list(edges)
    strat = WeightStrategy(strategy)
    for a in nodes:
        for b in nodes:
            if a == b:
                continue
            key = (a, b)
            if key in pair_paths:
                continue
            pair_paths[key] = shortest_path(
                edge_list,
                start=a,
                goal=b,
                allowed_modes=allowed_modes,
                strategy=strat,
            )
    return pair_paths


def compute_path_branch_and_bound(
    edges: Iterable[Edge],
    start: str,
    end: str,
    targets: Sequence[str],
    *,
    allowed_modes: Optional[Sequence[str] | str] = None,
    strategy: WeightStrategy | str = WeightStrategy.TIME,
    max_targets_for_exact: int = 10,
) -> PathOrderResult:
    """Compute an optimal visiting order from ``start`` to ``end`` over ``targets``.

    If the number of unique targets exceeds ``max_targets_for_exact``, falls back
    to a greedy nearest-neighbour heuristic.
    """

    strat = WeightStrategy(strategy)
    unique_targets = list(dict.fromkeys(t for t in targets if t not in (start, end)))
    nodes = [start, end] + unique_targets
    pair_paths = compute_pair_paths(edges, nodes, allowed_modes=allowed_modes, strategy=strat)

    # Helper to get cost between two nodes
    def cost(a: str, b: str) -> float:
        p = pair_paths.get((a, b))
        if p is None:
            return inf
        return p.total_distance if strat is WeightStrategy.DISTANCE else p.total_time

    # Fallback to greedy when too many targets
    if len(unique_targets) > max_targets_for_exact:
        route: List[str] = [start]
        remaining = set(unique_targets)
        current = start
        while remaining:
            next_node = min(remaining, key=lambda n: cost(current, n))
            route.append(next_node)
            remaining.remove(next_node)
            current = next_node
        route.append(end)
        legs: List[PathResult] = [pair_paths[(a, b)] for a, b in zip(route, route[1:])]
        total_distance = sum(p.total_distance for p in legs)
        total_time = sum(p.total_time for p in legs)
        return PathOrderResult(route=route, legs=legs, total_distance=total_distance, total_time=total_time)

    # Branch-and-bound search
    best_route: List[str] | None = None
    best_cost: float = inf

    # Precompute minimal outgoing cost per node to assist lower bounds
    min_out: Dict[str, float] = {}
    for n in [start] + unique_targets:
        # allow destination among remaining targets or the end
        candidates = [m for m in unique_targets + [end] if m != n]
        min_out[n] = min((cost(n, m) for m in candidates), default=inf)

    def lower_bound(current_cost: float, last: str, remaining: Sequence[str]) -> float:
        # Simple admissible-ish bound: cost so far + min to end from last + sum of min_out for remaining
        lb = current_cost
        lb += cost(last, end)
        for r in remaining:
            lb += min_out.get(r, 0.0)
        return lb

    def dfs(path: List[str], used: set[str], current_cost: float) -> None:
        nonlocal best_route, best_cost
        last = path[-1]
        remaining = [t for t in unique_targets if t not in used]

        # Bound pruning
        if lower_bound(current_cost, last, remaining) >= best_cost:
            return

        if not remaining:
            final_cost = current_cost + cost(last, end)
            if final_cost < best_cost:
                best_cost = final_cost
                best_route = path + [end]
            return

        # Explore remaining targets
        for nxt in remaining:
            step_cost = cost(last, nxt)
            if step_cost >= inf:
                continue
            dfs(path + [nxt], used | {nxt}, current_cost + step_cost)

    dfs([start], set(), 0.0)

    if not best_route:
        raise BranchBoundError("No feasible route found for given nodes")

    legs: List[PathResult] = [pair_paths[(a, b)] for a, b in zip(best_route, best_route[1:])]
    total_distance = sum(p.total_distance for p in legs)
    total_time = sum(p.total_time for p in legs)
    return PathOrderResult(route=best_route, legs=legs, total_distance=total_distance, total_time=total_time)
