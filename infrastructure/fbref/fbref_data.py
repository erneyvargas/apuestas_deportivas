import pandas as pd
from io import StringIO
from seleniumbase import SB


class FbrefData:
    URL = "https://fbref.com/es/comps/9/Estadisticas-de-Premier-League"

    def get_data_table(self):
        """Obtiene todas las tablas de datos desde Fbref"""
        try:
            with SB(uc=True, headless=False) as sb:
                sb.open(self.URL)
                sb.sleep(5)
                html = sb.get_page_source()

            df_total = pd.read_html(StringIO(html), flavor="lxml")
            return list(df_total)

        except Exception as e:
            print(f"❌ Error obteniendo datos de Fbref: {e}")
            return []
