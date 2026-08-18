# Diseño del agente

Este documento debe completarse **antes** de la implementación principal del agente.

Use sus propias palabras y notación. No reemplace este archivo por una transcripción
del enunciado. Las subsecciones existen para que no se le olvide una decisión;
usted decide el contenido.

El entorno, según las propiedades vistas en clase, es totalmente observable,
determinista, secuencial, estático, discreto y de agente único. Bajo esas
condiciones la solución es un **plan completo** y el marco correcto es la
búsqueda clásica. Justifique cada componente con ese marco (AIMA, cap. 3).

---

## Estado

### Definición formal

El estado se puede representar con la siguiente tupla:

```text
s = ⟨z, b, C, L, D, P, E⟩
```

Donde:

- `z`: zona actual del robot
- `b`: batería disponible
- `C`: carga actual del robot
- `L`: ubicación de los objetos relevantes que están en el suelo
- `D`: conjunto de puertas que ya fueron abiertas
- `P`: conjunto de paneles que ya fueron reparados
- `E`: conjunto de estaciones que se encuentran ONLINE

### Por qué cada variable es necesaria

La zona `z` es necesaria porque dependiendo de dónde esté el robot cambian los movimientos y las acciones que puede realizar.

La batería `b` también debe estar en el estado porque todas las acciones gastan batería. Dos robots en el mismo lugar y con los mismos objetos, pero con diferente batería, pueden tener diferentes acciones disponibles.

La carga `C` es necesaria porque algunas acciones requieren tener ciertos objetos. También se debe tener en cuenta la capacidad máxima que puede transportar el robot.

La ubicación de los objetos `L` debe estar en el estado porque los objetos pueden ser recogidos y también soltados. Por esto, después de comenzar el problema no podemos saber su ubicación mirando solamente el escenario inicial.

Las puertas abiertas `D` son importantes porque cuando una puerta se abre queda abierta permanentemente y esto cambia los caminos que puede usar el robot.

Los paneles reparados `P` se necesitan porque un panel reparado cambia el entorno y puede permitir que después se active una estación.

Las estaciones ONLINE `E` forman parte del estado porque algunas estaciones dependen de otras y también porque la meta del problema se comprueba usando las estaciones que están activas.

En general, estas variables forman parte del estado porque si alguna cambia, también pueden cambiar las acciones que el robot puede realizar después.

### Qué información se deriva y NO se almacena

No es necesario guardar información que se pueda calcular usando el estado y los datos del escenario.

Por ejemplo, el peso actual de la carga se puede calcular sumando el peso de los objetos que están en `C`, por lo que no hace falta guardarlo como otra variable.

Tampoco se guardan como parte del estado:

- el grafo de corredores;
- los costos de las acciones;
- la capacidad máxima de carga;
- la batería máxima;
- la ubicación inicial de los paneles;
- los requisitos de reparación;
- las dependencias de las estaciones.

Toda esta información es fija y viene definida por el escenario.

Las acciones posibles tampoco se guardan porque se pueden calcular en cada momento usando `Applicable(s)`.

### Qué pertenece al historial de búsqueda y no al estado físico

El costo acumulado `g(n)`, el nodo padre, la acción que llevó hasta el nodo y la profundidad no forman parte del estado físico.

Esta información pertenece al nodo de búsqueda porque explica cómo se llegó hasta una situación.

Dos caminos diferentes pueden terminar exactamente en el mismo estado del mundo. Si guardáramos el camino dentro del estado, Graph Search pensaría que son situaciones diferentes y no podría detectar correctamente los estados repetidos.

Por eso el estado guarda cómo está el mundo actualmente, mientras que el nodo guarda cómo se llegó hasta allí.

### Cuándo dos configuraciones son el mismo estado

Dos configuraciones son el mismo estado cuando tienen:

- la misma zona;
- la misma batería;
- la misma carga;
- la misma distribución de los objetos relevantes;
- las mismas puertas abiertas;
- los mismos paneles reparados;
- las mismas estaciones ONLINE.

En este caso el orden de los objetos en la carga no importa y dos materiales iguales se tomarán como dos unidades del mismo tipo


### Relevancia: objetos que ya no cambian el futuro

Un objeto deja de ser relevante cuando ya no puede ayudar a realizar ninguna acción necesaria para cumplir la misión.

Por ejemplo, una llave deja de ser relevante después de abrir la puerta correspondiente, ya que esta no vuelve a cerrarse.

Si en este caso la llave está en el suelo ya no es necesario tomarla en cuenta ya que de usarla ya no se llegaría a la respuesta más optima, en cambio si se encuentra dentro de la carga del robot debe ser soltada para luego ser ignorada


---

## Acciones

Las acciones internas del agente serán las siguientes:

| Acción | Precondiciones | Efectos | Costo |
|---|---|---|---|
| `MOVE(z')` | Existe un corredor hacia `z'`. Si hay una puerta, debe estar abierta. El robot debe tener batería suficiente. | El robot cambia de zona y disminuye su batería. | Costo del corredor. |
| `PICKUP(o)` | El objeto está en la zona actual, todavía es relevante, cabe dentro de la capacidad y hay batería suficiente. | El objeto pasa del suelo a la carga y disminuye la batería. | `action_costs.pickup` |
| `DROP(o)` | El objeto está en la carga, soltarlo es relevante para liberar capacidad y hay batería suficiente. | El objeto sale de la carga y queda en la zona actual. También disminuye la batería. | `action_costs.drop` |
| `OPEN_DOOR(d)` | El robot está junto a la puerta, la puerta está cerrada, tiene la llave necesaria y batería suficiente. | La puerta queda abierta permanentemente. | Costo de interacción del escenario. |
| `REPAIR(p)` | El robot está en la zona del panel, el panel no está reparado y tiene la herramienta y el material necesarios. También necesita batería suficiente. | El panel queda reparado. El material se consume y la herramienta permanece. | Costo de interacción del escenario. |
| `ACTIVATE(e)` | El robot está en la zona de la estación, la estación está OFFLINE, se cumplen sus dependencias y hay batería suficiente. | La estación pasa a ONLINE. | Costo de interacción del escenario. |
| `RECHARGE` | El robot está en una zona con cargador, la batería no está llena y puede pagar el costo de la acción. | Primero se paga el costo de la acción y después la batería vuelve hasta `battery_max`. | `action_costs.recharge` |

Como regla general, una acción solo puede generarse si el robot tiene batería suficiente para pagar su costo.

### `Applicable` interno vs legalidad del contrato

El simulador puede permitir acciones que físicamente son legales pero que no son útiles para encontrar una solución.

El caso más importante es `DROP` ya que de usarlo en cada sala se generarían demasiadas combinaciones que no serían óptimas además de no generar beneficio en caso de que se suelte salas antes de necesitar espacio por eso el robot puede esperar hasta llegar al lugar donde realmente hace falta recoger el nuevo objeto, evitando recoger objetos sin utilidad


---

## Modelo de transición

El modelo de transición se puede expresar como:

```text
Result(s, a) = s'     solo si a ∈ Applicable(s)
```

El entorno es determinista, así que aplicar una acción legal sobre un estado produce un único estado siguiente.

Todas las acciones consumen batería según su costo.

Además, dependiendo de la acción ocurren los siguientes cambios:

- `MOVE` cambia la zona del robot.
- `PICKUP` quita un objeto del suelo y lo agrega a la carga.
- `DROP` quita un objeto de la carga y lo deja en la zona actual.
- `OPEN_DOOR` agrega una puerta al conjunto de puertas abiertas.
- `REPAIR` agrega el panel al conjunto de paneles reparados y consume el material necesario. La herramienta no se consume.
- `ACTIVATE` agrega la estación al conjunto de estaciones ONLINE.
- `RECHARGE` restaura la batería hasta `battery_max` después de pagar el costo de la acción.

Las partes del estado que no son afectadas por una acción se mantienen iguales.

---

## Prueba de meta

La prueba de meta será:

```text
Goal(s) ⟺ goal.stations_online ⊆ E
```

Esto significa que el problema termina cuando todas las estaciones que el escenario pide en `goal.stations_online` están dentro del conjunto `E` de estaciones ONLINE.

La meta se comprueba mirando cómo quedó el mundo y no revisando las acciones que el robot tomó.

---

## Función de costo

El costo acumulado se representa como:

```text
g(n) = Σ c(ai)
```

`g(n)` es la suma de los costos de todas las acciones realizadas desde el estado inicial hasta el nodo actual.

Los costos siempre se toman directamente del escenario.

Los movimientos usan el costo del corredor y las demás acciones usan los costos definidos en `action_costs`.

Un plan con menos acciones puede ser mas costoso que uno mas complejo, por esto, la profundidad del nodo no representa qué tan buena es una solución. Lo importante es el costo acumulado `g(n)`.

---

## Estrategia de búsqueda

Se utilizará **Búsqueda de Costo Uniforme (Uniform Cost Search, UCS) con Graph Search**.

UCS es adecuada para este problema porque las acciones tienen costos diferentes y necesitamos encontrar el plan que tenga el menor costo total.

La frontera `OPEN` se manejará con una cola de prioridad ordenada por `g(n)`. De esta forma, siempre se expande primero el nodo que tenga el menor costo acumulado.

### Completitud

Como el espacio de estados es finito, se controla el número de sucesores y los costos son positivos, UCS puede encontrar una solución si existe.

### Optimalidad

UCS siempre extrae de `OPEN` el nodo que tenga el menor costo acumulado.

La prueba de meta debe hacerse cuando un nodo se extrae de la frontera y no cuando se genera.

Esto se hace porque un camino que ya llegó a la meta puede ser más costoso que otro camino que todavía no termina de explorarse.

### Costo de camino

La prioridad utilizada es:

```text
g(n)
```

que corresponde a la suma de todos los costos oficiales de las acciones usadas para llegar hasta ese nodo.

### Tiempo y espacio

UCS puede usar bastante memoria porque mantiene diferentes posibilidades dentro de `OPEN`.

El problema principal no es solamente cuántos caminos salen de cada zona. Acciones como `PICKUP` y especialmente `DROP` pueden producir muchas configuraciones diferentes del inventario y de los objetos que quedan en el mapa.

Por esto, `Applicable` debe evitar generar acciones que no aporten a una posible solución óptima.

### Graph Search y CLOSED

Se utilizará una estructura `CLOSED` para evitar volver a explorar situaciones que ya fueron procesadas.

Los estados utilizados en `CLOSED` deben estar representados de forma canónica.

Esto permite que dos caminos diferentes que llegan exactamente a la misma situación física sean reconocidos como el mismo estado.

Las garantías de la búsqueda pueden fallar si se usan estados mal representados, se generan demasiadas acciones innecesarias, existen costos negativos o se maneja incorrectamente `OPEN` y `CLOSED`.

### Batería como recurso

La batería sí forma parte del estado porque determina qué acciones puede realizar el robot.

Sin embargo, no todas las diferencias de batería tienen la misma utilidad.

Para comparar dos caminos se puede separar la configuración del mundo de la batería:

```text
w = ⟨zona, carga, suelo, puertas, paneles, estaciones⟩
```

Si dos nodos llegan a la misma configuración `w`, se pueden comparar usando su costo y su batería.

Un nodo `n1` domina a un nodo `n2` cuando:

```text
g(n1) <= g(n2)
bateria(n1) >= bateria(n2)
```

Esto quiere decir que `n1` llegó a la misma situación con un costo menor o igual y además tiene una batería mayor o igual.

En ese caso no tiene sentido seguir explorando `n2`, porque cualquier acción que pueda realizar desde `n2` también podría realizarse desde `n1`.

---

## Formulación y tamaño del espacio

### 1. ¿Por qué «5 zonas, ~10 objetos, capacidad 3» puede generar millones de nodos en un UCS ingenuo?

Porque un estado no depende solamente de la zona donde está el robot sino de cada una de las variables y posiciones de los objetos, haciendo que combinando las posibilidades de todas se pueda generar una gran cantidad de estados

### 2. ¿Qué papel tiene `DROP` en esa explosión?

`DROP` puede aumentar demasiado el espacio de búsqueda porque permite dejar los objetos en diferentes zonas ya que el agente puede repetir un ciclo en el que deja y recoge los objetos en cada sala, llegando a soluciones poco optimas.

Por eso, aunque `DROP` pueda ser una acción legal, el agente solamente lo genera cuando tiene una utilidad real para liberar capacidad.

### 3. ¿Qué podas o abstracciones se aplican y por qué no pierden el óptimo?

Se aplicarán las siguientes ideas:

- No generar `DROP` si no ayuda a liberar capacidad para recoger un objeto relevante.
- No recoger objetos que ya no tengan utilidad para cumplir la misión.
- Ignorar la ubicación exacta de objetos que ya no puedan afectar ninguna acción futura.
- Representar materiales equivalentes usando cantidades por tipo.
- Utilizar estados canónicos para que CLOSED reconozca configuraciones repetidas.
- Aplicar dominancia de batería para descartar caminos que llegan a la misma situación con mayor costo y menor batería.

Estas podas no eliminan una solución óptima porque solamente descartan estados o acciones que no pueden producir una ventaja futura frente a otra opción que ya tenemos.

### 4. ¿Por qué no es solución subir la capacidad, bajar las estaciones o ignorar la batería?

Porque eso cambiaría las reglas del problema y el agente debe poder resolver otros escenarios que mantengan el mismo contrato.

Cambiar artificialmente esto haría el escenario mas fácil pero no se estaría resolviendo el problema original
