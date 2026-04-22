import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import pandas as pd
import requests
from unidecode import unidecode

from apuestas.infrastructure.betplay.config import Config

logger = logging.getLogger(__name__)


class BetplayAPIClient:

    @staticmethod
    def fetch_leagues():
        url = Config.API_URL + "/group/highlight.json"
        logger.debug("GET %s", url)
        try:
            response = requests.get(
                url,
                params=Config.DEFAULT_PARAMS,
                headers=Config.HEADERS,
                timeout=10
            )
            response.raise_for_status()
            groups = response.json().get('groups', [])
            logger.info("Ligas obtenidas: %d", len(groups))
            return groups

        except requests.exceptions.RequestException as e:
            logger.error("Error fetching leagues: %s", e)
            return None

    def get_full_data(self, path):
        df_partidos = self.get_datos_partidos(path)
        return df_partidos

    def get_datos_partidos(self, path):
        url = (Config.API_URL + "/listView" + path
               + ".json?lang=es_ES&market=CO&client_id=2&channel_id=1&ncid=1641434042006&useCombined=true")
        logger.debug("GET partidos base — path: %s", path)

        response = requests.get(url, headers=Config.HEADERS)
        data_api_partido = response.json()
        partidos = data_api_partido["events"]
        logger.debug("Eventos base recibidos: %d", len(partidos))

        lista_partidos = []
        now = datetime.now()
        for partido in partidos:
            event = partido["event"]
            bet_offers = partido["betOffers"]
            dicc_partido = {
                "id": event["id"],
                "fecha_registro": now.strftime("%Y-%m-%d %H:%M:%S"),
                "fecha_evento": event["start"],
                "liga": event["group"],
                "partido": event["name"]
            }
            dicc_offers = self.get_offers_event(bet_offers)
            dicc_partido.update(dicc_offers)
            lista_partidos.append(dicc_partido)

        df_partidos = pd.DataFrame(lista_partidos)

        category_ids = ['11942', '12220', '11927', '11929', '12319', '11930', '11931', '19260']
        logger.debug("Fetching %d categorías en paralelo", len(category_ids))
        with ThreadPoolExecutor(max_workers=len(category_ids)) as executor:
            futures = {cat: executor.submit(self.get_data_event_by_category, path, cat)
                       for cat in category_ids}
            category_dfs = {cat: future.result() for cat, future in futures.items()}

        df_resultado = df_partidos
        for cat in category_ids:
            df_cat = category_dfs[cat].drop(columns=["partido"], errors="ignore")
            df_resultado = df_resultado.merge(df_cat, on="id", how="left")

        logger.info("DataFrame final: %d partidos, %d columnas", len(df_resultado), len(df_resultado.columns))
        return df_resultado

    def get_data_event_by_category(self, path, category):
        endpoint = (f".json?lang=es_ES&market=CO&client_id=2&channel_id=1"
                    f"&ncid=1641434366938&category={category}&useCombined=true")
        url = Config.API_URL + "/listView" + path + endpoint
        response = requests.get(url, headers=Config.HEADERS)
        data_api_json = response.json()
        events = data_api_json["events"]

        lista_partidos = []
        for e in events:
            event = e["event"]
            bet_offers = e["betOffers"]
            dicc_partido = {
                "id": event["id"],
                "partido": event["name"]
            }
            dicc_offers = self.get_offers_event(bet_offers)
            dicc_partido.update(dicc_offers)
            lista_partidos.append(dicc_partido)

        df_partidos = pd.DataFrame(lista_partidos)
        logger.debug("Categoría %s: %d eventos", category, len(df_partidos))
        return df_partidos

    def get_offers_event(self, bet_offers):
        dicc_offers = {}
        for offer in bet_offers:
            title = ""
            if offer["criterion"].get("label") is not None:
                title = offer["criterion"].get("label")
            for outcome in offer["outcomes"]:
                if outcome.get("line") is not None:
                    title_aux = unidecode(title + " " + outcome["label"] + " " + str(outcome["line"] / 1000))
                else:
                    title_aux = title + " " + outcome["label"]
                if outcome.get('odds') is not None:
                    dicc_offers[title_aux] = outcome["odds"] / 1000
        return dicc_offers
