from infrastructure.fbref_data import FbrefData


class FbrefService:
    def __init__(self):
        self.fbref_data = FbrefData()

    def get_data_frame(self):
        """Obtiene y muestra los DataFrames de Fbref"""
        data_frames = self.fbref_data.get_data_table()

        if not data_frames:
            print("❌ No se encontraron datos en Fbref")
            return

        for i, df in enumerate(data_frames, start=1):
            print(f"📌 DataFrame {i}:")
            print(df.head())  # Muestra las primeras filas
