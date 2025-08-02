from ..VectorDBInterface import VectorDBInterface
from ..VectorDBEnums import (
    DistanceMethodEnums,
    PgVectorTableSchemaEnums,
    PgVectorDistanceMethodEnums,
    PgVectorIndexTypeEnums
)
from models.db_schemes import RetrievedDocument
import logging
from typing import List, Optional
from sqlalchemy.sql import text as sql_text
import json


class PGVectorProvider(VectorDBInterface):

    def __init__(self, db_client: str, default_vector_size: int = 786,
                  distance_method: str=None, index_threshold=100):
        
        self.db_client = db_client
        self.default_vector_size = default_vector_size
        self.index_threshold = index_threshold


        if distance_method == DistanceMethodEnums.COSINE.value:
            distance_method = PgVectorDistanceMethodEnums.COSINE.value
        elif distance_method == DistanceMethodEnums.DOT.value:
            distance_method = PgVectorDistanceMethodEnums.DOT.value


        self.distance_method = distance_method

        self.pgvector_table_prefix = PgVectorTableSchemaEnums._PREFIX.value

        self.logger = logging.getLogger("uvicorn")

        self.default_index_name = lambda collection_name : f"{collection_name}_vector_idx"


    async def connect(self):
        # Connection logic for PostgreSQL with PGVector
        async with self.db_client() as session:
            async with session.begin():
                await session.execute(
                    sql_text(
                        "CREATE EXTENSION IF NOT EXISTS vector;"
                    )
                )
                await session.commit()
    

    async def disconnect(self):
        # Disconnect logic for PostgreSQL with PGVector
        pass

    async def is_collection_existed(self, collection_name: str) -> bool:
        # Logic to check if a collection exists in PostgreSQL
        # collection_name --> table name
        record = None 
        async with self.db_client() as session:
            async with session.begin():
                list_tbl =  sql_text(
                    f'SELECT * FROM pg_tables WHERE tablename = :collection_name'
                )
                result = await session.execute(list_tbl,{"collection_name":collection_name})
                record = result.scalar_one_or_none()

                return record 
                
        

    async def list_all_collections(self) -> List:
        # Logic to list all collections in PostgreSQL
        records = []
        async with self.db_client() as session:
            async with session.begin():
                list_tbl = sql_text(
                    f'SELECT tablename FROM pg_tables LIKE {self.pgvector_table_prefix}'
                )
                result = await session.execute(list_tbl)
                records = result.scalars().all()
        return records
    
    async def get_collection_info(self, collection_name: str) -> dict:
        # Logic to get collection info from PostgreSQL
        async with self.db_client() as session:
            async with session.begin():
                table_info_sql = sql_text(f'''
                    SELECT schemaname, tablename, tableowner, tablespace, hasindexes
                                          FROM pg_tables
                                          WHERE tablename = :collection_name''')
                count_sql = sql_text(f"SELECT COUNT(*) FROM {collection_name}")
                table_info = await session.execute(table_info_sql,{"collection_name":collection_name})
                record_count = await session.execute(count_sql)

                table_data = table_info.fetchone()
                if not table_data:
                    return None
                return {
                    "table_info": {
                        "schemaname": table_data[0],
                        "tablename": table_data[1],
                        "tableowner": table_data[2],
                        "tablespace": table_data[3],
                        "hasindexes": table_data[4]
                    },
                    "record_count": record_count.scalar_one(),
                }

    async def delete_collection(self, collection_name: str):
        # Logic to delete a collection in PostgreSQL
        async with self.db_client() as session:
            async with session.begin():
                self.logger.info(f"Deleting collection: {collection_name}")
                delete_sql = sql_text(f'DROP TABLE IF EXISTS {collection_name}')
                await session.execute(delete_sql)
                await session.commit()
        return True

    async def create_collection(self, collection_name: str,
                          embedding_size: int,
                          do_reset: bool = False) -> bool:
        # Logic to create a collection in PostgreSQL
        if do_reset:
            _= await self.delete_collection(collection_name)

        is_collection_existed = await self.is_collection_existed(collection_name)
        if not is_collection_existed:
            self.logger.info(f"Creating collection: {collection_name}")
            async with self.db_client() as session:
                async with session.begin():
                    create_sql = sql_text(
                        f'CREATE TABLE {collection_name} ('
                            f'{PgVectorTableSchemaEnums.ID.value} bigserial PRIMARY KEY, '
                            f'{PgVectorTableSchemaEnums.TEXT.value} text, '
                            f'{PgVectorTableSchemaEnums.VECTOR.value} vector({embedding_size}), '
                            f'{PgVectorTableSchemaEnums.METADATA.value} jsonb DEFAULT \'{{}}\', '
                            f'{PgVectorTableSchemaEnums.CHUNK_ID.value} integer, '
                            f'FOREIGN KEY ({PgVectorTableSchemaEnums.CHUNK_ID.value}) REFERENCES chunks(chunk_id)'
                        ')'
                        )
                    await session.execute(create_sql)
                    await session.commit()
            return True

        return False
    

    async def is_index_existed(self, collection_name: str)-> bool:
        index_name = self.default_index_name(collection_name=collection_name)
        async with self.db_client() as session:
            async with session.begin():
                check_sql = sql_text(f"""
                                    
                                    SELECT 1 
                                    FROM pg_indexes
                                    WHERE tablename = :collection_name
                                    AND  indexname = :index_name
                                    """)
                results = await session.execute(check_sql,{
                    "collection_name":collection_name,
                    "index_name":index_name
                })

        return bool(results.scalar_one_or_none())
    

    async def create_vector_index(self, collection_name: str,
                                        index_type: str = PgVectorIndexTypeEnums.HNSW.value):

        is_index_existed = await self.is_index_existed(collection_name=collection_name)

        if is_index_existed :
            return False
        

        async with self.db_client() as session:
            async with session.begin():
                count_sql = sql_text(f"SELECT COUNT(*) FROM {collection_name}")

                result = await session.execute(count_sql)

                records_count = result.scalar_one()

                if records_count < self.index_threshold:
                    return False 
                
                self.logger.info(f"START: Creating vector index for collection: {collection_name}")
                index_name = self.default_index_name(collection_name=collection_name)
                create_idx_sql = sql_text(
                        f'CREATE INDEX {index_name} ON {collection_name} '
                        f'USING {index_type} ({PgVectorTableSchemaEnums.VECTOR.value} {self.distance_method})'
                    )
                
                await session.execute(create_idx_sql)
                await session.commit()

                self.logger.info(f"End: Creating vector index for collection: {collection_name}")
        return True
        
    async def reset_vector_index(self, collection_name: str,
                                    index_type: str =  PgVectorIndexTypeEnums.HNSW.value) -> bool:
                
            
        index_name = self.default_index_name(collection_name=collection_name)
        async with self.db_client() as session:
            async with session.begin():
                drop_sql = sql_text(
                    f'DROP INDEX IF EXISTS {index_name}'
                )
                await session.execute(drop_sql)
        

        return await self.create_vector_index(
            collection_name=collection_name,
            index_type= index_type
        )





    async def insert_one(self, collection_name: str, text: str, vector: list,
                          metadata: dict=None,
                          record_id: str= None): 
        
        is_collection_existed = await self.is_collection_existed(collection_name)
        if not is_collection_existed:
            self.logger.error(f"Can not insert new record to non-existed collection: {collection_name}")
            return False
        
        if not record_id :
            self.logger.error(f"Can not insert new record without record_id: {collection_name}")
            return False
        
        async with self.db_client() as session:
            async with session.begin():
                insert_sql = sql_text(
                    f'INSERT INTO {collection_name}'
                    f'({PgVectorTableSchemaEnums.TEXT.value}, {PgVectorTableSchemaEnums.VECTOR.value}, {PgVectorTableSchemaEnums.METADATA.value}, {PgVectorTableSchemaEnums.CHUNK_ID.value}) '
                    f'VALUES( :text, :vector, :metadata, :chunk_id)'
                )
                metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata is not None else "{}"
                await session.execute(insert_sql,{
                    "text":text,
                    "vector": "[" + ",".join([ str(v) for v in vector]) + "]",
                    "metadata": metadata_json,
                    "chunk_id" : record_id
                })
                await self.create_vector_index(collection_name=collection_name)

                await session.commit()
        return True
    
    async def insert_many(self, collection_name: str, texts: list,
                          vectors: list, metadata: dict=None,
                          record_ids: list= None, batch_size: int= 50):
        
        is_collection_existed = await self.is_collection_existed(collection_name)
        if not is_collection_existed:
            self.logger.error(f"Can not insert new record to non-existed collection: {collection_name}")
            return False
        
        if len(vectors) != len(record_ids):
            self.logger.error(f"Invalid data item for collection: {collection_name}")
            return False
        
        if not metadata or  len(metadata) == 0 :
            metadata = [None]*len(texts)

        async with self.db_client() as session:
            async with session.begin():

                for i in range(0, len(texts), batch_size):
                    batch_texts = texts[i: i+batch_size]
                    batch_vecotrs = vectors[i: i+batch_size]
                    batch_metadata = metadata[i: i+batch_size]
                    batch_record_ids = record_ids[i: i+batch_size]

                    values = []

                    for _text, _vector, _metadata, _record_id in zip(batch_texts,batch_vecotrs,batch_metadata,batch_record_ids):
                        
                        metadata_json = json.dumps(_metadata, ensure_ascii=False) if _metadata is not None else "{}" 
                        values.append({
                            'text': _text,
                            'vector':"[" + ",".join([ str(v) for v in _vector]) + "]",
                            'metadata': metadata_json,
                            'chunk_id': _record_id
                        })

                    batch_insert_sql = sql_text(
                        f'INSERT INTO {collection_name} '
                        f'({PgVectorTableSchemaEnums.TEXT.value}, ' 
                        f'{PgVectorTableSchemaEnums.VECTOR.value}, ' 
                        f'{PgVectorTableSchemaEnums.METADATA.value}, ' 
                        f'{PgVectorTableSchemaEnums.CHUNK_ID.value}) '
                        f'VALUES (:text, :vector, :metadata, :chunk_id)')
                    await session.execute(batch_insert_sql, values)

                    await session.commit()
        await self.create_vector_index(collection_name=collection_name)


        return True
    
    async def search_by_vector(self, collection_name: str, 
                               vector: list, 
                               limit: int) -> List[RetrievedDocument]:

        is_collection_existed = await self.is_collection_existed(collection_name)
        if not is_collection_existed:
            self.logger.error(f"Can not search for record to non-existed collection: {collection_name}")
            return False
        
        vector = "[" + ",".join([ str(v) for v in vector]) + "]"

        async with self.db_client() as session:
            async with session.begin():
                search_sql = sql_text(
                    f'SELECT {PgVectorTableSchemaEnums.TEXT.value} as text, 1 - ({PgVectorTableSchemaEnums.VECTOR.value} <=> :vector) as score'
                    f' FROM {collection_name} '
                    'ORDER BY score DESC '
                    f'LIMIT {limit}'
                )

                result = await session.execute(search_sql, {'vector':vector})

                records = result.fetchall()

                if not records or len(records) ==0 :
                    return None

                return [
                    RetrievedDocument(
                        text = record.text,
                        score = record.score
                    )
                    for record in records
                ]

    





