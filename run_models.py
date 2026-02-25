from models.xgboost.predictor import run as run_xgb
from models.poisson.predictor import run as run_poisson

if __name__ == "__main__":
    run_xgb(db_name="premier_league")      # 1X2 principal
    run_poisson(db_name="premier_league")  # Over/Under, BTTS, Corners
