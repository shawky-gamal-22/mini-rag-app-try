from .BaseDataModel import BaseDataModel
from .db_schemes import Asset
from .enums.DataBaseEnum import DataBaseEnum
from bson import ObjectId
from sqlalchemy.future import select


class AssetModel(BaseDataModel):
    """
    AssetModel class for managing asset data.
    Inherits from BaseDataModel.
    This class provides methods to interact with asset data in the database.
    """
    
    def __init__(self, db_client: object):
        super().__init__(db_client)
        self.db_client = db_client

    @classmethod
    async def create_instance(cls, db_client: object):
        """
        Factory method to create an instance of ProjectModel.
        
        :param db_client: Database client object.
        :return: Instance of ProjectModel.
        """
        instance = cls(db_client)
        return instance
        

    
    async def create_asset(self, asset: Asset)-> Asset: 
        """
        Create a new asset in the database.
        
        :param asset: Asset object to be created.
        :return: The created asset object.
        """
        async with self.db_client() as session:
            async with session.begin():
                session.add(asset)
            await session.commit()
            await session.refresh(asset)
        return asset 

    async def get_all_project_assets(self, asset_project_id: int, asset_type: str):
        """
        Get all assets for a specific project.
        
        :param project_id: The ID of the project to retrieve assets for.
        :return: A list of Asset objects associated with the project.
        """
        async with self.db_client() as session:
            stmt = select(Asset).where(
                Asset.asset_project_id == asset_project_id,
                Asset.asset_type == asset_type
            )
            result = await session.execute(stmt)
            records = result.scalars().all()
        return records

        

    async def get_asset_record(self, asset_project_id:int, asset_name:str):

        async with self.db_client() as session:
            stmt = select(Asset).where(
                Asset.asset_project_id == asset_project_id,
                Asset.asset_name == asset_name
            )
            result = await session.execute(stmt)
            records = result.scalar_one_or_none()
        return records
