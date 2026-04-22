VALUE_THRESHOLD = 0.05  # diferencia mínima para considerar value bet


def implied_prob(odd: float) -> float | None:
    """Probabilidad implícita de la cuota (sin eliminar margen)."""
    return round(1 / odd, 4) if odd and odd > 0 else None


def devig(odd_h: float, odd_d: float, odd_a: float) -> tuple[float | None, float | None, float | None]:
    """
    Elimina el margen (overround) de la casa de apuestas usando el método multiplicativo.
    Divide cada probabilidad implícita por la suma total para obtener la probabilidad
    justa (fair odds), sin el margen incluido.
    """
    raw = [1 / o if o and o > 0 else None for o in (odd_h, odd_d, odd_a)]
    if any(r is None for r in raw):
        return None, None, None
    total = sum(raw)
    return tuple(round(r / total, 4) for r in raw)


def detect_value(model_prob: float, odd: float) -> bool:
    """Retorna True si la probabilidad del modelo supera la implícita en al menos VALUE_THRESHOLD."""
    impl = implied_prob(odd)
    return impl is not None and model_prob - impl >= VALUE_THRESHOLD
