from __future__ import annotations

from dataclasses import dataclass


@dataclass(
    frozen=True,
    slots=True,
)
class Estado:
    """
    Estado físico del mundo.
    """

    zona: str
    bateria: int

    # (item, cantidad)
    carga: tuple[
        tuple[str, int],
        ...
    ]

    # (zona, item, cantidad)
    suelo: tuple[
        tuple[str, str, int],
        ...
    ]

    puertas_abiertas: frozenset[str]

    paneles_reparados: frozenset[str]

    estaciones_online: frozenset[str]

    def __post_init__(
        self,
    ):
        """
        Garantiza representación canónica.
        """

        canonical_load = tuple(
            sorted(
                (
                    item,
                    quantity,
                )
                for item, quantity
                in self.carga
                if quantity > 0
            )
        )

        canonical_floor = tuple(
            sorted(
                (
                    zone,
                    item,
                    quantity,
                )
                for zone, item, quantity
                in self.suelo
                if quantity > 0
            )
        )

        object.__setattr__(
            self,
            "carga",
            canonical_load,
        )

        object.__setattr__(
            self,
            "suelo",
            canonical_floor,
        )

        object.__setattr__(
            self,
            "puertas_abiertas",
            frozenset(
                self.puertas_abiertas
            ),
        )

        object.__setattr__(
            self,
            "paneles_reparados",
            frozenset(
                self.paneles_reparados
            ),
        )

        object.__setattr__(
            self,
            "estaciones_online",
            frozenset(
                self.estaciones_online
            ),
        )

    def clave_sin_bateria(
        self,
    ):
        """
        Configuración utilizada para dominancia.
        """

        return (
            self.zona,
            self.carga,
            self.suelo,
            self.puertas_abiertas,
            self.paneles_reparados,
            self.estaciones_online,
        )