import pandas as pd
from app.config.constants import STORE_MONITOR_DATA


async def upload_files(app):
    """
    Uploads CSV files to a MongoDB database.

    Args:
        app (FastAPI): The FastAPI instance to use for the upload.

    Returns:
        None
    """
    mongodb_collections = await app.mongodb.list_collection_names()
    for collection, csv_file in STORE_MONITOR_DATA.items():
        df = pd.read_csv(csv_file)
        app.logger.info(f"COLLECTION  : {collection}")
        if collection in mongodb_collections:
            # reset data in collection
            app.mongodb[collection].drop()
        if collection == "store_status_history":
            df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"])
        data = df.to_dict(orient="records")
        await app.mongodb[collection].insert_many(data)
