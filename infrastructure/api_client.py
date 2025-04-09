from datetime import datetime

import pandas as pd
import requests
from unidecode import unidecode

from infrastructure.config import Config


class BetplayAPIClient:

    @staticmethod
    def fetch_leagues():
        try:
            response = requests.get(
                Config.API_URL,
                params=Config.DEFAULT_PARAMS,
                headers=Config.HEADERS,
                timeout=10
            )
            response.raise_for_status()
            return response.json().get('groups', [])
        except requests.exceptions.RequestException as e:
            print(f"[API Error] {str(e)}")
            return None

    def get_full_data(self, path):
        df_partidos = self.get_datos_partidos(path)
        df_resultado = df_partidos
        return df_resultado


    def get_datos_partidos(self, path):
        headers = {
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36',
        }

        baseUrl = "https://na-offering-api.kambicdn.net/offering/v2018/betplay"
        url_api_partido = baseUrl + "/listView" + path + ".json?lang=es_ES&market=CO&client_id=2&channel_id=1&ncid=1641434042006&useCombined=true"
        response = requests.get(url_api_partido, headers=headers)
        data_api_partido = response.json()
        partidos = data_api_partido["events"]

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
        df_equipos_marcan = self.get_data_event_by_category(path, '11942')
        df_doble_oportunidad = self.get_data_event_by_category(path, '12220')
        df_primer_tiempo = self.get_data_event_by_category(path, '11927')
        df_sin_empate = self.get_data_event_by_category(path, '11929')
        df_handicap_asiatico = self.get_data_event_by_category(path, '12319')
        df_goles_equipo_local = self.get_data_event_by_category(path, '11930')
        df_goles_equipo_visitante = self.get_data_event_by_category(path, '11931')
        df_corners = self.get_data_event_by_category(path, '19260')

        df_resultado = df_partidos.merge(df_equipos_marcan)
        df_resultado = df_resultado.merge(df_doble_oportunidad)
        df_resultado = df_resultado.merge(df_primer_tiempo)
        df_resultado = df_resultado.merge(df_sin_empate)
        # df_resultado = df_resultado.merge(df_handicap_asiatico)
        # df_resultado = df_resultado.merge(df_goles_equipo_local)
        # df_resultado = df_resultado.merge(df_goles_equipo_visitante)
        df_resultado = df_resultado.merge(df_corners)

        return df_resultado


    def get_data_event_by_category(self, path, category):
        baseUrl = "https://na-offering-api.kambicdn.net/offering/v2018/betplay"
        headers = {
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36',
        }
        endpoint = ".json?lang=es_ES&market=CO&client_id=2&channel_id=1&ncid=1641434366938&category=" + category + "&useCombined=true";
        url_api = baseUrl + "/listView" + path + endpoint
        response = requests.get(url_api, headers=headers)
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
