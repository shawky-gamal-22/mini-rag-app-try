from enum import Enum

class ResponseSignal(Enum):

    FILE_TYPE_NOT_ALLOWED = "file type not allowed"
    FILE_SIZE_EXCEEDS_LIMIT = "file size exceeds the maximum limit"
    FILE_UPLOADED_SUCCESS = "file uploaded successfully"
    FILE_UPLOADED_FAILED = "file upload failed"
    FILE_VALIDATED_SUCCESS = "file validated successfully"
    FILE_VALIDATED_FAILED = "file validation failed"
    PROCESSING_SUCCESS = "file processed successfully"
    PROCESSING_FAILED = "file processing failed"
    NO_FILES_FOUND="No files found for the project"
    FILE_NOT_FOUND = "file not found"
    PROJECT_NOT_FOUND_ERROR = "project_not_found"
    INSERT_INTO_VECTORDB_ERROR = "insertion error into vectordb"
    INSERT_INTO_VECTORDB_SUCCES = "insert into vectordb success"
    VECTORDB_COLLECTION_RETRIEVED = "vectordb_collection_retrieved"
    VECTORDB_SEARCH_ERROR = "vectordb_search_error"
    VECTORDB_SEARCH_SUCCESS= "vectordb_search_success"
    RAG_ANSWER_SUCCESS= "rag_answer_succes"
    RAG_ANSWER_ERROR = "rag_answer_errpr"