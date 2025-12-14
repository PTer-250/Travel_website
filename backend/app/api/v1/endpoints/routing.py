"""Routing endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.api import deps
from app.algorithms import WeightStrategy
from app.services import NodeValidationError, RegionNotFoundError, RouteNotFoundError, RoutingService
from app.schemas import RoutePlanResponse, RouteSegment, RouteNode

router = APIRouter(prefix="/routing", tags=["routing"])


@router.get("/routes", response_model=RoutePlanResponse)
async def compute_route(
    *,
    region_id: int = Query(..., description="Region identifier containing the graph"),
    start_node_id: int = Query(..., description="Starting graph node identifier"),
    end_node_id: int = Query(..., description="Destination graph node identifier"),
    strategy: WeightStrategy = Query(WeightStrategy.TIME, description="Optimisation strategy"),
    transport_modes: List[str] | None = Query(
        None,
        description="Optional list of desired transport modes (walk, bike, electric_cart)",
    ),
    service: RoutingService = Depends(deps.get_routing_service),
) -> RoutePlanResponse:
    try:
        plan = await service.compute_route(
            region_id=region_id,
            start_node_id=start_node_id,
            end_node_id=end_node_id,
            strategy=strategy,
            transport_modes=transport_modes,
        )
    except RegionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except NodeValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RouteNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    generated_at = datetime.now(timezone.utc)
    return RoutePlanResponse(
        region_id=plan.region_id,
        strategy=plan.strategy,
        total_distance=plan.total_distance,
        total_time=plan.total_time,
    nodes=[RouteNode.model_validate(node) for node in plan.nodes],
    segments=[RouteSegment.model_validate(segment) for segment in plan.segments],
        generated_at=generated_at,
        allowed_transport_modes=list(plan.allowed_modes),
    )


@router.get("/multi-route", response_model=RoutePlanResponse)
async def compute_multi_route(
    *,
    region_id: int = Query(..., description="Region identifier containing the graph"),
    waypoint_node_ids: List[int] = Query(..., description="Intermediate waypoint node identifiers"),
    start_node_id: int | None = Query(None, description="Optional starting node"),
    end_node_id: int | None = Query(None, description="Optional ending node"),
    strategy: WeightStrategy = Query(WeightStrategy.TIME, description="Optimisation strategy"),
    transport_modes: List[str] | None = Query(
        None,
        description="Optional list of desired transport modes (walk, bike, electric_cart)",
    ),
    service: RoutingService = Depends(deps.get_routing_service),
) -> RoutePlanResponse:
    try:
        plan = await service.compute_multi_route(
            region_id=region_id,
            waypoint_node_ids=waypoint_node_ids,
            start_node_id=start_node_id,
            end_node_id=end_node_id,
            strategy=strategy,
            transport_modes=transport_modes,
        )
    except RegionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except NodeValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RouteNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    generated_at = datetime.now(timezone.utc)
    return RoutePlanResponse(
        region_id=plan.region_id,
        strategy=plan.strategy,
        total_distance=plan.total_distance,
        total_time=plan.total_time,
        nodes=[RouteNode.model_validate(node) for node in plan.nodes],
        segments=[RouteSegment.model_validate(segment) for segment in plan.segments],
        generated_at=generated_at,
        allowed_transport_modes=list(plan.allowed_modes),
    )


class MultiRouteRequest(BaseModel):
    region_id: int
    waypoint_node_ids: List[int]
    start_node_id: int | None = None
    end_node_id: int | None = None
    strategy: WeightStrategy = WeightStrategy.TIME
    transport_modes: List[str] | None = None


@router.post("/multi-route", response_model=RoutePlanResponse)
async def compute_multi_route_post(
    payload: MultiRouteRequest,
    service: RoutingService = Depends(deps.get_routing_service),
) -> RoutePlanResponse:
    try:
        plan = await service.compute_multi_route(
            region_id=payload.region_id,
            waypoint_node_ids=payload.waypoint_node_ids,
            start_node_id=payload.start_node_id,
            end_node_id=payload.end_node_id,
            strategy=payload.strategy,
            transport_modes=payload.transport_modes,
        )
    except RegionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except NodeValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RouteNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    generated_at = datetime.now(timezone.utc)
    return RoutePlanResponse(
        region_id=plan.region_id,
        strategy=plan.strategy,
        total_distance=plan.total_distance,
        total_time=plan.total_time,
        nodes=[RouteNode.model_validate(node) for node in plan.nodes],
        segments=[RouteSegment.model_validate(segment) for segment in plan.segments],
        generated_at=generated_at,
        allowed_transport_modes=list(plan.allowed_modes),
    )


