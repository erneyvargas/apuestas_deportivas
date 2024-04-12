import pandas as pd


class FbrefData:
    url_df = 'https://fbref.com/es/comps/9/Estadisticas-de-Premier-League'

    def get_data_table(self):
        df_total = pd.read_html(self.url_df)
        df_list_response = []

        for i, df in enumerate(df_total, start=1):
            #file_path = f"../tmp/response_fbref_{i}.xlsx"
            #df.to_excel(file_path)
            print(df)
            df_list_response.append(df)

        return df_list_response
