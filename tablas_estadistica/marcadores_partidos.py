from scrapy.crawler import CrawlerProcess
from my_project.tablas_estadistica.estadistica_main import EstadisticaEquipo as ES
from scrapy.spiders import Spider
from scrapy.selector import Selector
import pandas as pd
import re

class MarcadoresPartidos(Spider):
    name = "marcadores_partidos"
    # Definicion de las configuraciones, 1=> para no ser baneado, 2=> salida de la data en formato legible
    custom_settings = ES.custom_settings

    download_delay = 2

    # URL semilla
    start_urls = ES.start_urls

    # Parseo de la Respuesta
    lista_resultados = []
    def parse(self, response):
        sel = Selector(response)

        # Tablas encontradas en HTML
        info_equipo = sel.xpath('//div[@id="all_matchlogs"]//h2/span/text()').get()
        temporada = re.findall(r"\d+[\-]\d+", info_equipo)[0]
        equipo = re.findall(r"[a-zA-Z][^:]*", info_equipo)[0]

        resultados = sel.xpath('//table[@id="matchlogs_for"]/tbody')
        for result in resultados:
            rows = result.xpath('./tr')
            for row in rows:
                fecha = row.xpath('./th/a/text()').get()
                if fecha == None:
                    fecha = row.xpath('./th/text()').get()

                hora = row.xpath('./td[@data-stat="time"]//*/text()').get()
                competencia = row.xpath('./td[@data-stat="comp"]/a/text()').get()
                ronda = row.xpath('./td[@data-stat="round"]/a/text()').get()
                dia = row.xpath('./td[@data-stat="dayofweek"]/text()').get()
                sede = row.xpath('./td[@data-stat="venue"]/text()').get()
                resultado = row.xpath('./td[@data-stat="result"]/text()').get()
                goles_favor = row.xpath('./td[@data-stat="goals_for"]/text()').get()
                goles_contra = row.xpath('./td[@data-stat="goals_against"]/text()').get()
                adversario = row.xpath('./td[@data-stat="opponent"]/a/text()').get()
                goles_esperados = row.xpath('./td[@data-stat="xg_for"]/text()').get()
                goles_esperados_permitidos = row.xpath('./td[@data-stat="xg_against"]/text()').get()
                posesion = row.xpath('./td[@data-stat="possession"]/text()').get()
                asistencia = row.xpath('./td[@data-stat="attendance"]/text()').get()
                capitan = row.xpath('./td[@data-stat="captain"]/a/text()').get()
                formacion = row.xpath('./td[@data-stat="formation"]/text()').get()
                arbitro = row.xpath('./td[@data-stat="referee"]/text()').get()
                notas = row.xpath('./td[@data-stat="note"]/text()').get()

                self.lista_resultados.append({
                    "temporada": temporada,
                    "equipo": equipo,
                    "fecha": fecha,
                    "hora": hora,
                    "competencia": competencia,
                    "ronda": ronda,
                    "dia": dia,
                    "sede": sede,
                    "resultado": resultado,
                    "goles_favor": goles_favor,
                    "goles_contra": goles_contra,
                    "adversario": adversario,
                    "goles_esperados": goles_esperados,
                    "goles_esperados_permitidos": goles_esperados_permitidos,
                    "posesion": posesion,
                    "asistencia": asistencia,
                    "capitan": capitan,
                    "formacion": formacion,
                    "arbitro": arbitro,
                    "notas": notas
                })

        df = pd.DataFrame(self.lista_resultados)
        print(df)
        df.to_csv("estadistica.csv")

    # EJECUCION


process = CrawlerProcess()
process.crawl(MarcadoresPartidos)
process.start()
