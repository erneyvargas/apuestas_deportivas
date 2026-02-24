import pandas as pd
from typing import Tuple
from infrastructure.persistence.mongo_config import MongoConfig


class MongoDBRepository:
    def __init__(self, db_name: str):
        self.db = MongoConfig.get_db(db_name)

    def save_dataframe_to_collection(
            self,
            collection_name: str,
            df: pd.DataFrame,
            clear_collection: bool = True
    ) -> Tuple[bool, int]:
        """
        Guarda un DataFrame en una colección de MongoDB y muestra el resultado

        Args:
            collection_name: Nombre de la colección
            df: DataFrame a guardar
            clear_collection: Si True, borra la colección antes de insertar

        Returns:
            Tuple (success, inserted_count):
                - success: True si la operación fue exitosa
                - inserted_count: Número de documentos insertados
        """
        try:
            collection = self.db[collection_name]

            if clear_collection:
                collection.delete_many({})

            if df.empty:
                print(f"⚠️ Colección '{collection_name}' recibió DataFrame vacío")
                return True, 0

            records = df.to_dict('records')
            result = collection.insert_many(records)
            inserted_count = len(result.inserted_ids)

            # Mensaje de éxito dentro del repositorio
            print(f"✅ Se insertaron {inserted_count} documentos en '{collection_name}'")

            return True, inserted_count

        except Exception as e:
            # Mensaje de error dentro del repositorio
            print(f"❌ Error guardando en '{collection_name}': {str(e)}")
            return False, 0