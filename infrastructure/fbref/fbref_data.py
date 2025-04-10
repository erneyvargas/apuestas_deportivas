import pandas as pd


class FbrefData:
    URL = "https://fbref.com/es/comps/9/Estadisticas-de-Premier-League"

    def get_data_table(self):
        """Obtiene todas las tablas de datos desde Fbref"""
        try:
            df_total = pd.read_html(self.URL)
            df_list_response = []

            for df in df_total:
                df_list_response.append(df)

            return df_list_response

        except Exception as e:
            print(f"❌ Error obteniendo datos de Fbref: {e}")
            return []
