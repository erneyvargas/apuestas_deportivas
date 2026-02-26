from models.poisson.data_loader import (
    load_home_away,
    load_home_away_historical,
    load_matches,
    load_corners_stats,
    load_corners_stats_historical,
)
from models.poisson.model import FootballPoisson
from models.poisson.corners_model import CornersPoisson

VALUE_THRESHOLD = 0.05  # diferencia mínima para considerar value bet


def implied_prob(odd: float) -> float:
    return round(1 / odd, 4) if odd and odd > 0 else None


def devig(odd_h: float, odd_d: float, odd_a: float) -> tuple[float | None, float | None, float | None]:
    """
    Elimina el margen (overround) de la casa de apuestas usando el método multiplicativo.
    Divide cada probabilidad implícita por la suma total para obtener la probabilidad
    'justa' (fair odds), sin el margen incluido.

    Ejemplo: si las cuotas suman un overround de 3.6%,
    normaliza cada una para que el total sea 100%.
    """
    raw = [1 / o if o and o > 0 else None for o in (odd_h, odd_d, odd_a)]
    if any(r is None for r in raw):
        return None, None, None
    total = sum(raw)
    return tuple(round(r / total, 4) for r in raw)


def detect_value(model_prob: float, odd: float) -> bool:
    impl = implied_prob(odd)
    return impl is not None and model_prob - impl >= VALUE_THRESHOLD


def _print_rows(rows):
    for label, prob, odd in rows:
        impl = implied_prob(odd) if odd else None
        value = "✅" if detect_value(prob, odd) else ""
        odd_str = f"{odd:.2f}" if odd else "  N/A"
        impl_str = f"{impl*100:.1f}%" if impl else "  N/A"
        print(f"   {label:30s}  {prob*100:>6.1f}%  {odd_str:>6}  {impl_str:>6}  {value}")


def run(db_name: str):
    try:
        df_home_away = load_home_away_historical(db_name)
        print("📊 Modelo de goles: datos históricos (10 temporadas)")
    except RuntimeError:
        df_home_away = load_home_away(db_name)
        print("📊 Modelo de goles: temporada actual (FBRef)")

    df_matches = load_matches(db_name)

    goals_model = FootballPoisson()
    goals_model.fit(df_home_away)

    corners_model = None
    try:
        df_corners = load_corners_stats_historical(db_name)
        corners_model = CornersPoisson()
        corners_model.fit(df_corners)
        print("📊 Modelo de corners: datos históricos reales (HC/AC)")
    except RuntimeError:
        try:
            df_corners = load_corners_stats(db_name)
            corners_model = CornersPoisson()
            corners_model.fit(df_corners)
            print("📊 Modelo de corners: proxy de crosses (FBRef)")
        except RuntimeError as e:
            print(f"\n⚠️  Corners model no disponible: {e}")

    print(f"\n{'='*65}")
    print(f"  PREDICCIONES POISSON — {db_name.upper().replace('_', ' ')}")
    print(f"{'='*65}")

    for _, match in df_matches.iterrows():
        home = match["home_team"]
        away = match["away_team"]

        try:
            pred = goals_model.predict(home, away)
        except ValueError as e:
            print(f"\n⚠️  {e}")
            continue

        odd_1    = match.get("Resultado Final 1")
        odd_x    = match.get("Resultado Final X")
        odd_2    = match.get("Resultado Final 2")
        odd_over = match.get("Total de goles Mas de 2.5")
        odd_btts = match.get("Ambos Equipos Marcarán Sí")

        print(f"\n⚽ {match['partido']}")
        print(f"   xG: {home} {pred['xg_home']} — {pred['xg_away']} {away}")
        print(f"   {'Resultado':30s}  {'Modelo':>7}  {'Cuota':>6}  {'Impl%':>6}  {'Value':>5}")
        print(f"   {'-'*57}")

        _print_rows([
            ("1 (Local)",     pred["home_win"], odd_1),
            ("X (Empate)",    pred["draw"],     odd_x),
            ("2 (Visitante)", pred["away_win"], odd_2),
            ("Over 2.5",      pred["over_25"],  odd_over),
            ("BTTS Si",       pred["btts_yes"], odd_btts),
        ])

        if corners_model:
            try:
                cp = corners_model.predict(home, away)
            except ValueError as e:
                print(f"   ⚠️  {e}")
                continue

            odd_o95  = match.get("Total de Tiros de Esquina Mas de 9.5")
            odd_u95  = match.get("Total de Tiros de Esquina Menos de 9.5")
            odd_o105 = match.get("Total de Tiros de Esquina Mas de 10.5")
            odd_u105 = match.get("Total de Tiros de Esquina Menos de 10.5")
            odd_o115 = match.get("Total de Tiros de Esquina Mas de 11.5")
            odd_u115 = match.get("Total de Tiros de Esquina Menos de 11.5")

            print(f"\n   Corners — xC: {home} {cp['xc_home']} + {cp['xc_away']} {away} = {cp['xc_total']} total")
            print(f"   {'Mercado':30s}  {'Modelo':>7}  {'Cuota':>6}  {'Impl%':>6}  {'Value':>5}")
            print(f"   {'-'*57}")

            _print_rows([
                ("Over 9.5",  cp["over_95"],  odd_o95),
                ("Under 9.5", cp["under_95"], odd_u95),
                ("Over 10.5", cp["over_105"], odd_o105),
                ("Under 10.5",cp["under_105"],odd_u105),
                ("Over 11.5", cp["over_115"], odd_o115),
                ("Under 11.5",cp["under_115"],odd_u115),
            ])
