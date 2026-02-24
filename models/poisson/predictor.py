from models.poisson.data_loader import load_home_away, load_matches
from models.poisson.model import FootballPoisson

VALUE_THRESHOLD = 0.05  # diferencia mínima para considerar value bet


def implied_prob(odd: float) -> float:
    return round(1 / odd, 4) if odd and odd > 0 else None


def detect_value(model_prob: float, odd: float) -> bool:
    if not odd or odd <= 0:
        return False
    return model_prob - implied_prob(odd) >= VALUE_THRESHOLD


def run(db_name: str):
    df_home_away = load_home_away(db_name)
    df_matches = load_matches(db_name)

    model = FootballPoisson()
    model.fit(df_home_away)

    print(f"\n{'='*65}")
    print(f"  PREDICCIONES POISSON — {db_name.upper().replace('_', ' ')}")
    print(f"{'='*65}")

    for _, match in df_matches.iterrows():
        home = match["home_team"]
        away = match["away_team"]

        try:
            pred = model.predict(home, away)
        except ValueError as e:
            print(f"\n⚠️  {e}")
            continue

        odd_1 = match.get("Resultado Final 1")
        odd_x = match.get("Resultado Final X")
        odd_2 = match.get("Resultado Final 2")
        odd_over = match.get("Total de goles Mas de 2.5")
        odd_btts = match.get("Ambos Equipos Marcarán Sí")

        print(f"\n⚽ {match['partido']}")
        print(f"   xG: {home} {pred['xg_home']} — {pred['xg_away']} {away}")
        print(f"   {'Resultado':30s}  {'Modelo':>7}  {'Cuota':>6}  {'Impl%':>6}  {'Value':>5}")
        print(f"   {'-'*57}")

        rows = [
            ("1 (Local)",  pred["home_win"], odd_1),
            ("X (Empate)", pred["draw"],     odd_x),
            ("2 (Visitante)", pred["away_win"], odd_2),
            ("Over 2.5",   pred["over_25"],  odd_over),
            ("BTTS Sí",    pred["btts_yes"], odd_btts),
        ]

        for label, prob, odd in rows:
            impl = implied_prob(odd) if odd else None
            value = "✅" if detect_value(prob, odd) else ""
            odd_str = f"{odd:.2f}" if odd else "  N/A"
            impl_str = f"{impl*100:.1f}%" if impl else "  N/A"
            print(f"   {label:30s}  {prob*100:>6.1f}%  {odd_str:>6}  {impl_str:>6}  {value}")
