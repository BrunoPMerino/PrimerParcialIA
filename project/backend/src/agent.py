from __future__ import annotations

import heapq
import itertools

from dataclasses import dataclass
from typing import Any, Optional

from state import Estado
from scenario_model import ScenarioModel
from problem import (
    crear_estado_inicial,
    es_meta,
    obtener_sucesores,
)


@dataclass(slots=True)
class Nodo:
    """
    Nodo de búsqueda.

    estado:
        situación física.

    padre / acciones:
        historial para reconstruir el plan.

    costo:
        g(n)
    """

    estado: Estado

    padre: Optional["Nodo"] = None

    acciones: Optional[
        list[dict[str, Any]]
    ] = None

    costo: int = 0


def reconstruir_plan(
    node: Nodo,
) -> list[dict[str, Any]]:
    """
    Reconstruye los pasos visuales desde el nodo meta.
    """

    blocks = []

    current = node

    while current.padre is not None:

        if current.acciones:
            blocks.append(
                current.acciones
            )

        current = current.padre

    blocks.reverse()

    plan = []

    for block in blocks:
        plan.extend(
            block
        )

    return plan


# ============================================================
# DOMINANCIA
# ============================================================

def world_key(
    state: Estado,
):
    """
    Misma situación física ignorando únicamente batería.
    """

    return state.clave_sin_bateria()


def is_dominated(
    state: Estado,
    cost: int,
    pareto: dict[
        Any,
        list[tuple[int, int]]
    ],
) -> bool:
    """
    Un nodo está dominado si ya existe:

        mismo mundo
        costo <=
        batería >=
    """

    key = world_key(
        state
    )

    for (
        previous_cost,
        previous_battery,
    ) in pareto.get(
        key,
        (),
    ):

        if (
            previous_cost <= cost
            and previous_battery >= state.bateria
        ):
            return True

    return False


def register_state(
    state: Estado,
    cost: int,
    pareto: dict[
        Any,
        list[tuple[int, int]]
    ],
) -> None:
    """
    Registra una opción no dominada y elimina las opciones
    anteriores que ahora quedan dominadas.
    """

    key = world_key(
        state
    )

    old = pareto.get(
        key
    )

    if old is None:
        pareto[key] = [
            (
                cost,
                state.bateria,
            )
        ]

        return

    new = []

    for (
        previous_cost,
        previous_battery,
    ) in old:

        new_dominates_old = (
            cost <= previous_cost
            and state.bateria >= previous_battery
        )

        if not new_dominates_old:
            new.append(
                (
                    previous_cost,
                    previous_battery,
                )
            )

    new.append(
        (
            cost,
            state.bateria,
        )
    )

    pareto[key] = new


# ============================================================
# UCS
# ============================================================

def buscar_plan(
    model: ScenarioModel,
) -> dict[str, Any]:

    initial_state = crear_estado_inicial(
        model
    )

    initial_node = Nodo(
        estado=initial_state,
        costo=0,
    )

    frontier = []

    counter = itertools.count()

    heapq.heappush(
        frontier,
        (
            0,
            next(counter),
            initial_node,
        ),
    )

    pareto: dict[
        Any,
        list[tuple[int, int]]
    ] = {}

    register_state(
        initial_state,
        0,
        pareto,
    )

    expanded = 0

    while frontier:

        current_cost, _, node = heapq.heappop(
            frontier
        )

        state = node.estado

        key = world_key(
            state
        )

        # -----------------------------------------------------
        # Lazy deletion:
        # si mientras esperaba en OPEN apareció una opción mejor,
        # este nodo ya no se expande.
        # -----------------------------------------------------

        if (
            current_cost,
            state.bateria,
        ) not in pareto.get(
            key,
            (),
        ):
            continue

        expanded += 1

        # -----------------------------------------------------
        # META
        #
        # En UCS se prueba al EXTRAER, no al generar.
        # -----------------------------------------------------

        if es_meta(
            state,
            model,
        ):

            plan = reconstruir_plan(
                node
            )


            return {
                "solution_found": True,
                "total_cost": current_cost,
                "steps": plan,
                "message": (
                    "Plan óptimo encontrado con UCS"
                ),
            }

        # -----------------------------------------------------
        # SUCESORES
        # -----------------------------------------------------

        for (
            actions,
            new_state,
            action_cost,
        ) in obtener_sucesores(
            state,
            model,
        ):

            new_cost = (
                current_cost
                + action_cost
            )

            if is_dominated(
                new_state,
                new_cost,
                pareto,
            ):
                continue

            # Registrar antes de meterlo a OPEN.
            register_state(
                new_state,
                new_cost,
                pareto,
            )

            child = Nodo(
                estado=new_state,
                padre=node,
                acciones=actions,
                costo=new_cost,
            )

            heapq.heappush(
                frontier,
                (
                    new_cost,
                    next(counter),
                    child,
                ),
            )

    return {
        "solution_found": False,
        "total_cost": 0,
        "steps": [],
        "message": (
            "No existe un plan válido para este escenario"
        ),
    }


def solve_scenario(
    scenario: dict[str, Any],
) -> dict[str, Any]:
    """
    Punto de entrada usado por main.py.

    El escenario se indexa UNA sola vez.
    """

    model = ScenarioModel(
        scenario
    )

    return buscar_plan(
        model
    )