from fastapi import FastAPI, APIRouter, Depends, UploadFile, status, Request
from fastapi.responses import JSONResponse
import os
from helpers.config import get_settings, Settings
#from controllers.DataController import DataController
from controllers import DataController, ProjectController, ProcessController # i have imported the datacontroller in the __init_.py file in the controllers folder so i can import it like this
import aiofiles
from models import ResponseSignal
import logging 
from .schemes.data import ProcessRequest
from models.ProjectModel import ProjectModel
from models.ChunkModel import ChunkModel
from models.db_schemes import DataChunk, Asset
from models.AssetModel import AssetModel
from models.enums.AssetTypeEnum import AssetTypeEnum
from bson import ObjectId


logger = logging.getLogger("uvicorn.error")



data_router=APIRouter(
    prefix="/api/v1/data",
    tags=["api_v1", "data"],
)


@data_router.post("/upload/{project_id}")
async def upload_data(request:Request, project_id: str, file: UploadFile,
                      app_settings: Settings = Depends(get_settings)):

    project_model = await ProjectModel.create_instance(request.app.db_client) # get the project model from the request app's db_client

    project = await project_model.get_project_or_create_one(
        project_id=project_id
    )

    data_controller = DataController()
    
    # valdate the file properties --> it is a logic then we will implement it in the controller folder
    is_valid, result_signal = data_controller.validate_uploaded_file(file)
    

    if not is_valid:
        return JSONResponse(
            status_code= status.HTTP_400_BAD_REQUEST,
            content={
                "message": result_signal.value,
            }
        )

    # get the project path
    project_dir_path = ProjectController().get_project_path(project_id)
    file_path, file_id = data_controller.generate_unique_filepath(file.filename, project_id)

    try:
        async with aiofiles.open(file_path, 'wb') as f:
            while chunk := await file.read(app_settings.FILE_DEFAULT_CHUNK_SIZE):
                await f.write(chunk)

    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "message": ResponseSignal.FILE_UPLOAD_FAILED.value,
            }
        )
    
    # create an asset record in the database
    asset_model = await AssetModel.create_instance(request.app.db_client)
    asset_resource = Asset(
        asset_project_id= project.id,
        asset_type= AssetTypeEnum.FILE.value,
        asset_name= file_id,
        asset_size= os.path.getsize(file_path)
    )

    asset_record = await asset_model.create_asset(asset_resource)
    logger.info(f"File {file.filename} uploaded successfully to {file_path}")

    return JSONResponse(
        content={
            "message": ResponseSignal.FILE_UPLOADED_SUCCESS.value,
            "file_id": str(asset_record.id)
        }
    )

# this is the endpoint to process the file and save the chunks to the database
# it will be called after the file is uploaded successfully
@data_router.post("/process/{project_id}")
async def process_data(req:Request,project_id: str, request: ProcessRequest):
    
    chunk_size = request.chunk_size
    overlap_size = request.overlap_size
    do_reset = request.do_reset


    project_model = await ProjectModel.create_instance(req.app.db_client) # get the project model from the request app's db_client

    project = await project_model.get_project_or_create_one(
        project_id=project_id
    )
    asset_model = await AssetModel.create_instance(req.app.db_client)

    project_files_ids = {}

    if request.file_id:
        asset_record = await asset_model.get_asset_record(
            asset_project_id=project.id,
            asset_name=request.file_id
        )
        if asset_record is None:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "signal": ResponseSignal.FILE_NOT_FOUND.value,
                }
            )
        project_files_ids = {asset_record.id: asset_record.asset_name}
    else:
        # get all the assets for the project
        
        project_files = await asset_model.get_all_project_assets(
            asset_project_id=project.id,
            asset_type=AssetTypeEnum.FILE.value
        )

        project_files_ids= {record.id:record.asset_name for record in project_files}

    if len(project_files_ids) == 0:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignal.NO_FILES_FOUND.value,
            }
        )

    process_controller = ProcessController(project_id)


    no_of_recoreds = 0
    no_files = 0
    chunk_model = await ChunkModel.create_instance(req.app.db_client)

    if do_reset == 1 :
        # delete all the chunks for the project if do_reset is set to 1 and if the project exists
        no_of_deleted_chunks = await chunk_model.delete_chunks_by_project_id(
            project_id=project.id
        )
        logger.info(f"Deleted {no_of_deleted_chunks} chunks for project {project_id}")

    for asset_id, file_id in project_files_ids.items():
        file_content = process_controller.get_file_content(file_id)

        if file_content is None or len(file_content) == 0:
            logger.error(f"File {file_id} is empty or not found.")
            continue

        file_chunks = process_controller.process_file_content(
            file_content=file_content,
            file_id=file_id,
            chunk_size=chunk_size,
            overlap=overlap_size
        )

        
        if file_chunks is None or len(file_chunks) == 0:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "message": ResponseSignal.PROCESSING_FAILED.value,
                }
            )
        
        # save the chunks to the database
        file_chunks_records = [
            DataChunk(
                chunk_text = chunk.page_content,
                chunk_meatadata= chunk.metadata,
                chunk_order = i+1, 
                chunk_project_id= project.id,
                chunk_asset_id= asset_id
            )
            for i, chunk in enumerate(file_chunks)
            ]


        
        
        no_of_recoreds += await chunk_model.insert_many_chunks(
            chunks=file_chunks_records,
        )
        no_files += 1

    return JSONResponse(
        content={
            "message": ResponseSignal.PROCESSING_SUCCESS.value,
            "inserted_chunks": no_of_recoreds,
            "processed_files": no_files,
        }
    )

# stateless applications you do not save any data.
# statefull applications you save data in the database or in the file system.

