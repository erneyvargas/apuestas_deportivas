from scrapy.crawler import CrawlerProcess
from scrapy.item import Field
from scrapy.item import Item
from scrapy.spiders import Spider
from scrapy.spiders import Rule
from scrapy.selector import Selector
from scrapy.loader import ItemLoader

class PosicionesLiga(Item):
    # Definicion de las propiedades de los Items
    liga = Field()
    posicion = Field()
    nombre_equipo = Field()
    partidos_jugados = Field()
    partidos_ganados = Field()
    partidos_empatados = Field()
    partidos_perdidos = Field()
    goles_favor = Field()
    goles_en_contra = Field()
    goles_diferencia = Field()
    puntos = Field()

# Se encarga de los requerintos y parceos
class TablaPosiciones(Spider):
    name = 'tabla_posiciones'
    # Definicion de las configuraciones, 1=> para no ser baneado, 2=> salida de la data en formato legible
    custom_settings = {
        'USER_AGENT': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/71.0.3578.80 Chrome/71.0.3578.80 Safari/537.36',
        'FEED_EXPORT_ENCODING': 'utf-8'
    }

    # URL semilla
    start_urls = ['https://www.espn.com.co/futbol/posiciones/_/liga/esp.1']

    # Parseo de la Respuesta
    def parse(self, response):
        sel = Selector(response)

        # Tablas encontradas en HTML
        tabla_equipos = sel.xpath('(//table)[1]//tr')
        tabla_resultados = sel.xpath('(//table)[2]')

        # Extrae el nombre de la liga
        liga = sel.xpath('//div[@class="Table__Title"]/text()').get()

        # Iteracion para sacar las filas en la tabla resultados
        rows = []
        for resultado in tabla_resultados:
            rows = resultado.xpath(".//tr")

        # Iteracion de la tabla equipos y llenado de la data
        i = 0
        for equipo in tabla_equipos:
            item = ItemLoader(PosicionesLiga(), equipo)

            # definicion de las variables resultados
            partidos_jugados = rows[i].xpath(".//td[1]/span/text()")
            partidos_ganados = rows[i].xpath(".//td[2]/span/text()")
            partidos_empatados = rows[i].xpath(".//td[3]/span/text()")
            partidos_perdidos = rows[i].xpath(".//td[4]/span/text()")
            goles_favor = rows[i].xpath(".//td[5]/span/text()")
            goles_en_contra = rows[i].xpath(".//td[6]/span/text()")
            goles_diferencia = rows[i].xpath(".//td[7]/span/text()")
            puntos = rows[i].xpath(".//td[8]/span/text()")

            # LLenado de la data con los valores
            item.add_value("liga", liga)
            item.add_xpath("posicion", './/span[@class="team-position ml2 pr3"]/text()')
            item.add_xpath("nombre_equipo", './/span[@class="hide-mobile"]/a/text()')
            item.add_value("partidos_jugados", partidos_jugados.get())
            item.add_value("partidos_ganados", partidos_ganados.get())
            item.add_value("partidos_empatados", partidos_empatados.get())
            item.add_value("partidos_perdidos", partidos_perdidos.get())
            item.add_value("goles_favor", goles_favor.get())
            item.add_value("goles_en_contra", goles_en_contra.get())
            item.add_value("goles_diferencia", goles_diferencia.get())
            item.add_value("puntos", puntos.get())

            yield item.load_item()
            i += 1

# EJECUCION
process = CrawlerProcess({
  'FEED_FORMAT': 'json',
  'FEED_URI': 'tabla_posiciones_data.json'
})
process.crawl(TablaPosiciones)
process.start()