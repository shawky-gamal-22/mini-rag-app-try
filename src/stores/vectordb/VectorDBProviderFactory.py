from .providers import QdrantDBProvider
from .VectorDBEnums import VectorDBEnums
from controllers.BaseController import BaseController

class VectorDBProviderFactory:
    def __init__(self, config):
        self.config = config
        self.base_controller= BaseController()

    def create(self, provider:str):
        if provider == VectorDBEnums.QDRANT.value:
            return QdrantDBProvider(
                db_path=self.base_controller.get_database_path(db_name=self.config.VECTOR_DB_PATH),
                distance_method= self.config.VECTOR_DB_DISTANT_METHOD
            )
        

        return None
