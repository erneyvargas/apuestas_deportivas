from data.fbref.fbref_data import FbrefData


class FbrefService:
    def get_data_frame(self):
        fbref = FbrefData()
        data = fbref.get_data_table()
        for i, df in enumerate(data, start=1):
            print(f"DataFrame {i}:")
            print(df.head())
