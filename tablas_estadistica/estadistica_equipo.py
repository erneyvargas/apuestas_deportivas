from scrapy.crawler import CrawlerProcess
from my_project.tablas_estadistica.estadistica_main import EstadisticaEquipo as ES
from scrapy.spiders import Spider
from scrapy.selector import Selector
import pandas as pd
import re

class EstadisticaEquipos(Spider):
    name = "estadistica_equpo"
    # Definicion de las configuraciones, 1=> para no ser baneado, 2=> salida de la data en formato legible
    custom_settings = ES.custom_settings

    download_delay = 2

    # URL semilla
    start_urls = ES.start_urls

    def limpiarTexto(self, texto):
        nuevo_texto = texto.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ').strip()
        return nuevo_texto

    # Parseo de la Respuesta
    lista_resultados = []
    def parse(self, response):
        sel = Selector(response)

        # Tablas encontradas en HTML
        resultado = sel.xpath('//div[@id="info"]')

        record = resultado.xpath('.//p[1]/text()[2]').get()
        record = record.split(",")
        resultados = self.limpiarTexto(record[0])
        puntos = self.limpiarTexto(record[1])

        record_local = resultado.xpath('.//p[2]/text()[2]').get()
        record_local = record_local.split(",")
        resultados_local = self.limpiarTexto(record_local[0])
        puntos_local = self.limpiarTexto(record_local[1])


        record_visitante = resultado.xpath('.//p[2]/text()[3]').get()
        record_visitante = record_visitante.split(",")
        resultados_visitante = self.limpiarTexto(record_visitante[0])
        puntos_visitante = self.limpiarTexto(record_visitante[1])



        goles = resultado.xpath('.//p[3]/text()[1]').get()
        goles_contra = resultado.xpath('.//p[3]/text()[2]').get()
        diferencia = resultado.xpath('.//p[3]/text()[3]').get()
        goles_esperados = resultado.xpath('.//p[4]/text()[1]').get()
        goles_permitidos = resultado.xpath('.//p[4]/text()[2]').get()
        x_diferencia = resultado.xpath('.//p[4]/text()[3]').get()
        ultimo_partido = resultado.xpath('.//p[5]/text()').get()
        siguiente_partido = resultado.xpath('.//p[6]/text()').get()
        entrenador = resultado.xpath('.//p[7]/text()').get()
        pais = resultado.xpath('.//p[8]/a/text()').get()
        genero = resultado.xpath('.//p[9]/text()').get()

        self.lista_resultados.append({
            "resultados": resultados,
            "puntos": puntos,
            "resultados_local" : resultados_local,
            "puntos_local" : puntos_local,
            "resultados_visitante" : resultados_visitante,
            "puntos_visitante" : puntos_visitante,
            "goles" : self.limpiarTexto(goles),
            "goles_contra" : self.limpiarTexto(goles_contra),
            "diferencia": diferencia,
            "goles_esperados" : self.limpiarTexto(goles_esperados),
            "goles_permitidos" : self.limpiarTexto(goles_permitidos),
            "x_diferencia" : x_diferencia,
            "ultimo_partido" : ultimo_partido,
            "siguiente_partido" : siguiente_partido,
            "entrenador" : entrenador,
            "pais" : pais,
            "genero" : genero.replace(":",""),

        })

        #temporada = re.findall(r"\d+[\-]\d+", info_equipo)[0]
        df = pd.DataFrame(self.lista_resultados)
        print(df)
        df.to_csv("estadistica.csv")

    # EJECUCION


process = CrawlerProcess()
process.crawl(EstadisticaEquipos)
process.start()