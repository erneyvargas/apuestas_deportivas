from scrapy.crawler import CrawlerProcess
from scrapy.spiders import Spider
from scrapy.selector import Selector
import pandas as pd
import re



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

    def parse(self, response):
        sel = Selector(response)

        # Tablas encontradas en HTML
        tablas = sel.xpath('//table')

        i = 1
        tablas_name = {}
        df = {}
        for tabla in tablas:

            tablas_name[i] = []
            rows = tabla.xpath(".//tr")
            for tr in rows:
                cols = tr.xpath(".//td")
                diccionario = {}
                contador = 1
                for cell in cols:
                    data = cell.xpath(".//*/text()").get()
                    if data == None:
                        data = cell.xpath("./text()").get()
                    if data == "\n":
                        data = cell.xpath(".//b/text()").get()
                    # Limpiar la data
                    if data != None:
                        data = data.replace("\xa0","").replace('\n', ' ').replace('\r', ' ').replace('\t', ' ').strip()
                    diccionario["dato"+str(contador)] =  data
                    contador += 1
                tablas_name[i].append(diccionario)
            df[i] = pd.DataFrame(tablas_name[i])
            print(df[i])
            i += 1
        print("k")

# EJECUCION

process = CrawlerProcess()
process.crawl(EstadisticaLiga)
process.start()