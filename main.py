import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime

import uvicorn
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI

import train_xgboost
from application.betplay.betplay_service import BetplayService
from application.football_data.football_data_service import FootballDataService
from infrastructure.logging_config import setup_logging
from infrastructure.persistence.leagues_config_repository import LeaguesConfigRepository
from infrastructure.persistence.postgres_config import PostgresConfig
from models.xgboost import predictor as xgboost_predictor

setup_logging()
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()
last_run: dict = {
    "betplay": {"time": None, "status": None},
    "nightly": {"time": None, "status": None},
}



def run_betplay():
    last_run["betplay"]["time"] = datetime.now().isoformat()
    logger.info("=== Iniciando job betplay ===")
    t0 = time.perf_counter()
    try:
        leagues = LeaguesConfigRepository().find_active()
        logger.info("Ligas activas: %d", len(leagues))
        for league in leagues:
            logger.info("Procesando liga: %s", league["name"])
            BetplayService(
                league_db=league['league_db'],
                betplay_path=league['betplay_path']
            ).save_league_odds()
            xgboost_predictor.run(league['league_db'], league.get('api_football_id'))
        elapsed = time.perf_counter() - t0
        last_run["betplay"]["status"] = "ok"
        logger.info("=== Job betplay completado en %.1fs ===", elapsed)
    except Exception as e:
        last_run["betplay"]["status"] = f"error: {e}"
        logger.error("Job betplay falló: %s", e, exc_info=True)


def run_nightly():
    """Sincroniza la temporada actual y reentrena el modelo XGBoost por liga."""
    last_run["nightly"]["time"] = datetime.now().isoformat()
    logger.info("=== Iniciando job nightly ===")
    t0 = time.perf_counter()
    try:
        leagues = LeaguesConfigRepository().find_active()
        for league in leagues:
            logger.info("Nightly — %s", league["name"])
            FootballDataService(db_name=league['league_db']).update_current_season()
            train_xgboost.run(league['league_db'])
        elapsed = time.perf_counter() - t0
        last_run["nightly"]["status"] = "ok"
        logger.info("=== Job nightly completado en %.1fs ===", elapsed)
    except Exception as e:
        last_run["nightly"]["status"] = f"error: {e}"
        logger.error("Job nightly falló: %s", e, exc_info=True)



@asynccontextmanager
async def lifespan(app: FastAPI):
    PostgresConfig.init_schema()
    leagues = LeaguesConfigRepository().find_active()
    logger.info("Ligas configuradas: %d", len(leagues))
    for lg in leagues:
        logger.info("  · %s  (db=%s)", lg["name"], lg["league_db"])

    logger.info("Arrancando scheduler...")
    scheduler.add_job(run_betplay, 'interval', minutes=10, id='betplay')
    scheduler.add_job(run_nightly, 'cron', hour=0, minute=0, id='nightly')
    scheduler.start()
    logger.info("Scheduler activo — jobs: %s", [j.id for j in scheduler.get_jobs()])
    yield
    scheduler.shutdown()
    logger.info("Scheduler detenido")


app = FastAPI(title="Apuestas Deportivas API", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/status")
def status():
    jobs = [
        {"id": j.id, "next_run": str(j.next_run_time)}
        for j in scheduler.get_jobs()
    ]
    return {"jobs": jobs, "last_run": last_run}


@app.post("/run/betplay")
def trigger_betplay():
    run_betplay()
    return last_run["betplay"]


@app.post("/run/nightly")
def trigger_nightly():
    run_nightly()
    return last_run["nightly"]


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
