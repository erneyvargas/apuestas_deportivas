import pandas as pd
from infrastructure.fbref.fbref_data import FbrefData
from infrastructure.persistence.mongo_db_repository import MongoDBRepository


class FbrefService:
    def __init__(self):
        self.fbref_data = FbrefData()
        self.repo = MongoDBRepository()

    def _flatten_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aplana columnas MultiIndex filtrando niveles 'Unnamed'"""
        if isinstance(df.columns, pd.MultiIndex):
            new_cols = []
            for col in df.columns:
                parts = [str(c) for c in col if "Unnamed" not in str(c)]
                new_cols.append("_".join(parts) if parts else str(col[-1]))
            df.columns = new_cols
        return df

    def get_data_frame(self):
        """Obtiene los DataFrames de FBRef y los guarda en MongoDB"""
        tables = self.fbref_data.get_data_table()

        if not tables:
            print("❌ No se encontraron datos en Fbref")
            return

        print(f"📊 Tablas encontradas: {len(tables)}")
        for table_id, df in tables.items():
            df = self._flatten_columns(df)
            self.repo.save_dataframe_to_collection(f"fbref_{table_id}", df)
