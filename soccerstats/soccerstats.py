from scrapy.crawler import CrawlerProcess
from my_project.tablas_estadistica.estadistica_main import EstadisticaEquipo as ES
from scrapy.spiders import Spider
from scrapy.selector import Selector
import pandas as pd

class EstadisticaEquipo():
    class EstadisticaLiga(Spider):
        name = 'estadistica_liga'
        # Definicion de las configuraciones, 1=> para no ser baneado, 2=> salida de la data en formato legible
        custom_settings = {
            'USER_AGENT': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/71.0.3578.80 Chrome/71.0.3578.80 Safari/537.36',
            'FEED_EXPORT_ENCODING': 'utf-8'
        }

        download_delay = 2

        # URL semilla
        start_urls = ['https://www.soccerstats.com/latest.asp?league=england#']

