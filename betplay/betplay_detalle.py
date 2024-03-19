import requests
import pandas as pd

headers = {
    'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36',
    }

url_api_partido = "https://us1-api.aws.kambicdn.com/offering/v2018/betplay/listView/football/england/premier_league.json?lang=es_ES&market=CO&client_id=2&channel_id=1&ncid=1641434042006&useCombined=true"
response = requests.get(url_api_partido, headers= headers)
data_api_partido = response.json()

url_api_ambos_equipos_marcan = "https://us1-api.aws.kambicdn.com/offering/v2018/betplay/listView/football/england/premier_league.json?lang=es_ES&market=CO&client_id=2&channel_id=1&ncid=1641434366938&category=11942&useCombined=true"
response = requests.get(url_api_ambos_equipos_marcan, headers= headers)
data_api_ambos_equipos_marcan = response.json()

url_api_doble_oprtunidad = "https://us1-api.aws.kambicdn.com/offering/v2018/betplay/listView/football/england/premier_league.json?lang=es_ES&market=CO&client_id=2&channel_id=1&ncid=1641434371608&category=12220&useCombined=true"
response = requests.get(url_api_doble_oprtunidad, headers= headers)
data_api_doble_oprtunidad = response.json()

url_api_primer_tiempo = "https://us1-api.aws.kambicdn.com/offering/v2018/betplay/listView/football/england/premier_league.json?lang=es_ES&market=CO&client_id=2&channel_id=1&ncid=1641434379674&category=11927&useCombined=true"
response = requests.get(url_api_primer_tiempo, headers= headers)
data_api_primer_tiempo = response.json()

url_api_goles_primer_tiempo = "https://us1-api.aws.kambicdn.com/offering/v2018/betplay/listView/football/england/premier_league.json?lang=es_ES&market=CO&client_id=2&channel_id=1&ncid=1641953882492&useCombined=true"
response = requests.get(url_api_goles_primer_tiempo, headers= headers)
data_api_goles_primer_tiempo = response.json()

url_api_sin_empate = "https://us1-api.aws.kambicdn.com/offering/v2018/betplay/listView/football/england/premier_league.json?lang=es_ES&market=CO&client_id=2&channel_id=1&ncid=1641954520859&category=11929&useCombined=true"
response = requests.get(url_api_sin_empate, headers= headers)
data_api_sin_empate = response.json()


url_api_handicap_asiatico = "https://us1-api.aws.kambicdn.com/offering/v2018/betplay/listView/football/england/premier_league.json?lang=es_ES&market=CO&client_id=2&channel_id=1&ncid=1641956881357&category=12319&useCombined=true"
response = requests.get(url_api_handicap_asiatico, headers= headers)
data_api_handicap_asiatico = response.json()


url_api_goles_equipo_local = "https://us1-api.aws.kambicdn.com/offering/v2018/betplay/listView/football/england/premier_league.json?lang=es_ES&market=CO&client_id=2&channel_id=1&ncid=1641957488162&category=11930&useCombined=true"
response = requests.get(url_api_goles_equipo_local, headers= headers)
data_api_goles_equipo_local = response.json()

url_api_goles_equipo_visitante = "https://us1-api.aws.kambicdn.com/offering/v2018/betplay/listView/football/england/premier_league.json?lang=es_ES&market=CO&client_id=2&channel_id=1&ncid=1641958021621&category=11931&useCombined=true"
response = requests.get(url_api_goles_equipo_visitante, headers= headers)
data_api_goles_equipo_visitante = response.json()


partidos = data_api_partido["events"]
equipos_marcan = data_api_ambos_equipos_marcan["events"]
doble_oprtunidad = data_api_doble_oprtunidad["events"]
primer_tiempo = data_api_primer_tiempo["events"]
goles_primer_tiempo = data_api_goles_primer_tiempo["events"]
apuestas_sin_empate = data_api_sin_empate["events"]
handicap_asiatico = data_api_handicap_asiatico["events"]
goles_equipo_local = data_api_goles_equipo_local["events"]
goles_equipo_visistante = data_api_goles_equipo_visitante["events"]

lista_partidos = []
lista_equipos_marcan = []
lista_doble_oprtunidad = []
lista_primer_tiempo = []
lista_goles_primer_tiempo = []
lista_apuesta_sin_empate = []
lista_handicap_asiatico = []
lista_goles_equipo_local = []
lista_goles_equipo_visitante = []

for partido in partidos:
    lista_partidos.append({
        "liga": partido["event"]["group"],
        "partido": partido["event"]["name"],
        "homeName": partido["event"]["homeName"],
        "awayName": partido["event"]["awayName"],
        "gana_home": partido["betOffers"][0]["outcomes"][0]["odds"]/1000,
        "empate": partido["betOffers"][0]["outcomes"][1]["odds"]/1000,
        "gana_away": partido["betOffers"][0]["outcomes"][2]["odds"]/1000,
        "mas_de_": partido["betOffers"][1]["outcomes"][0]["line"] / 1000,
        "mas_value": partido["betOffers"][1]["outcomes"][0]["odds"] / 1000,
        "menos_de_": partido["betOffers"][1]["outcomes"][1]["line"] / 1000,
        "menos_value": partido["betOffers"][1]["outcomes"][1]["odds"] / 1000,
   })

for equipo_marca in equipos_marcan:
    lista_equipos_marcan.append({
        "liga": equipo_marca["event"]["group"],
        "partido": equipo_marca["event"]["name"],
        "homeName": equipo_marca["event"]["homeName"],
        "awayName": equipo_marca["event"]["awayName"],
        "Si": equipo_marca["betOffers"][0]["outcomes"][0]["odds"]/1000,
        "NO": equipo_marca["betOffers"][0]["outcomes"][1]["odds"]/1000,
   })

for doble in doble_oprtunidad:
    lista_doble_oprtunidad.append({
        "liga": doble["event"]["group"],
        "partido": doble["event"]["name"],
        "homeName": doble["event"]["homeName"],
        "awayName": doble["event"]["awayName"],
        "1X": doble["betOffers"][0]["outcomes"][0]["odds"]/1000,
        "12": doble["betOffers"][0]["outcomes"][1]["odds"]/1000,
        "x2": doble["betOffers"][0]["outcomes"][2]["odds"]/1000,
   })

for primer_t in primer_tiempo:
    lista_primer_tiempo.append({
        "liga": primer_t["event"]["group"],
        "partido": primer_t["event"]["name"],
        "homeName": primer_t["event"]["homeName"],
        "awayName": primer_t["event"]["awayName"],
        "gana_home_primer_tiempo": primer_t["betOffers"][0]["outcomes"][0]["odds"]/1000,
        "empate_primer_tiempo": primer_t["betOffers"][0]["outcomes"][1]["odds"]/1000,
        "gana_away_primer_tiempo": primer_t["betOffers"][0]["outcomes"][2]["odds"]/1000,
   })

for goles_primer_t in goles_primer_tiempo:
    lista_goles_primer_tiempo.append({
        "liga": goles_primer_t["event"]["group"],
        "partido": goles_primer_t["event"]["name"],
        "homeName": goles_primer_t["event"]["homeName"],
        "awayName": goles_primer_t["event"]["awayName"],
        "mas_de_line": goles_primer_t["betOffers"][1]["outcomes"][0]["line"]/1000,
        "mas_de": goles_primer_t["betOffers"][1]["outcomes"][0]["odds"]/1000,
        "menos_de_line": goles_primer_t["betOffers"][1]["outcomes"][1]["line"]/1000,
        "menos_de": goles_primer_t["betOffers"][1]["outcomes"][1]["odds"]/1000,
   })

for apusta_sin_empate in apuestas_sin_empate:
    lista_apuesta_sin_empate.append({
        "liga": apusta_sin_empate["event"]["group"],
        "partido": apusta_sin_empate["event"]["name"],
        "homeName": apusta_sin_empate["event"]["homeName"],
        "awayName": apusta_sin_empate["event"]["awayName"],
        "home_sin_empate": apusta_sin_empate["betOffers"][0]["outcomes"][0]["odds"]/1000,
        "away_sin_empate": apusta_sin_empate["betOffers"][0]["outcomes"][1]["odds"]/1000,
   })

for handicap_a in handicap_asiatico:
    lista_handicap_asiatico.append({
        "liga": handicap_a["event"]["group"],
        "partido": handicap_a["event"]["name"],
        "homeName": handicap_a["event"]["homeName"],
        "awayName": handicap_a["event"]["awayName"],
        "home_line": handicap_a["betOffers"][0]["outcomes"][0]["line"]/1000,
        "home": handicap_a["betOffers"][0]["outcomes"][0]["odds"]/1000,
        "away_line": handicap_a["betOffers"][0]["outcomes"][1]["line"]/1000,
        "away": handicap_a["betOffers"][0]["outcomes"][1]["odds"]/1000,
   })

for goles in goles_equipo_local:
    lista_goles_equipo_local.append({
        "liga": goles["event"]["group"],
        "partido": goles["event"]["name"],
        "homeName": goles["event"]["homeName"],
        "awayName": goles["event"]["awayName"],
        "local_mas_de": goles["betOffers"][0]["outcomes"][0]["line"]/1000,
        "local_value": goles["betOffers"][0]["outcomes"][0]["odds"]/1000,
        "local_menos_de": goles["betOffers"][0]["outcomes"][1]["line"]/1000,
        "local_value2": goles["betOffers"][0]["outcomes"][1]["odds"]/1000,
   })

for goles in goles_equipo_visistante:
    lista_goles_equipo_visitante.append({
        "liga": goles["event"]["group"],
        "partido": goles["event"]["name"],
        "homeName": goles["event"]["homeName"],
        "awayName": goles["event"]["awayName"],
        "visitante_mas_de": goles["betOffers"][0]["outcomes"][0]["line"]/1000,
        "visitante_value1": goles["betOffers"][0]["outcomes"][0]["odds"]/1000,
        "visitante_menos_de": goles["betOffers"][0]["outcomes"][1]["line"]/1000,
        "visitante_value2": goles["betOffers"][0]["outcomes"][1]["odds"]/1000,
   })
df_partidos = pd.DataFrame(lista_partidos)
df_equipos_marcan = pd.DataFrame(lista_equipos_marcan)
df_doble_oportunidad = pd.DataFrame(lista_doble_oprtunidad)
df_primer_tiempo = pd.DataFrame(lista_primer_tiempo)
df_goles_primer_tiempo = pd.DataFrame(lista_goles_primer_tiempo)
df_apuesta_sin_empate = pd.DataFrame(lista_apuesta_sin_empate)
df_handicap_asiatico = pd.DataFrame(lista_handicap_asiatico)
df_goles_equipo_local = pd.DataFrame(lista_goles_equipo_local)
df_goles_equipo_visitante = pd.DataFrame(lista_goles_equipo_visitante)

df_resultado = df_partidos.merge(df_equipos_marcan)
df_resultado = df_resultado.merge(df_doble_oportunidad)
df_resultado = df_resultado.merge(df_primer_tiempo)
df_resultado = df_resultado.merge(df_goles_primer_tiempo)
df_resultado = df_resultado.merge(df_apuesta_sin_empate)
df_resultado = df_resultado.merge(df_handicap_asiatico)
df_resultado = df_resultado.merge(df_goles_equipo_local)
df_resultado = df_resultado.merge(df_goles_equipo_visitante)
print(df_resultado)
"""


Dobles:


Primer tiempo


Total goles primera parte
https://us1-api.aws.kambicdn.com/offering/v2018/betplay/listView/football/england/premier_league.json?lang=es_ES&market=CO&client_id=2&channel_id=1&ncid=1641434379674&category=11927&useCombined=true



https://us1-api.aws.kambicdn.com/offering/v2018/betplay/listView/football/england/premier_league.json?lang=es_ES&market=CO&client_id=2&channel_id=1&ncid=1641434457953&category=11942&useCombined=true





https://us1-api.aws.kambicdn.com/offering/v2018/betplay/listView/football/england/premier_league.json?lang=es_ES&market=CO&client_id=2&channel_id=1&ncid=1641434462714&category=12220&useCombined=true




https://us1-api.aws.kambicdn.com/offering/v2018/betplay/listView/football/england/premier_league.json?lang=es_ES&market=CO&client_id=2&channel_id=1&ncid=1641434472788&category=11927&useCombined=true

"""

#df.to_csv("cursos_udemy.csv")