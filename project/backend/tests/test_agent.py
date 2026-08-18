from __future__ import annotations

import copy
import sys
from pathlib import Path

# Permite importar los archivos de backend/src
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from agent import solve_scenario
from state import Estado
from simulator import (
    goal_satisfied,
    load_scenario,
    simulate,
)


# ============================================================
# 1. ESTADOS EQUIVALENTES
# ============================================================

def test_estados_equivalentes() -> None:
    """
    El orden de los objetos de la carga no debe hacer
    que dos estados físicamente iguales sean diferentes.
    """

    estado1 = Estado(
        zona="Z1",
        bateria=50,
        carga=(
            ("FUSE", 1),
            ("KEY1", 1),
        ),
        suelo=(),
        puertas_abiertas=frozenset(),
        paneles_reparados=frozenset(),
        estaciones_online=frozenset(),
    )

    estado2 = Estado(
        zona="Z1",
        bateria=50,
        carga=(
            ("KEY1", 1),
            ("FUSE", 1),
        ),
        suelo=(),
        puertas_abiertas=frozenset(),
        paneles_reparados=frozenset(),
        estaciones_online=frozenset(),
    )

    assert estado1 == estado2
    assert hash(estado1) == hash(estado2)


# ============================================================
# 2. INFORMACIÓN RELEVANTE
# ============================================================

def test_bateria_distingue_estados() -> None:
    """
    La batería sí pertenece al estado.

    Dos configuraciones iguales excepto por batería
    deben ser estados diferentes.
    """

    estado1 = Estado(
        zona="Z1",
        bateria=50,
        carga=(),
        suelo=(),
        puertas_abiertas=frozenset(),
        paneles_reparados=frozenset(),
        estaciones_online=frozenset(),
    )

    estado2 = Estado(
        zona="Z1",
        bateria=20,
        carga=(),
        suelo=(),
        puertas_abiertas=frozenset(),
        paneles_reparados=frozenset(),
        estaciones_online=frozenset(),
    )

    assert estado1 != estado2


# ============================================================
# 3. EL PLAN REAL DEBE SER LEGAL Y LLEGAR A LA META
# ============================================================

def test_plan_real_llega_a_meta() -> None:
    """
    Ejecuta el escenario oficial completo.

    Después vuelve a ejecutar cada paso usando simulator.py,
    que representa las reglas independientes del frontend.
    """

    scenario = load_scenario()

    resultado = solve_scenario(
        scenario
    )

    assert resultado["solution_found"] is True

    assert len(
        resultado["steps"]
    ) > 0

    # El costo reportado debe coincidir con la suma de los costos de cada paso.
    costo_calculado = sum(
        paso["cost"]
        for paso in resultado["steps"]
    )

    assert (
        resultado["total_cost"]
        == costo_calculado
    )

    # El simulador oficial vuelve a ejecutar el plan.
    final = simulate(
        scenario,
        resultado["steps"],
    )

    assert goal_satisfied(
        scenario,
        final,
    )

    # El costo también debe coincidir con la energía gastada según el simulador.
    assert (
        final["energy_spent"]
        == resultado["total_cost"]
    )


# ============================================================
# 4. CONTRATO DE OPERACIONES
# ============================================================

def test_plan_respeta_operaciones_permitidas() -> None:
    """
    El frontend solo acepta:
    MOVE, PICKUP, DROP e INTERACT.
    """

    scenario = load_scenario()

    resultado = solve_scenario(
        scenario
    )

    operaciones_validas = {
        "MOVE",
        "PICKUP",
        "DROP",
        "INTERACT",
    }

    interacciones_validas = {
        "OPEN_DOOR",
        "REPAIR",
        "ACTIVATE",
        "RECHARGE",
    }

    for paso in resultado["steps"]:

        assert (
            paso["op"]
            in operaciones_validas
        )

        if paso["op"] == "INTERACT":

            assert (
                paso["action"]
                in interacciones_validas
            )


# ============================================================
# 5. COSTOS DIFERENTES
# ============================================================

def test_ucs_prefiere_menor_costo_y_no_menos_pasos() -> None:
    """
    Creamos un escenario mínimo:

        A -> B = 20

        A -> C = 5
        C -> B = 5

    Llegar directamente toma un movimiento,
    pero cuesta 20.

    Pasar por C toma dos movimientos,
    pero cuesta 10.

    UCS debe escoger costo 10.
    """

    scenario = {
        "meta": {
            "id": "test_costos",
            "title": "Test costos",
        },

        "robot": {
            "start": "A",
            "battery_max": 100,
            "battery_start": 100,
            "cargo_capacity": 3,
        },

        "zones": [
            {
                "id": "A",
                "name": "A",
                "recharge": False,
            },
            {
                "id": "B",
                "name": "B",
                "recharge": False,
            },
            {
                "id": "C",
                "name": "C",
                "recharge": False,
            },
        ],

        "corridors": [
            {
                "from": "A",
                "to": "B",
                "cost": 20,
                "door": None,
            },
            {
                "from": "A",
                "to": "C",
                "cost": 5,
                "door": None,
            },
            {
                "from": "C",
                "to": "B",
                "cost": 5,
                "door": None,
            },
        ],

        "doors": [],
        "keys": [],
        "tools": [],
        "materials": [],
        "panels": [],

        "stations": [
            {
                "id": "GOAL",
                "kind": "test",
                "zone": "B",
                "state": "OFFLINE",
                "requires": {},
            }
        ],

        "chargers": [],

        "goal": {
            "stations_online": [
                "GOAL"
            ]
        },

        "action_costs": {
            "pickup": 1,
            "drop": 1,
            "interact": 1,
            "recharge": 3,
        },
    }

    resultado = solve_scenario(
        scenario
    )

    assert resultado["solution_found"] is True

    # Ruta esperada:
    #
    # A -> C = 5
    # C -> B = 5
    # ACTIVATE = 1
    #
    # Total = 11
    assert resultado["total_cost"] == 11

    movimientos = [
        paso
        for paso in resultado["steps"]
        if paso["op"] == "MOVE"
    ]

    assert len(movimientos) == 2

    assert movimientos[0]["to"] == "C"
    assert movimientos[1]["to"] == "B"


# ============================================================
# 6. CASO SIN SOLUCIÓN
# ============================================================

def test_escenario_sin_solucion() -> None:
    """
    Quitamos MULTITOOL del escenario.

    PANEL_A necesita MULTITOOL.
    GENERATOR necesita PANEL_A.
    La meta necesita GENERATOR.

    Por lo tanto la misión debe quedar sin solución.
    """

    scenario = copy.deepcopy(
        load_scenario()
    )

    scenario["tools"] = [
        tool
        for tool in scenario["tools"]
        if tool["id"] != "MULTITOOL"
    ]

    resultado = solve_scenario(
        scenario
    )

    assert resultado["solution_found"] is False
    assert resultado["steps"] == []


# ============================================================
# 7. RUTAS ALTERNATIVAS
# ============================================================

def test_graph_search_elige_mejor_ruta() -> None:
    """
    Dos caminos llevan al mismo lugar.

        A -> B = 15

        A -> C = 3
        C -> B = 3

    Graph Search + UCS debe conservar la llegada barata.
    """

    scenario = {
        "meta": {
            "id": "test_rutas",
            "title": "Test rutas",
        },

        "robot": {
            "start": "A",
            "battery_max": 100,
            "battery_start": 100,
            "cargo_capacity": 3,
        },

        "zones": [
            {
                "id": "A",
                "name": "A",
                "recharge": False,
            },
            {
                "id": "B",
                "name": "B",
                "recharge": False,
            },
            {
                "id": "C",
                "name": "C",
                "recharge": False,
            },
        ],

        "corridors": [
            {
                "from": "A",
                "to": "B",
                "cost": 15,
                "door": None,
            },
            {
                "from": "A",
                "to": "C",
                "cost": 3,
                "door": None,
            },
            {
                "from": "C",
                "to": "B",
                "cost": 3,
                "door": None,
            },
        ],

        "doors": [],
        "keys": [],
        "tools": [],
        "materials": [],
        "panels": [],

        "stations": [
            {
                "id": "GOAL",
                "kind": "test",
                "zone": "B",
                "state": "OFFLINE",
                "requires": {},
            }
        ],

        "chargers": [],

        "goal": {
            "stations_online": [
                "GOAL"
            ]
        },

        "action_costs": {
            "pickup": 1,
            "drop": 1,
            "interact": 1,
            "recharge": 3,
        },
    }

    resultado = solve_scenario(
        scenario
    )

    assert resultado["solution_found"] is True

    # 3 + 3 + 1 de ACTIVATE
    assert resultado["total_cost"] == 7


# ============================================================
# EJECUCIÓN DIRECTA
# ============================================================

if __name__ == "__main__":

    print("Ejecutando pruebas del agente...\n")

    test_estados_equivalentes()
    print("[OK] Estados equivalentes")

    test_bateria_distingue_estados()
    print("[OK] Información relevante")

    test_plan_real_llega_a_meta()
    print("[OK] Plan real válido y meta alcanzada")

    test_plan_respeta_operaciones_permitidas()
    print("[OK] Contrato de operaciones")

    test_ucs_prefiere_menor_costo_y_no_menos_pasos()
    print("[OK] UCS minimiza costo")

    test_escenario_sin_solucion()
    print("[OK] Caso sin solución")

    test_graph_search_elige_mejor_ruta()
    print("[OK] Rutas alternativas")

    print("\nTODAS LAS PRUEBAS PASARON")