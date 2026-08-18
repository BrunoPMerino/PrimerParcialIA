from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent import solve_scenario


app = FastAPI(
    title="Emergency Control API",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


SCENARIO_PATH = (
    Path(__file__).resolve().parents[2]
    / "scenarios"
    / "scenario.json"
)


def cargar_escenario() -> dict[str, Any]:
    """
    Carga el escenario por defecto desde scenario.json.
    """

    with SCENARIO_PATH.open(
        encoding="utf-8"
    ) as archivo:
        return json.load(archivo)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {
        "status": "ok"
    }


@app.get("/api/scenario")
def get_scenario() -> dict[str, Any]:
    return cargar_escenario()


@app.post("/api/solve")
def solve(
    scenario: dict[str, Any],
) -> dict[str, Any]:

    data = (
        scenario
        if scenario
        else cargar_escenario()
    )

    return solve_scenario(
        data
    )