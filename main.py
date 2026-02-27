from contextlib import asynccontextmanager
from datetime import datetime

import uvicorn
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI

from application.betplay.betplay_service import BetplayService
from application.fbref.fbref_service import FbrefService
from infrastructure.persistence.leagues_config_repository import LeaguesConfigRepository
from models.xgboost import predictor as xgboost_predictor

scheduler = BackgroundScheduler()
last_run: dict = {
    "betplay": {"time": None, "status": None},
}


def run_betplay():
    last_run["betplay"]["time"] = datetime.now().isoformat()
    try:
        leagues = LeaguesConfigRepository().find_active()
        for league in leagues:
            print(f"\n🏆 Liga: {league['name']}")
            BetplayService(
                league_db=league['league_db'],
                betplay_path=league['betplay_path']
            ).save_league_odds()
            xgboost_predictor.run(league['league_db'], league.get('api_football_id'))
        last_run["betplay"]["status"] = "ok"
    except Exception as e:
        last_run["betplay"]["status"] = f"error: {e}"
        print(f"❌ Error en betplay/predictor: {e}")


def run_fbref():
    last_run["fbref"]["time"] = datetime.now().isoformat()
    try:
        leagues = LeaguesConfigRepository().find_active()
        for league in leagues:
            print(f"\n🏆 FBRef — {league['name']}")
            fbref = FbrefService(
                league_slug=league['league_slug'],
                db_name=league['league_db']
            )
            fbref.get_data_frame()
            fbref.get_passing_data()
        last_run["fbref"]["status"] = "ok"
    except Exception as e:
        last_run["fbref"]["status"] = f"error: {e}"
        print(f"❌ Error en fbref: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(run_betplay, 'interval', minutes=10, id='betplay')
    scheduler.start()
    yield
    scheduler.shutdown()


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



if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=False)
