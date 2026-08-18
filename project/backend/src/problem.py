from __future__ import annotations

from state import Estado
from scenario_model import ScenarioModel
from relevance import canonicalize_state
from transitions import generar_sucesores


def crear_estado_inicial(
    model: ScenarioModel,
) -> Estado:
    """
    Construye s0 directamente desde el escenario.
    """

    floor = []

    # Llaves
    for key in model.keys:
        floor.append(
            (
                key["zone"],
                key["id"],
                1,
            )
        )

    # Herramientas
    for tool in model.tools:
        floor.append(
            (
                tool["zone"],
                tool["id"],
                1,
            )
        )

    # Materiales equivalentes por tipo
    for material in model.materials:
        floor.append(
            (
                material["zone"],
                material["type"],
                material["count"],
            )
        )

    opened_doors = frozenset(
        door["id"]
        for door in model.doors
        if door.get("state") == "OPEN"
    )

    repaired_panels = frozenset(
        panel["id"]
        for panel in model.panels
        if panel.get("state") == "REPAIRED"
    )

    online_stations = frozenset(
        station["id"]
        for station in model.stations
        if station.get("state") == "ONLINE"
    )

    state = Estado(
        zona=model.start,
        bateria=model.battery_start,
        carga=tuple(),
        suelo=tuple(sorted(floor)),
        puertas_abiertas=opened_doors,
        paneles_reparados=repaired_panels,
        estaciones_online=online_stations,
    )

    return canonicalize_state(
        state,
        model,
    )


def es_meta(
    state: Estado,
    model: ScenarioModel,
) -> bool:
    """
    Goal(s):
    todas las estaciones pedidas deben estar ONLINE.
    """

    return model.goal_stations.issubset(
        state.estaciones_online
    )


def obtener_sucesores(
    state: Estado,
    model: ScenarioModel,
):
    """
    Applicable + Result.
    """

    return generar_sucesores(
        state,
        model,
    )