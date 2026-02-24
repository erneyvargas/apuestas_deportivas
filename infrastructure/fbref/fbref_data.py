import pandas as pd
from io import StringIO
from bs4 import BeautifulSoup
from seleniumbase import SB


class FbrefData:
    BASE_URL = "https://fbref.com/es/comps"

    def __init__(self, league_slug: str):
        self.url = f"{self.BASE_URL}/{league_slug}"

    def get_data_table(self) -> dict[str, pd.DataFrame]:
        """Obtiene las tablas de FBRef indexadas por su ID HTML"""
        try:
            with SB(uc=True, headless=False) as sb:
                sb.open(self.url)
                sb.sleep(5)
                html = sb.get_page_source()

            soup = BeautifulSoup(html, "lxml")
            tables = soup.find_all("table", id=True)

            result = {}
            for table in tables:
                table_id = table["id"]
                df = pd.read_html(StringIO(str(table)), flavor="lxml")[0]
                result[table_id] = df

            return result

        except Exception as e:
            print(f"❌ Error obteniendo datos de Fbref: {e}")
            return {}
