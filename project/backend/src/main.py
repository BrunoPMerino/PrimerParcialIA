from pathlib import Path
import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent import solve_scenario


app = FastAPI()


# Permite que el frontend se comunique con el backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Ruta al archivo del escenario.
BASE_DIR = Path(__file__).resolve().parent
SCENARIO_PATH = BASE_DIR.parent.parent / "scenarios" / "scenario.json"


def cargar_escenario():
    """
    Carga el escenario desde scenario.json.

    El agente no tiene valores del escenario escritos directamente
    en el código. Toda la información se toma del archivo JSON.
    """
    with open(
        SCENARIO_PATH,
        "r",
        encoding="utf-8",
    ) as archivo:
        return json.load(archivo)


@app.get("/api/health")
def health():
    """
    Endpoint sencillo para comprobar que el backend está funcionando.
    """
    return {
        "status": "ok"
    }


@app.post("/api/solve")
def solve(scenario: dict[str, Any]) -> dict[str, Any]:
    data = scenario if scenario else _load_default_scenario()

    resultado = solve_scenario(data)

    return resultado