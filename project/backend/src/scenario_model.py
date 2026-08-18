from __future__ import annotations

from typing import Any


class ScenarioModel:
    """
    Preprocesa el escenario para evitar recorrer el JSON
    completo cada vez que UCS expande un estado.
    """

    def __init__(self, scenario: dict[str, Any]):
        self.raw = scenario

        # -----------------------------------------------------
        # Robot y costos
        # -----------------------------------------------------

        self.robot = scenario["robot"]
        self.costs = scenario["action_costs"]

        self.start = self.robot["start"]
        self.battery_start = self.robot["battery_start"]
        self.battery_max = self.robot["battery_max"]
        self.capacity = self.robot["cargo_capacity"]

        # -----------------------------------------------------
        # Elementos del escenario
        # -----------------------------------------------------

        self.zones = scenario.get("zones", [])
        self.corridors = scenario.get("corridors", [])
        self.doors = scenario.get("doors", [])
        self.keys = scenario.get("keys", [])
        self.tools = scenario.get("tools", [])
        self.materials = scenario.get("materials", [])
        self.panels = scenario.get("panels", [])
        self.stations = scenario.get("stations", [])
        self.chargers = scenario.get("chargers", [])

        self.goal_stations = frozenset(
            scenario["goal"]["stations_online"]
        )

        # -----------------------------------------------------
        # Índices básicos
        # -----------------------------------------------------

        self.weights: dict[str, int] = {}

        self.key_ids = frozenset(
            key["id"]
            for key in self.keys
        )

        self.tool_ids = frozenset(
            tool["id"]
            for tool in self.tools
        )

        self.material_types = frozenset(
            material["type"]
            for material in self.materials
        )

        for key in self.keys:
            self.weights[key["id"]] = key["weight"]

        for tool in self.tools:
            self.weights[tool["id"]] = tool["weight"]

        for material in self.materials:
            self.weights[material["type"]] = material["weight"]

        # -----------------------------------------------------
        # Puertas
        # -----------------------------------------------------

        self.doors_by_id = {
            door["id"]: door
            for door in self.doors
        }

        self.doors_by_key: dict[str, list[dict[str, Any]]] = {}

        for door in self.doors:
            self.doors_by_key.setdefault(
                door["key"],
                [],
            ).append(door)

        # -----------------------------------------------------
        # Paneles
        # -----------------------------------------------------

        self.panels_by_id = {
            panel["id"]: panel
            for panel in self.panels
        }

        # Herramienta -> paneles
        self.panels_by_tool: dict[str, set[str]] = {}

        # Material -> paneles
        self.panels_by_material: dict[str, set[str]] = {}

        for panel in self.panels:
            tool = panel["requires"]["tool"]
            material = panel["requires"]["material"]

            self.panels_by_tool.setdefault(
                tool,
                set(),
            ).add(panel["id"])

            self.panels_by_material.setdefault(
                material,
                set(),
            ).add(panel["id"])

        # -----------------------------------------------------
        # Estaciones
        # -----------------------------------------------------

        self.stations_by_id = {
            station["id"]: station
            for station in self.stations
        }

        (
            self.required_stations,
            self.required_panels,
        ) = self._calculate_required_goals()

        # -----------------------------------------------------
        # Corredores
        #
        # IMPORTANTE:
        # scenario.json YA contiene ambos sentidos.
        #
        # No convertimos nuevamente cada corredor en bidireccional.
        # -----------------------------------------------------

        self.corridors_from: dict[
            str,
            list[dict[str, Any]]
        ] = {}

        for corridor in self.corridors:
            self.corridors_from.setdefault(
                corridor["from"],
                [],
            ).append(corridor)

        # -----------------------------------------------------
        # Elementos por zona
        # -----------------------------------------------------

        self.chargers_by_zone: dict[
            str,
            list[dict[str, Any]]
        ] = {}

        for charger in self.chargers:
            self.chargers_by_zone.setdefault(
                charger["zone"],
                [],
            ).append(charger)

        self.panels_by_zone: dict[
            str,
            list[dict[str, Any]]
        ] = {}

        for panel in self.panels:
            self.panels_by_zone.setdefault(
                panel["zone"],
                [],
            ).append(panel)

        self.stations_by_zone: dict[
            str,
            list[dict[str, Any]]
        ] = {}

        for station in self.stations:
            self.stations_by_zone.setdefault(
                station["zone"],
                [],
            ).append(station)

        self.doors_by_zone: dict[
            str,
            list[dict[str, Any]]
        ] = {}

        for door in self.doors:
            for zone in door["between"]:
                self.doors_by_zone.setdefault(
                    zone,
                    [],
                ).append(door)

    def _calculate_required_goals(
        self,
    ) -> tuple[frozenset[str], frozenset[str]]:
        """
        Sigue las dependencias desde goal hacia atrás.

        Así evitamos reparar paneles o activar estaciones
        que nunca contribuyen a la misión.
        """

        required_stations = set(
            self.goal_stations
        )

        required_panels = set()

        pending = list(
            required_stations
        )

        while pending:
            station_id = pending.pop()

            station = self.stations_by_id.get(
                station_id
            )

            if station is None:
                continue

            requires = station.get(
                "requires",
                {},
            )

            required_panels.update(
                requires.get(
                    "panels_ok",
                    [],
                )
            )

            for dependency in requires.get(
                "stations_online",
                [],
            ):
                if dependency not in required_stations:
                    required_stations.add(
                        dependency
                    )

                    pending.append(
                        dependency
                    )

        return (
            frozenset(required_stations),
            frozenset(required_panels),
        )