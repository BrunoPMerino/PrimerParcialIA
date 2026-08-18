from __future__ import annotations

from state import Estado
from scenario_model import ScenarioModel


def key_is_relevant(
    item: str,
    state: Estado,
    model: ScenarioModel,
) -> bool:
    """
    Una llave es relevante mientras alguna de sus
    puertas todavía esté cerrada.
    """

    for door in model.doors_by_key.get(
        item,
        [],
    ):
        if door["id"] not in state.puertas_abiertas:
            return True

    return False


def tool_is_relevant(
    item: str,
    state: Estado,
    model: ScenarioModel,
) -> bool:
    """
    La herramienta importa mientras quede un panel
    necesario y sin reparar que la utilice.
    """

    for panel_id in model.panels_by_tool.get(
        item,
        set(),
    ):
        if panel_id not in model.required_panels:
            continue

        if panel_id not in state.paneles_reparados:
            return True

    return False


def material_is_relevant(
    item: str,
    state: Estado,
    model: ScenarioModel,
) -> bool:
    """
    El material importa mientras quede un panel necesario
    y sin reparar que lo consuma.
    """

    for panel_id in model.panels_by_material.get(
        item,
        set(),
    ):
        if panel_id not in model.required_panels:
            continue

        if panel_id not in state.paneles_reparados:
            return True

    return False


def item_is_relevant(
    item: str,
    state: Estado,
    model: ScenarioModel,
) -> bool:

    if item in model.key_ids:
        return key_is_relevant(
            item,
            state,
            model,
        )

    if item in model.tool_ids:
        return tool_is_relevant(
            item,
            state,
            model,
        )

    if item in model.material_types:
        return material_is_relevant(
            item,
            state,
            model,
        )

    return False


def remaining_material_needed(
    material: str,
    state: Estado,
    model: ScenarioModel,
) -> int:
    """
    Cantidad máxima que todavía puede consumirse
    de este material.
    """

    total = 0

    for panel_id in model.panels_by_material.get(
        material,
        set(),
    ):
        if panel_id not in model.required_panels:
            continue

        if panel_id in state.paneles_reparados:
            continue

        total += 1

    return total


def normalize_floor(
    state: Estado,
    model: ScenarioModel,
) -> tuple:
    """
    Elimina del estado objetos que están en el suelo
    y que ya no pueden cambiar ninguna acción futura.

    No se eliminan objetos de la carga porque siguen
    ocupando capacidad física.
    """

    result = []

    for zone, item, quantity in state.suelo:

        if item_is_relevant(
            item,
            state,
            model,
        ):
            result.append(
                (
                    zone,
                    item,
                    quantity,
                )
            )

    return tuple(
        sorted(result)
    )


def canonicalize_state(
    state: Estado,
    model: ScenarioModel,
) -> Estado:

    floor = normalize_floor(
        state,
        model,
    )

    if floor == state.suelo:
        return state

    return Estado(
        zona=state.zona,
        bateria=state.bateria,
        carga=state.carga,
        suelo=floor,
        puertas_abiertas=state.puertas_abiertas,
        paneles_reparados=state.paneles_reparados,
        estaciones_online=state.estaciones_online,
    )