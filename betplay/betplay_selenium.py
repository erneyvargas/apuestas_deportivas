from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import pandas as pd
import time

# instanciar el driver
driver = webdriver.Chrome('../../chromedriver')

# Abrir la pagina
driver.get('https://betplay.com.co/apuestas#filter/football/england/premier_league')
time.sleep(1)
driver.set_window_size(1280,800)
botones = WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.XPATH, '//div[contains(@class, "KambiBC-mod-event-group-container") and not(contains(@class, "KambiBC-expanded"))]'))
        )
for boton in botones:
     boton.click()

# tiempo de espera de carga de la informacion dinamica, espera que el precion exista
WebDriverWait(driver, 20).until(
     EC.presence_of_all_elements_located((By.XPATH, '//div[@class="KambiBC-event-groups-list"]//div[@class="KambiBC-event-participants"]'))
)
lista_encuntros = driver.find_elements_by_xpath('//div[@class="KambiBC-event-groups-list"]')
lista_encuentros = []
for encuntros in lista_encuntros:
     # Busco elementos dentro de la lista autos (.//)
     rows = encuntros.find_elements_by_xpath('.//div[@class="KambiBC-event-item__event-wrapper"]')

     for row in rows:

          fecha = row.find_element_by_xpath('.//div[@class="KambiBC-event-item__match-clock-container"]')
          equipos = row.find_element_by_xpath('.//div[@class="KambiBC-event-participants"]')
          oferta = row.find_element_by_xpath('.//span[@class="KambiBC-event-item__bet-offer-count"]')
          puntos = row.find_element_by_xpath('.//div[contains(@class,"KambiBC-bet-offers-list__column--num-3")]')
          total_goles = row.find_element_by_xpath('.//div[contains(@class,"KambiBC-bet-offer--outcomes-2")]')

          fecha = fecha.text.split('\n')
          fecha_dia = fecha[0]
          fecha_hora = fecha[1]

          equipos = equipos.text.split('\n')
          local = equipos[0]
          visitante = equipos[1]

          puntos = puntos.text.split()
          gana_local = puntos[0]
          empate = puntos[1]
          gana_visitante = puntos[2]

          total_goles = total_goles.text.split('\n')
          mas_de_2_5 = total_goles[2]
          menos_de_2_5 = total_goles[5]

          lista_encuentros.append({
               "fecha": fecha_dia,
               "hora": fecha_hora,
               "local": local,
               "visitante": visitante,
               "oferta": oferta.text,
               "gana_local": gana_local,
               "empate": empate,
               "gana_visitante": gana_visitante,
               "mas_de_2_5": mas_de_2_5,
               "menos_de_2_5" : menos_de_2_5,
          })
df = pd.DataFrame(lista_encuentros)
print(df)

driver.close()


