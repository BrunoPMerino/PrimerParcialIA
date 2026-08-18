from __future__ import annotations

from itertools import combinations

from state import Estado
from scenario_model import ScenarioModel
from relevance import (
    canonicalize_state,
    item_is_relevant,
    remaining_material_needed,
)


# ============================================================
# UTILIDADES DE CARGA
# ============================================================

def load_weight(
    state: Estado,
    model: ScenarioModel,
) -> int:

    total = 0

    for item, quantity in state.carga:
        total += (
            model.weights[item]
            * quantity
        )

    return total


def load_quantity(
    state: Estado,
    item: str,
) -> int:

    return dict(
        state.carga
    ).get(
        item,
        0,
    )


def add_to_load(
    load: tuple,
    item: str,
    quantity: int = 1,
) -> tuple:

    data = dict(load)

    data[item] = (
        data.get(item, 0)
        + quantity
    )

    return tuple(
        sorted(data.items())
    )


def remove_from_load(
    load: tuple,
    item: str,
    quantity: int = 1,
) -> tuple:

    data = dict(load)

    remaining = (
        data[item]
        - quantity
    )

    if remaining <= 0:
        del data[item]

    else:
        data[item] = remaining

    return tuple(
        sorted(data.items())
    )


# ============================================================
# SUELO
# ============================================================

def items_in_zone(
    state: Estado,
) -> dict[str, int]:

    result = {}

    for zone, item, quantity in state.suelo:

        if zone == state.zona:
            result[item] = (
                result.get(item, 0)
                + quantity
            )

    return result


def remove_from_floor(
    floor: tuple,
    zone: str,
    item: str,
    quantity: int = 1,
) -> tuple:

    data = {
        (z, obj): qty
        for z, obj, qty in floor
    }

    key = (
        zone,
        item,
    )

    remaining = (
        data[key]
        - quantity
    )

    if remaining <= 0:
        del data[key]

    else:
        data[key] = remaining

    return tuple(
        sorted(
            (
                z,
                obj,
                qty,
            )
            for (z, obj), qty
            in data.items()
            if qty > 0
        )
    )


def add_to_floor(
    floor: tuple,
    zone: str,
    item: str,
    quantity: int = 1,
) -> tuple:

    data = {
        (z, obj): qty
        for z, obj, qty in floor
    }

    key = (
        zone,
        item,
    )

    data[key] = (
        data.get(key, 0)
        + quantity
    )

    return tuple(
        sorted(
            (
                z,
                obj,
                qty,
            )
            for (z, obj), qty
            in data.items()
            if qty > 0
        )
    )


# ============================================================
# DROP + PICKUP
# ============================================================

def expanded_load(
    state: Estado,
) -> list[str]:

    result = []

    for item, quantity in state.carga:

        result.extend(
            [item] * quantity
        )

    return result


def items_weight(
    items: tuple[str, ...],
    model: ScenarioModel,
) -> int:

    return sum(
        model.weights[item]
        for item in items
    )


def minimal_drop_sets(
    state: Estado,
    wanted_item: str,
    model: ScenarioModel,
) -> list[tuple[str, ...]]:
    """
    Devuelve únicamente conjuntos mínimos que liberan
    suficiente capacidad.

    DROP A -> DROP B y DROP B -> DROP A se consideran
    la misma decisión interna.
    """

    current_weight = load_weight(
        state,
        model,
    )

    needed = (
        current_weight
        + model.weights[wanted_item]
        - model.capacity
    )

    if needed <= 0:
        return []

    units = expanded_load(
        state
    )

    candidates: set[
        tuple[str, ...]
    ] = set()

    for size in range(
        1,
        len(units) + 1,
    ):

        for combo_raw in combinations(
            units,
            size,
        ):
            combo = tuple(
                sorted(combo_raw)
            )

            if combo in candidates:
                continue

            freed = items_weight(
                combo,
                model,
            )

            if freed < needed:
                continue

            # Debe ser mínimo por inclusión.
            minimal = True

            for i in range(
                len(combo)
            ):
                reduced = (
                    combo[:i]
                    + combo[i + 1:]
                )

                if (
                    items_weight(
                        reduced,
                        model,
                    )
                    >= needed
                ):
                    minimal = False
                    break

            if minimal:
                candidates.add(
                    combo
                )

    return list(
        candidates
    )


def apply_drops(
    state: Estado,
    items: tuple[str, ...],
) -> tuple[tuple, tuple]:

    load = state.carga
    floor = state.suelo

    for item in items:

        load = remove_from_load(
            load,
            item,
        )

        floor = add_to_floor(
            floor,
            state.zona,
            item,
        )

    return (
        load,
        floor,
    )


# ============================================================
# MOVE
# ============================================================

def generate_moves(
    state: Estado,
    model: ScenarioModel,
):

    result = []

    # corridor list already has directions.
    for corridor in model.corridors_from.get(
        state.zona,
        [],
    ):
        cost = corridor["cost"]

        if state.bateria < cost:
            continue

        door = corridor.get(
            "door"
        )

        if (
            door is not None
            and door not in state.puertas_abiertas
        ):
            continue

        destination = corridor["to"]

        new_state = Estado(
            zona=destination,
            bateria=state.bateria - cost,
            carga=state.carga,
            suelo=state.suelo,
            puertas_abiertas=state.puertas_abiertas,
            paneles_reparados=state.paneles_reparados,
            estaciones_online=state.estaciones_online,
        )

        new_state = canonicalize_state(
            new_state,
            model,
        )

        actions = [
            {
                "op": "MOVE",
                "from": state.zona,
                "to": destination,
                "cost": cost,
            }
        ]

        result.append(
            (
                actions,
                new_state,
                cost,
            )
        )

    return result


# ============================================================
# PICKUP / INTERCAMBIO
# ============================================================

def generate_pickups(
    state: Estado,
    model: ScenarioModel,
):

    result = []

    pickup_cost = model.costs[
        "pickup"
    ]

    drop_cost = model.costs[
        "drop"
    ]

    floor_items = items_in_zone(
        state
    )

    current_weight = load_weight(
        state,
        model,
    )

    for item, quantity in floor_items.items():

        if quantity <= 0:
            continue

        if not item_is_relevant(
            item,
            state,
            model,
        ):
            continue

        # -----------------------------------------------
        # No recoger materiales sobrantes.
        # -----------------------------------------------

        if item in model.material_types:

            needed = remaining_material_needed(
                item,
                state,
                model,
            )

            carrying = load_quantity(
                state,
                item,
            )

            if carrying >= needed:
                continue

        item_weight = model.weights[
            item
        ]

        # ===============================================
        # PICKUP NORMAL
        # ===============================================

        if (
            current_weight
            + item_weight
            <= model.capacity
        ):
            if state.bateria < pickup_cost:
                continue

            new_load = add_to_load(
                state.carga,
                item,
            )

            new_floor = remove_from_floor(
                state.suelo,
                state.zona,
                item,
            )

            new_state = Estado(
                zona=state.zona,
                bateria=(
                    state.bateria
                    - pickup_cost
                ),
                carga=new_load,
                suelo=new_floor,
                puertas_abiertas=state.puertas_abiertas,
                paneles_reparados=state.paneles_reparados,
                estaciones_online=state.estaciones_online,
            )

            new_state = canonicalize_state(
                new_state,
                model,
            )

            result.append(
                (
                    [
                        {
                            "op": "PICKUP",
                            "item": item,
                            "cost": pickup_cost,
                        }
                    ],
                    new_state,
                    pickup_cost,
                )
            )

            continue

        # ===============================================
        # INTERCAMBIO DROP + PICKUP
        # ===============================================

        for drops in minimal_drop_sets(
            state,
            item,
            model,
        ):

            total_cost = (
                len(drops)
                * drop_cost
                + pickup_cost
            )

            if state.bateria < total_cost:
                continue

            new_load, new_floor = apply_drops(
                state,
                drops,
            )

            new_load = add_to_load(
                new_load,
                item,
            )

            new_floor = remove_from_floor(
                new_floor,
                state.zona,
                item,
            )

            new_state = Estado(
                zona=state.zona,
                bateria=(
                    state.bateria
                    - total_cost
                ),
                carga=new_load,
                suelo=new_floor,
                puertas_abiertas=state.puertas_abiertas,
                paneles_reparados=state.paneles_reparados,
                estaciones_online=state.estaciones_online,
            )

            new_state = canonicalize_state(
                new_state,
                model,
            )

            actions = []

            for dropped in drops:

                actions.append(
                    {
                        "op": "DROP",
                        "item": dropped,
                        "cost": drop_cost,
                    }
                )

            actions.append(
                {
                    "op": "PICKUP",
                    "item": item,
                    "cost": pickup_cost,
                }
            )

            result.append(
                (
                    actions,
                    new_state,
                    total_cost,
                )
            )

    return result


# ============================================================
# OPEN DOOR
# ============================================================

def generate_open_doors(
    state: Estado,
    model: ScenarioModel,
):

    result = []

    cost = model.costs[
        "interact"
    ]

    if state.bateria < cost:
        return result

    for door in model.doors_by_zone.get(
        state.zona,
        [],
    ):
        door_id = door["id"]

        if door_id in state.puertas_abiertas:
            continue

        key = door["key"]

        if load_quantity(
            state,
            key,
        ) <= 0:
            continue

        opened = set(
            state.puertas_abiertas
        )

        opened.add(
            door_id
        )

        new_state = Estado(
            zona=state.zona,
            bateria=state.bateria - cost,
            carga=state.carga,
            suelo=state.suelo,
            puertas_abiertas=frozenset(opened),
            paneles_reparados=state.paneles_reparados,
            estaciones_online=state.estaciones_online,
        )

        new_state = canonicalize_state(
            new_state,
            model,
        )

        result.append(
            (
                [
                    {
                        "op": "INTERACT",
                        "target": door_id,
                        "action": "OPEN_DOOR",
                        "cost": cost,
                    }
                ],
                new_state,
                cost,
            )
        )

    return result


# ============================================================
# REPAIR
# ============================================================

def generate_repairs(
    state: Estado,
    model: ScenarioModel,
):

    result = []

    cost = model.costs[
        "interact"
    ]

    if state.bateria < cost:
        return result

    for panel in model.panels_by_zone.get(
        state.zona,
        [],
    ):

        panel_id = panel["id"]

        if panel_id not in model.required_panels:
            continue

        if panel_id in state.paneles_reparados:
            continue

        tool = panel["requires"]["tool"]
        material = panel["requires"]["material"]

        if load_quantity(
            state,
            tool,
        ) <= 0:
            continue

        if load_quantity(
            state,
            material,
        ) <= 0:
            continue

        repaired = set(
            state.paneles_reparados
        )

        repaired.add(
            panel_id
        )

        new_load = remove_from_load(
            state.carga,
            material,
        )

        new_state = Estado(
            zona=state.zona,
            bateria=state.bateria - cost,
            carga=new_load,
            suelo=state.suelo,
            puertas_abiertas=state.puertas_abiertas,
            paneles_reparados=frozenset(repaired),
            estaciones_online=state.estaciones_online,
        )

        new_state = canonicalize_state(
            new_state,
            model,
        )

        result.append(
            (
                [
                    {
                        "op": "INTERACT",
                        "target": panel_id,
                        "action": "REPAIR",
                        "consumes": material,
                        "cost": cost,
                    }
                ],
                new_state,
                cost,
            )
        )

    return result


# ============================================================
# ACTIVATE
# ============================================================

def generate_activations(
    state: Estado,
    model: ScenarioModel,
):

    result = []

    cost = model.costs[
        "interact"
    ]

    if state.bateria < cost:
        return result

    for station in model.stations_by_zone.get(
        state.zona,
        [],
    ):

        station_id = station["id"]

        if station_id not in model.required_stations:
            continue

        if station_id in state.estaciones_online:
            continue

        requires = station.get(
            "requires",
            {},
        )

        needed_panels = set(
            requires.get(
                "panels_ok",
                [],
            )
        )

        needed_stations = set(
            requires.get(
                "stations_online",
                [],
            )
        )

        if not needed_panels.issubset(
            state.paneles_reparados
        ):
            continue

        if not needed_stations.issubset(
            state.estaciones_online
        ):
            continue

        online = set(
            state.estaciones_online
        )

        online.add(
            station_id
        )

        new_state = Estado(
            zona=state.zona,
            bateria=state.bateria - cost,
            carga=state.carga,
            suelo=state.suelo,
            puertas_abiertas=state.puertas_abiertas,
            paneles_reparados=state.paneles_reparados,
            estaciones_online=frozenset(online),
        )

        new_state = canonicalize_state(
            new_state,
            model,
        )

        result.append(
            (
                [
                    {
                        "op": "INTERACT",
                        "target": station_id,
                        "action": "ACTIVATE",
                        "cost": cost,
                    }
                ],
                new_state,
                cost,
            )
        )

    return result


# ============================================================
# RECHARGE
# ============================================================

def generate_recharges(
    state: Estado,
    model: ScenarioModel,
):

    result = []

    cost = model.costs[
        "recharge"
    ]

    if state.bateria < cost:
        return result

    if state.bateria >= model.battery_max:
        return result

    for charger in model.chargers_by_zone.get(
        state.zona,
        [],
    ):

        new_state = Estado(
            zona=state.zona,

            # El contrato dice que primero paga la acción y luego queda restaurada a battery_max.
            bateria=model.battery_max,

            carga=state.carga,
            suelo=state.suelo,
            puertas_abiertas=state.puertas_abiertas,
            paneles_reparados=state.paneles_reparados,
            estaciones_online=state.estaciones_online,
        )

        new_state = canonicalize_state(
            new_state,
            model,
        )

        result.append(
            (
                [
                    {
                        "op": "INTERACT",
                        "target": charger["id"],
                        "action": "RECHARGE",
                        "cost": cost,
                    }
                ],
                new_state,
                cost,
            )
        )

    return result


# ============================================================
# GENERADOR GENERAL
# ============================================================

def generar_sucesores(
    state: Estado,
    model: ScenarioModel,
):

    successors = []

    successors.extend(
        generate_moves(
            state,
            model,
        )
    )

    successors.extend(
        generate_pickups(
            state,
            model,
        )
    )

    successors.extend(
        generate_open_doors(
            state,
            model,
        )
    )

    successors.extend(
        generate_repairs(
            state,
            model,
        )
    )

    successors.extend(
        generate_activations(
            state,
            model,
        )
    )

    successors.extend(
        generate_recharges(
            state,
            model,
        )
    )

    return successors