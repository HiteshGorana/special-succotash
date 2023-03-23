import hashlib
import math
from datetime import datetime, timedelta
from itertools import groupby
from typing import Dict, List, Union

import pytz
from app.config.constants import (
    ACTIVE,
    BATCH_SIZE,
    DAY,
    DEBUG,
    DEFAULT_END_HOURS_SHOP,
    DEFAULT_START_HOURS_SHOP,
    DEFAULT_TIMEZONE,
    HOUR,
    INACTIVE,
    NDIGITS,
    NUMBER_OF_DAYS_TO_BE_REMOVED_FROM_TODAY,
    STORE_HOURS_DATA,
    STORE_STATUS_HISTORY,
    STORE_TIMEZONE_DATA,
    WEEK,
)
from fastapi import Request


def get_active_inactive_store_records(
    records: List[Dict[str, any]], record_type: str
) -> List[datetime]:
    """
    Given a list of store records and a record type, return a list of timestamps for
    all records that match the given record type.

    Parameters:
    records (List[Dict[str, any]]): A list of store records containing a "status" and "timestamp_utc" key.
    record_type (str): The record type to filter by.

    Returns:
    List[str]: A list of timestamps for all records that match the given record type.
    """
    return [
        store_history["timestamp_utc"]
        for store_history in records
        if store_history["status"] == record_type
    ]


def filter_records_by_timestamp(
    records: List[Dict[str, any]], timestamp: datetime
) -> List[Dict[str, any]]:
    """
    Given a list of store records and a timestamp, return a list of records that have a "timestamp_utc"
    field greater than the given timestamp.

    Parameters:
    records (List[Dict[str, any]]): A list of store records containing a "timestamp_utc" field.
    timestamp (datetime): The timestamp to filter records by.

    Returns:
    List[Dict[str, any]]: A list of records that have a "timestamp_utc" field greater than the given timestamp.
    """
    return [
        store_status_hour
        for store_status_hour in records
        if timestamp < store_status_hour.get("timestamp_utc")
    ]


def localize_datetime(dt: datetime, timezone_str: str) -> datetime:
    """
    Given a datetime object and a timezone string, return a localized datetime object.

    Parameters:
    dt (datetime): The datetime object to localize.
    timezone_str (str): The timezone string to use for localization.

    Returns:
    datetime: A localized datetime object.
    """
    return pytz.utc.localize(dt).astimezone(pytz.timezone(timezone_str))


async def get_store_hours_data(
    store_id: str, request: Request
) -> List[Dict[str, Union[str, int]]]:
    """
    Given a store ID, return a list of dictionaries containing store hours data for each day of the week.
    If no store hours data is found for the store ID, return a list of default store hours data for each day of the week.

    Parameters:
    store_id (str): The ID of the store to get store hours data for.

    Returns:
    List[Dict[str, Union[str, int]]]: A list of dictionaries containing store hours data for each day of the week.
    """

    store_hours = (
        await request.app.mongodb[STORE_HOURS_DATA]
        .find({"store_id": store_id})
        .to_list(length=None)
    )

    if not store_hours:
        store_hours = [
            {
                "day": i,
                "start_time_local": DEFAULT_START_HOURS_SHOP,
                "end_time_local": DEFAULT_END_HOURS_SHOP,
            }
            for i in range(7)
        ]

    # uniques
    store_hours = [
        dict(store_hour_tuple)
        for store_hour_tuple in set(
            tuple(store_hour.items())
            for store_hour in store_hours
            if not all(
                val == list(store_hour.values())[0] for val in store_hour.values()
            )
        )
    ]

    return store_hours


def total_seconds_between_datetimes(datetimes: List[datetime]) -> float:
    """
    Calculates the total time difference in seconds between each consecutive pair of datetime objects in a list.

    Args:
        datetimes: A list of datetime objects.

    Returns:
        The total time difference in seconds between each consecutive pair of datetime objects in the input list.
    """
    total_seconds: float = 0.0
    for i in range(len(datetimes) - 1):
        total_seconds += (datetimes[i + 1] - datetimes[i]).total_seconds()
    return total_seconds


def calculate_uptime_downtime(
    store_active_last_hour: List[datetime],
    store_inactive_last_hour: List[datetime],
    store_active_last_day: List[datetime],
    store_inactive_last_day: List[datetime],
    store_active_last_week: List[datetime],
    store_inactive_last_week: List[datetime],
) -> Dict[str, float]:
    """
    Calculates the uptime and downtime durations for a store over the last hour, day, and week.

    Parameters:
    -----------
    store_active_last_hour: List[datetime]
        A list of datetime objects representing the times when the store was active during the last hour.
    store_inactive_last_hour: List[datetime]
        A list of datetime objects representing the times when the store was inactive during the last hour.
    store_active_last_day: List[datetime]
        A list of datetime objects representing the times when the store was active during the last day.
    store_inactive_last_day: List[datetime]
        A list of datetime objects representing the times when the store was inactive during the last day.
    store_active_last_week: List[datetime]
        A list of datetime objects representing the times when the store was active during the last week.
    store_inactive_last_week: List[datetime]
        A list of datetime objects representing the times when the store was inactive during the last week.

    Returns:
    A dictionary with uptime and downtime information
    --------
    """
    uptime_last_hour = total_seconds_between_datetimes(store_active_last_hour)
    downtime_last_hour = total_seconds_between_datetimes(store_inactive_last_hour)
    uptime_last_day = total_seconds_between_datetimes(store_active_last_day)
    downtime_last_day = total_seconds_between_datetimes(store_inactive_last_day)
    uptime_last_week = total_seconds_between_datetimes(store_active_last_week)
    downtime_last_week = total_seconds_between_datetimes(store_inactive_last_week)
    return dict(
        uptime_last_hour=uptime_last_hour,
        downtime_last_hour=downtime_last_hour,
        uptime_last_day=uptime_last_day,
        downtime_last_day=downtime_last_day,
        uptime_last_week=uptime_last_week,
        downtime_last_week=downtime_last_week,
    )


def get_uptime_downtime_pipeline(
    store_id: int,
    end_date_week_tz: datetime,
    start_date_tz: datetime,
    store_hours: List[Dict[str, Union[str, int]]],
) -> List[Dict[str, Union[str, int]]]:
    uptime_downtime_pipeline = [
        {
            "$match": {
                "store_id": store_id,
                "timestamp_utc": {
                    "$gte": end_date_week_tz,
                    "$lt": start_date_tz,
                },
            }
        },
        {
            "$addFields": {
                "weekday": {"$subtract": [{"$dayOfWeek": "$timestamp_utc"}, 1]},
                "time": {
                    "$dateToString": {
                        "format": "%H:%M:%S",
                        "date": "$timestamp_utc",
                    }
                },
            }
        },
        {
            "$addFields": {
                "filter": {
                    "$switch": {
                        "branches": [
                            {
                                "case": {
                                    "$and": [
                                        {
                                            "$eq": [
                                                "$weekday",
                                                store_hour.get("day"),
                                            ]
                                        },
                                        {
                                            "$gte": [
                                                "$time",
                                                store_hour.get("start_time_local"),
                                            ]
                                        },
                                        {
                                            "$lt": [
                                                "$time",
                                                store_hour.get("end_time_local"),
                                            ]
                                        },
                                    ]
                                },
                                "then": hashlib.md5(
                                    f'{store_hour.get("day")}_{store_hour.get("start_time_local")}_{store_hour.get("end_time_local")}'.encode(
                                        "utf-8"
                                    )
                                ).hexdigest(),
                            }
                            for store_hour in store_hours
                        ],
                        "default": False,
                    }
                }
            }
        },
        {
            "$match": {
                "filter": {"$ne": False},
            }
        },
        {"$sort": {"timestamp_utc": 1}},
    ]

    return uptime_downtime_pipeline


async def trigger_report_generation(report_id: str, request: Request):
    start_date = datetime.utcnow() - timedelta(
        days=NUMBER_OF_DAYS_TO_BE_REMOVED_FROM_TODAY
    )
    end_date_hour = start_date - timedelta(hours=HOUR)
    end_date_day = start_date - timedelta(days=DAY)
    end_date_week = start_date - timedelta(days=WEEK)
    report_collection_name = f"report_id_{report_id}"
    total_docs_in_store_timezone_data = await request.app.mongodb[
        STORE_TIMEZONE_DATA
    ].count_documents({})
    if DEBUG:
        total_docs_in_store_timezone_data = 10
    num_batches = math.ceil(total_docs_in_store_timezone_data / BATCH_SIZE)
    for i in range(num_batches):
        start_idx = i * BATCH_SIZE
        end_idx = min((i + 1) * BATCH_SIZE, total_docs_in_store_timezone_data)
        docs = (
            request.app.mongodb[STORE_TIMEZONE_DATA]
            .find()
            .skip(start_idx)
            .limit(BATCH_SIZE)
        )
        async for doc in docs:
            store_id: int = doc.get("store_id")
            timezone_str: str = doc.get("timezone_str", DEFAULT_TIMEZONE)
            start_date_tz: datetime = localize_datetime(start_date, timezone_str)
            end_date_week_tz: datetime = localize_datetime(end_date_week, timezone_str)
            end_date_day_tz: datetime = localize_datetime(end_date_day, timezone_str)
            end_date_hour_tz: datetime = localize_datetime(end_date_hour, timezone_str)
            day_tz_compare: datetime = end_date_day_tz.astimezone(pytz.utc).replace(
                tzinfo=None
            )
            hour_tz_compare: datetime = end_date_hour_tz.astimezone(pytz.utc).replace(
                tzinfo=None
            )
            store_hours: List[Dict[str, Union[str, int]]] = await get_store_hours_data(
                store_id=store_id, request=request
            )
            uptime_downtime_pipeline = get_uptime_downtime_pipeline(
                store_id=store_id,
                end_date_week_tz=end_date_week_tz,
                start_date_tz=start_date_tz,
                store_hours=store_hours,
            )
            store_status_history = request.app.mongodb[STORE_STATUS_HISTORY].aggregate(
                uptime_downtime_pipeline
            )
            store_status_history_week = await store_status_history.to_list(length=None)
            uptime_last_hour: float = 0
            uptime_last_week: float = 0
            downtime_last_hour: float = 0
            uptime_last_day: float = 0
            downtime_last_day: float = 0
            downtime_last_week: float = 0
            for group_k, group_values in groupby(
                store_status_history_week, key=lambda x: x["filter"]
            ):
                history_records = list(group_values)
                store_status_history_hour: List[
                    Dict[str, any]
                ] = filter_records_by_timestamp(history_records, hour_tz_compare)
                store_status_history_day: List[
                    Dict[str, any]
                ] = filter_records_by_timestamp(history_records, day_tz_compare)

                store_active_last_hour: List[
                    datetime
                ] = get_active_inactive_store_records(store_status_history_hour, ACTIVE)

                store_inactive_last_hour: List[
                    datetime
                ] = get_active_inactive_store_records(
                    store_status_history_hour, INACTIVE
                )
                store_active_last_day: List[
                    datetime
                ] = get_active_inactive_store_records(store_status_history_day, ACTIVE)

                store_inactive_last_day: List[
                    datetime
                ] = get_active_inactive_store_records(
                    store_status_history_day, INACTIVE
                )

                store_active_last_week: List[
                    datetime
                ] = get_active_inactive_store_records(history_records, ACTIVE)

                store_inactive_last_week: List[
                    datetime
                ] = get_active_inactive_store_records(history_records, INACTIVE)
                uptime_downtime_data: Dict[str, float] = calculate_uptime_downtime(
                    store_active_last_hour=store_active_last_hour,
                    store_inactive_last_hour=store_inactive_last_hour,
                    store_active_last_day=store_active_last_day,
                    store_inactive_last_day=store_inactive_last_day,
                    store_active_last_week=store_active_last_week,
                    store_inactive_last_week=store_inactive_last_week,
                )
                uptime_last_hour += uptime_downtime_data.get("uptime_last_hour", 0.0)
                downtime_last_hour += uptime_downtime_data.get(
                    "downtime_last_hour", 0.0
                )
                uptime_last_day += uptime_downtime_data.get("uptime_last_day", 0.0)
                downtime_last_day += uptime_downtime_data.get("downtime_last_day", 0.0)
                uptime_last_week += uptime_downtime_data.get("uptime_last_week", 0.0)
                downtime_last_week += uptime_downtime_data.get(
                    "downtime_last_week", 0.0
                )

            report_data = {
                "store_id": store_id,
                "uptime_last_hour": round(uptime_last_hour / 60, NDIGITS),
                "uptime_last_day": round(uptime_last_day / 3600, NDIGITS),
                "uptime_last_week": round(uptime_last_week / 3600, NDIGITS),
                "downtime_last_hour": round(downtime_last_hour / 60, NDIGITS),
                "downtime_last_day": round(downtime_last_day / 3600, NDIGITS),
                "downtime_last_week": round(downtime_last_week / 3600, NDIGITS),
            }
            await request.app.mongodb[report_collection_name].insert_one(report_data)
        percentage_completed = math.ceil(
            (end_idx / total_docs_in_store_timezone_data) * 100
        )
        await request.app.redis.set(report_id, percentage_completed)
