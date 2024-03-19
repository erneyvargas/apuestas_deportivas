from scrapy.crawler import CrawlerProcess
from my_project.tablas_estadistica.estadistica_main import EstadisticaEquipo as ES
from scrapy.spiders import Spider
from scrapy.selector import Selector
import pandas as pd


class EstadisticaLigaFbref(Spider):
    name = 'estadistica_equipo'
    # Definicion de las configuraciones, 1=> para no ser baneado, 2=> salida de la data en formato legible
    custom_settings = {
        'USER_AGENT': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/71.0.3578.80 Chrome/71.0.3578.80 Safari/537.36',
        'FEED_EXPORT_ENCODING': 'utf-8'
    }

    download_delay = 2

    # URL semilla
    start_urls = ["https://fbref.com/es/comps/9/Estadisticas-de-Premier-League"]

    def parse(self, response):
        sel = Selector(response)
        # Tablas encontradas en HTML
        tabla_liga = sel.xpath('//table[@id="results111601_overall"]')
        tabla_estandar_equipo = sel.xpath('//table[@id="stats_squads_standard_for"]')
        tabla_porteria_equipo = sel.xpath('//table[@id="stats_squads_keeper_for"]')
        tabla_porteria_avanzada = sel.xpath('//table[@id="stats_squads_keeper_adv_for"]')
        tabla_disparos_equipo = sel.xpath('//table[@id="stats_squads_shooting_for"]')
        tabla_pases_equipo = sel.xpath('//table[@id="stats_squads_passing_for"]')
        tabla_tipo_pases_equipo = sel.xpath('//table[@id="stats_squads_passing_types_for"]')
        tabla_creacion_goles = sel.xpath('//table[@id="stats_squads_gca_for"]')
        tabla_acciones_defensivas = sel.xpath('//table[@id="stats_squads_defense_for"]')
        tabla_posesion_equipo = sel.xpath('//table[@id="stats_squads_possession_for"]')
        tabla_tiempo_juego = sel.xpath('//table[@id="stats_squads_playing_time_for"]')
        tabla_estadisticas_adicionales = sel.xpath('//table[@id="stats_squads_misc_for"]')

        df_tabla_liga = self.recorrer_tabla(tabla_liga)
        df_tabla_estandar_equipo= self.recorrer_tabla(tabla_estandar_equipo)
        df_tabla_porteria_equipo = self.recorrer_tabla(tabla_porteria_equipo)
        df_tabla_porteria_avanzada = self.recorrer_tabla(tabla_porteria_avanzada)
        df_tabla_disparos_equipo = self.recorrer_tabla(tabla_disparos_equipo)
        df_tabla_pases_equipo = self.recorrer_tabla(tabla_pases_equipo)
        df_tabla_tipo_pases_equipo = self.recorrer_tabla(tabla_tipo_pases_equipo)
        df_tabla_creacion_goles = self.recorrer_tabla(tabla_creacion_goles)
        df_tabla_acciones_defensivas = self.recorrer_tabla(tabla_acciones_defensivas)
        df_tabla_posesion_equipo = self.recorrer_tabla(tabla_posesion_equipo)
        df_tabla_tiempo_juego = self.recorrer_tabla(tabla_tiempo_juego)
        df_tabla_estadisticas_adicionales = self.recorrer_tabla(tabla_estadisticas_adicionales)
        df_tabla_estadisticas_adicionales.to_excel("prueba.xlsx")
        print("")

    def recorrer_tabla(self, tabla):

        # Sacar Titulos para las columnas
        rows_title = tabla.xpath("./thead/tr[2]")
        if len(rows_title) == 0:
            rows_title = tabla.xpath("./thead/tr[1]")
        lista_titulo = []
        for cols_title in rows_title:
            col_title = cols_title.xpath("./th")
            for cel_title in col_title:
                title = cel_title.xpath("./text()").get()
                lista_titulo.append(title)

        # Obtener la data de las Columnas
        rows = tabla.xpath("./tbody/tr")
        lista = []

        for cols in rows:
            col = cols.xpath("./td")
            contador = 1
            diccionario = {}
            diccionario[lista_titulo[0]] = cols.xpath("./th/a/text()").get()

            for cell in col:
                data = cell.xpath("./text()").get()
                if (data == None or data == " ") or data == " - " or data == ", ":
                    data = cell.xpath("./a/text()").get()
                diccionario[lista_titulo[contador]] = data
                contador += 1

            lista.append(diccionario)

        df_result = pd.DataFrame(lista)
        return df_result


        print(df_tabla_liga)


# EJECUCION

process = CrawlerProcess()
process.crawl(EstadisticaLigaFbref)
process.start()