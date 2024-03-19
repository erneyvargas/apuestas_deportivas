from scrapy.crawler import CrawlerProcess
from scrapy.spiders import CrawlSpider
from scrapy.spiders import Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.selector import Selector
import json
import pandas as pd


class Calendario(CrawlSpider):
    name = "ultimos_resultados"
    # Numero maximo de paginas en las cuales voy a descargar items. Scrapy se cierra cuando alcanza este numero
    custom_settings = {
        'USER_AGENT': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/71.0.3578.80 Chrome/71.0.3578.80 Safari/537.36',
        'FEED_EXPORT_ENCODING': 'utf-8',
        #'CLOSESPIDER_PAGECOUNT': 20
    }
    # Tiempo de espera para hacer peticion al servisor
    download_delay = 1

    # dominios que se pueden sacar datos, esto para evitar que se dirija a otros links
    allowed_domains = ["espn.com.co"]

    #start_urls = ["https://www.espn.com.co/futbol/posiciones/_/liga/esp.1"]
    start_urls = ["https://www.espn.com.co/futbol/posiciones/_/liga/eng.1"]


    rules = (
        Rule(
            LinkExtractor(
                allow=r'/futbol/equipo/_/id/',
                restrict_xpaths=['//span[@class="dn show-mobile"]']
            ), follow=True
        ),
        Rule(
            LinkExtractor(
                allow=r'/futbol/equipo/calendario/_/id/'
            ), follow=True, callback="parse_items"
        ),
    )

    lista_resultados = []

    def parse_items(self, response):
        sel = Selector(response)
        # Tablas encontradas en HTML
        datos = sel.xpath('//script[contains(text(), "__espnfitt__")]/text()').get()
        indice_inicial = datos.find('{')

        datos = datos[indice_inicial:]
        datos = datos.replace(";", "")

        objeto = json.loads(datos)
        resultados = objeto["page"]["content"]["fixtures"]["events"]
        nombre_equipo = objeto["page"]["content"]["fixtures"]["team"]["displayName"]
        print(nombre_equipo)
        for resultado in resultados:

            if resultado:
                self.lista_resultados.append({
                    "equipo": nombre_equipo,
                    "fecha": pd.to_datetime(resultado["date"]),
                    "local": resultado["teams"][0]["displayName"],
                    "visitante": resultado["teams"][1]["displayName"],
                    "fecha_detalle": resultado["status"]["detail"],
                    "liga": resultado["league"],
                    "sede": resultado["venue"]["fullName"],
                    "ciudad": resultado["venue"]["address"]["city"],
                    "pais": resultado["venue"]["address"]["country"]
                })
        df = pd.DataFrame(self.lista_resultados)
        print(df)
        df.to_csv("calendario.csv")




# EJECUCION
process = CrawlerProcess()
process.crawl(Calendario)
process.start()
