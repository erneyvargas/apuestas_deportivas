import logging
from contextlib import asynccontextmanager

import uvicorn
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI

from application.scheduler import create_scheduler, last_run, run_betplay, run_nightly
from infrastructure.logging_config import setup_logging
from infrastructure.persistence.leagues_config_repository import LeaguesConfigRepository
from infrastructure.persistence.postgres_config import PostgresConfig

setup_logging()
logger = logging.getLogger(__name__)

scheduler: BackgroundScheduler | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global scheduler
    PostgresConfig.init_schema()
    leagues = LeaguesConfigRepository().find_active()
    logger.info("Ligas configuradas: %d", len(leagues))
    for lg in leagues:
        logger.info("  · %s  (db=%s)", lg["name"], lg["league_db"])

    scheduler = create_scheduler()
    logger.info("Arrancando scheduler...")
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
    ] if scheduler else []
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
