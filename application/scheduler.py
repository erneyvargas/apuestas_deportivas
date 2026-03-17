import logging
import time
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

import train_xgboost
from application.betplay.betplay_service import BetplayService
from application.football_data.football_data_service import FootballDataService
from infrastructure.persistence.leagues_config_repository import LeaguesConfigRepository
from models.xgboost import predictor as xgboost_predictor

logger = logging.getLogger(__name__)

last_run: dict = {
    "betplay": {"time": None, "status": None},
    "nightly": {"time": None, "status": None},
}


def run_betplay() -> None:
    last_run["betplay"]["time"] = datetime.now().isoformat()
    logger.info("=== Iniciando job betplay ===")
    t0 = time.perf_counter()
    try:
        leagues = LeaguesConfigRepository().find_active()
        logger.info("Ligas activas: %d", len(leagues))
        for league in leagues:
            logger.info("Procesando liga: %s", league["name"])
            BetplayService(
                league_db=league["league_db"],
                betplay_path=league["betplay_path"],
            ).save_league_odds()
            xgboost_predictor.run(league["league_db"])
        last_run["betplay"]["status"] = "ok"
        logger.info("=== Job betplay completado en %.1fs ===", time.perf_counter() - t0)
    except Exception as e:
        last_run["betplay"]["status"] = f"error: {e}"
        logger.error("Job betplay falló: %s", e, exc_info=True)


def run_nightly() -> None:
    """Sincroniza la temporada actual y reentrena el modelo XGBoost por liga."""
    last_run["nightly"]["time"] = datetime.now().isoformat()
    logger.info("=== Iniciando job nightly ===")
    t0 = time.perf_counter()
    try:
        leagues = LeaguesConfigRepository().find_active()
        for league in leagues:
            logger.info("Nightly — %s", league["name"])
            FootballDataService(db_name=league["league_db"]).update_current_season()
            train_xgboost.run(league["league_db"])
        last_run["nightly"]["status"] = "ok"
        logger.info("=== Job nightly completado en %.1fs ===", time.perf_counter() - t0)
    except Exception as e:
        last_run["nightly"]["status"] = f"error: {e}"
        logger.error("Job nightly falló: %s", e, exc_info=True)


def create_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_betplay,
        "interval",
        minutes=10,
        id="betplay",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=30,
    )
    scheduler.add_job(
        run_nightly,
        "cron",
        hour=0,
        minute=0,
        id="nightly",
        max_instances=1,
        coalesce=True,
    )
    return scheduler
