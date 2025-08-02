from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    APP_NAME: str
    APP_VERSION: str
    OPENAI_API_KEY: str

    FILE_ALLOWED_TYPES: list[str]
    FILE_MAX_SIZE: int
    FILE_DEFAULT_CHUNK_SIZE: int 

    # MONGODB_URI: str
    # MONGODB_DATABASE: str

    POSTGRES_USERNAME: str
    POSTGRES_PASSWORD : str
    POSTGRES_HOST : str
    POSTGRES_PORT: int
    POSTGRES_MAIN_DATABASE: str


    GENERATION_BACKEND: str
    EMBEDDING_BACKEND: str

    OPENAI_API_KEY: str = None
    OPENAI_API_URL: str = None

    COHERE_API_KEY: str = None
    GENERATION_MODEL_ID_LITTERAL: List[str] = None
    GENERATION_MODEL_ID: str = None
    EMBEDDING_MODEL_ID: str = None
    EMBEDDING_MODEL_SIZE: int = None

    INPUT_DEFAULT_MAX_CHARACTERS: int = None
    GENERATION_DEFAULT_MAX_TOKENS: int= None
    GENERATION_DEFAULT_TEMPERATURE: float= None

    VECTOR_DB_BACKEND_LITTERAL: List[str] = None
    VECTOR_DB_BACKEND : str
    VECTOR_DB_PATH : str
    VECTOR_DB_DISTANT_METHOD : str = None
    VECTOR_DB_PGVEC_INDEX_THRESHOLD: int = 100

    PRIMARY_LANG:str = "en"
    DEFAULT_LANG: str= "en"

    class Config:
        env_file = ".env"




def get_settings() -> Settings:
    return Settings()