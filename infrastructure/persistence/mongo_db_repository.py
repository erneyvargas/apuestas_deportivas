import logging
from typing import List, Tuple

import pandas as pd

from infrastructure.persistence.mongo_config import MongoConfig

logger = logging.getLogger(__name__)


class MongoDBRepository:
    def __init__(self, db_name: str):
        self.db = MongoConfig.get_db(db_name)

    def save_dataframe_to_collection(
            self,
            collection_name: str,
            df: pd.DataFrame,
            clear_collection: bool = True
    ) -> Tuple[bool, int]:
        try:
            collection = self.db[collection_name]

            if clear_collection:
                deleted = collection.delete_many({})
                logger.debug("Colección '%s' limpiada (%d docs eliminados)", collection_name, deleted.deleted_count)

            if df.empty:
                logger.warning("DataFrame vacío recibido para colección '%s'", collection_name)
                return True, 0

            records = df.to_dict('records')
            result = collection.insert_many(records)
            inserted_count = len(result.inserted_ids)
            logger.info("'%s' — %d documentos insertados", collection_name, inserted_count)
            return True, inserted_count

        except Exception as e:
            logger.error("Error guardando en '%s': %s", collection_name, e, exc_info=True)
            return False, 0

    def ensure_index(self, collection_name: str, keys: List[Tuple[str, int]]):
        """Crea un índice compuesto si no existe (operación idempotente)."""
        try:
            self.db[collection_name].create_index(keys)
            logger.debug("Índice asegurado en '%s': %s", collection_name, keys)
        except Exception as e:
            logger.warning("No se pudo crear índice en '%s': %s", collection_name, e)
