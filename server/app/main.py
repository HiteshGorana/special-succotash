import asyncio
import uuid
from io import StringIO
from os.path import dirname, join

import aioredis
import pandas as pd
from app.config.constants import (
    IMPORT_CSV_TO_MONGODB,
    MONGO_DATABASE,
    MONGO_HOST,
    MONGO_PORT,
    REDIS_HOST,
    REDIS_PORT,
    WEBSOCKET_HOST,
)
from app.models.report import Report
from app.controller.report import trigger_report_generation
from app.utils.logger import logger
from app.utils.upload import upload_files
from fastapi import BackgroundTasks, FastAPI, Request, WebSocket
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates
from motor.motor_asyncio import AsyncIOMotorClient

app = FastAPI()


templates = Jinja2Templates(
    directory=join(dirname(__file__), "templates"), autoescape=False, auto_reload=True
)


@app.on_event("startup")
async def startup():
    # Set up logging
    app.logger = logger
    # Connect to MongoDB
    app.mongodb_client = AsyncIOMotorClient(f"mongodb://{MONGO_HOST}:{MONGO_PORT}")
    app.mongodb = app.mongodb_client[MONGO_DATABASE]

    # Connect to Redis
    app.redis = await aioredis.from_url(f"redis://{REDIS_HOST}:{REDIS_PORT}")
    if IMPORT_CSV_TO_MONGODB:
        app.logger.info("*********** Uploading ... ***********")
        await upload_files(app=app)
        app.logger.info("*********** Completed ***********")
    for name in await app.mongodb.list_collection_names():
        if name.startswith("report_id_"):
            app.logger.info(f"removing report : {name}")
            await app.mongodb.drop_collection(name)
            await app.redis.delete(name.replace("report_id_", ""))


@app.on_event("shutdown")
async def shutdown():
    # Close MongoDB connection
    app.mongodb_client.close()

    # Close Redis connection
    await app.redis.close()


@app.get("/trigger_report", response_model=Report)
async def trigger_report(request: Request, background_tasks: BackgroundTasks) -> Report:
    """
    Trigger the generation of a report asynchronously.

    Parameters:
    - request (Request): the request object.
    - background_tasks (BackgroundTasks): the background tasks object.

    Returns:
    - A Report object containing a unique report ID.
    """
    report_id = str(uuid.uuid4())
    await request.app.redis.set(report_id, 0)
    background_tasks.add_task(
        trigger_report_generation, report_id=report_id, request=request
    )
    return Report(report_id=report_id)


@app.get("/get_report/{report_id}")
async def get_report(request: Request, report_id: str):
    """
    Returns a CSV report file if the report is ready, otherwise shows a progress page or an invalid report page.

    Args:
        request (Request): The incoming request.
        report_id (str): The ID of the report to retrieve.

    Returns:
        A StreamingResponse containing the CSV file if the report is ready,
        or a TemplateResponse for the progress or invalid report page.
    """

    value = await request.app.redis.get(report_id)
    if not value:
        return templates.TemplateResponse(
            "invalid_report.html", {"request": request, "report_id": report_id}
        )
    elif value == b"100":
        await asyncio.sleep(1)
        report_collection_name = f"report_id_{report_id}"
        cursor = request.app.mongodb[report_collection_name].find({}, {"_id": 0})
        df = pd.DataFrame(await cursor.to_list(length=None))
        csv_data = df.to_csv(index=False)
        # Use StreamingResponse to send the CSV data as a stream
        stream = StringIO(csv_data)
        response = StreamingResponse(stream, media_type="text/csv")
        response.headers[
            "Content-Disposition"
        ] = f"attachment; filename=report_id_{report_id}.csv"
        return response
    return templates.TemplateResponse(
        "progress.html",
        {"request": request, "report_id": report_id, "websocket_host": WEBSOCKET_HOST},
    )


@app.websocket("/ws/{report_id}")
async def websocket_endpoint(websocket: WebSocket, report_id: str):
    """
    WebSocket endpoint for reporting progress on the report generation.

    Args:
        websocket (WebSocket): The WebSocket instance for the connection.
        report_id (str): The ID of the report being generated.

    Returns:
        None
    """
    # http://api.localhost/get_report/4b20295b-a4d3-43ed-ab3c-e7d724483460
    await websocket.accept()
    value = b"0"
    while value != b"100":
        await asyncio.sleep(1)
        value = await app.redis.get(report_id)
        await websocket.send_text(value.decode("utf-8"))
    await websocket.close()
    return
