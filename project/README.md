# Emergency Control - Primer Parcial IA

## Descripción

Este proyecto implementa un agente autónomo encargado de resolver una misión de mantenimiento en una instalación compuesta por varias zonas.

El robot debe desplazarse por el mapa, recoger llaves, herramientas y materiales, abrir puertas, reparar paneles, activar estaciones y administrar su batería y capacidad de carga.

El agente genera automáticamente un plan de acciones que lleva desde el estado inicial hasta un estado que satisface el objetivo de la misión.

La estrategia utilizada es **Uniform Cost Search (UCS)** con búsqueda en grafos y poda por dominancia.

---

## Estructura del proyecto

```text
project/
│
├── backend/
│   ├── src/
│   │   ├── main.py
│   │   ├── agent.py
│   │   ├── state.py
│   │   ├── problem.py
│   │   ├── scenario_model.py
│   │   ├── relevance.py
│   │   ├── transitions.py
│   │   └── simulator.py
│   │
│   ├── tests/
│   │   └── test_agent.py
│   │
│   └── requirements.txt
│
├── frontend/
│
├── scenarios/
│   └── scenario.json
│
├── design.md
└── README.md
```

---

## Diseño del agente

El problema se modela como un problema de búsqueda.

Un estado contiene:

- zona actual del robot;
- batería restante;
- carga transportada;
- objetos relevantes que permanecen en el suelo;
- puertas abiertas;
- paneles reparados;
- estaciones activadas.

La representación del estado se encuentra en:

```text
backend/src/state.py
```

La formulación completa y su justificación se encuentran en:

```text
design.md
```

---

## Estrategia de búsqueda

Se utiliza **Uniform Cost Search (UCS)**.

UCS expande siempre el nodo con menor costo acumulado:

```text
g(n)
```

donde `g(n)` corresponde a la suma de los costos de todas las acciones realizadas desde el estado inicial.

Esta estrategia fue seleccionada porque las acciones tienen costos diferentes. Por esta razón no sería correcto minimizar únicamente la cantidad de acciones.

---

## Optimizaciones de búsqueda

Para mantener el espacio de estados manejable se implementaron varias optimizaciones.

### Graph Search

Las configuraciones ya exploradas se registran para evitar expandir repetidamente el mismo mundo.

### Dominancia de batería

Si se alcanza la misma configuración física mediante dos caminos y uno tiene menor o igual costo y mayor o igual batería, la otra alternativa se descarta.

```text
g1 <= g2
b1 >= b2
```

### Estados canónicos

El orden interno de objetos equivalentes no crea estados diferentes.

### Objetos irrelevantes

Los objetos que ya no pueden modificar acciones futuras dejan de formar parte de la representación del suelo. Los objetos dentro de la carga sí se conservan porque continúan ocupando capacidad.

### Materiales equivalentes

Los materiales del mismo tipo se representan mediante cantidades y no mediante identificadores artificiales individuales.

### Relevancia desde la meta

Solo se consideran paneles, materiales, herramientas y estaciones que pueden contribuir directa o indirectamente al objetivo.

### DROP restringido

`DROP` solo se considera cuando es necesario liberar capacidad para recoger un objeto relevante. Los conjuntos mínimos de objetos a soltar se calculan como una única decisión interna y luego se traducen a operaciones visuales `DROP` y `PICKUP`.

---

## Requisitos

```text
Python 3.10 o superior
Node.js
npm
```

---

## Instalación

```bash
git clone https://github.com/BrunoPMerino/PrimerParcialIA.git
cd PrimerParcialIA
```

---

## Backend

```bash
cd project/backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --app-dir src --port 8000
```

Comprobación:

```text
http://127.0.0.1:8000/api/health
```

Respuesta esperada:

```json
{
  "status": "ok"
}
```

---

## Frontend

En una segunda terminal:

```bash
cd project/frontend
npm install
npm run dev
```

Abrir normalmente:

```text
http://localhost:5173
```

---

## Ejecutar una misión

1. Iniciar backend y frontend.
2. Abrir la aplicación.
3. Presionar el botón para ejecutar el plan.
4. El frontend envía el escenario a `POST /api/solve`.
5. El backend ejecuta UCS.
6. Cuando encuentra la solución, retorna el plan.
7. El frontend ejecuta visualmente las acciones.

El escenario está en:

```text
project/scenarios/scenario.json
```

---

## Formato de respuesta

Ejemplo:

```json
{
  "solution_found": true,
  "total_cost": 100,
  "steps": [
    {
      "op": "MOVE",
      "from": "Z1",
      "to": "Z2",
      "cost": 4
    }
  ]
}
```

Operaciones permitidas:

```text
MOVE
PICKUP
DROP
INTERACT
```

Interacciones:

```text
OPEN_DOOR
REPAIR
ACTIVATE
RECHARGE
```

---

## Interpretación del resultado

### `solution_found`

Indica si fue posible encontrar un plan válido.

### `total_cost`

Representa el costo acumulado del plan completo. UCS busca minimizar este valor.

### `steps`

Contiene las acciones que debe ejecutar el robot en orden.

---

## Caso sin solución

```json
{
  "solution_found": false,
  "total_cost": 0,
  "steps": []
}
```

---

## Pruebas

Las pruebas están en:

```text
backend/tests/test_agent.py
```

Ejecutar:

```bash
cd project/backend
.venv\Scripts\activate
python tests/test_agent.py
```

También se pueden ejecutar con:

```bash
pytest tests/test_agent.py -v
```

---

## Casos de validación

Las pruebas comprueban:

1. Estados equivalentes.
2. Información relevante.
3. Costos diferentes.
4. Caso sin solución.
5. Rutas alternativas.
6. Ejecución válida del plan mediante `simulator.py`.
7. Cumplimiento del contrato de operaciones del frontend.

Resultado esperado:

```text
[OK] Estados equivalentes
[OK] Información relevante
[OK] Plan real válido y meta alcanzada
[OK] Contrato de operaciones
[OK] UCS minimiza costo
[OK] Caso sin solución
[OK] Rutas alternativas

TODAS LAS PRUEBAS PASARON
```

Con pytest:

```text
7 passed
```

---

## Integración visual

La interfaz permite observar:

- posición del robot;
- nivel de batería;
- acciones realizadas;
- progreso de la misión;
- costo acumulado;
- resultado final.

La lógica de decisión pertenece al agente implementado en el backend.

---

## Separación entre agente y frontend

El modelo interno puede utilizar acciones más abstractas para reducir el espacio de búsqueda.

Por ejemplo, liberar capacidad y recoger un objeto puede representarse internamente como una sola transición, pero antes de enviarla al frontend se traduce a operaciones permitidas:

```text
DROP
DROP
PICKUP
```

---

## Autor

Bruno Pérez

Primer Parcial - Fundamentos de Inteligencia Artificial

Universidad de La Sabana

Semestre 2026-2
