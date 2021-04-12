#!/usr/bin/python3
# -*- coding:utf-8 -*-
# Project: http://cloudedbats.org, https://github.com/cloudedbats
# Copyright (c) 2020-present Arnold Andreasson
# License: MIT License (see LICENSE.txt or http://opensource.org/licenses/mit).

import time
import datetime
import asyncio
import fastapi
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import websockets.exceptions


import sqlite3
import pandas
import io

from starlette.middleware.wsgi import WSGIMiddleware

# CloudedBats.
import wurb_rec

app = fastapi.FastAPI(
    title="CloudedBats WURB 2020",
    description="CloudedBats WURB 2020 - a part of CloudedBats.org.",
    version=wurb_rec.__version__,
)

app.mount("/static", StaticFiles(directory="wurb_rec/static"), name="static")

templates = Jinja2Templates(directory="wurb_rec/templates")

# CloudedBats.
wurb_rec_manager = None

# Schemas.
class LocationSettings(BaseModel):
    geo_source: str = None
    latitude_dd: float = None
    longitude_dd: float = None
    manual_latitude_dd: float = None
    manual_longitude_dd: float = None


class DetectorSettings(BaseModel):
    rec_mode: str = None
    file_directory: str = None
    file_directory_date_option: str = None
    filename_prefix: str = None
    detection_limit_khz: float = None
    detection_sensitivity_dbfs: float = None
    detection_algorithm: str = None
    classification_algorithm: str = None
    rec_length_s: str = None
    rec_type: str = None
    feedback_on_off: str = None
    feedback_volume: float = None
    feedback_pitch: float = None
    feedback_filter_low_khz: float = None
    feedback_filter_high_khz: float = None
    startup_option: str = None
    scheduler_start_event: str = None
    scheduler_start_adjust: float = None
    scheduler_stop_event: str = None
    scheduler_stop_adjust: float = None
    scheduler_post_action: str = None
    scheduler_post_action_delay: float = None


@app.get("/get_bat_data_as_file/")
async def bat_data_as_file():
    query = "SELECT * FROM audiofiles"
    global wurb_rec_manager

    c = await wurb_rec_manager.wurb_database.get_cursor()
    if c is not None:
        c.execute(query)
        data = c.fetchall()
        df = pandas.DataFrame(data, columns = [i[0] for i in c.description])
        stream = io.StringIO()
        df.to_csv(stream, index = False)

        response = StreamingResponse(iter([stream.getvalue()]),
                            media_type="text/csv")
        response.headers["Content-Disposition"] = "attachment; filename=export.csv"
        return response

    else:
        return 0

@app.get("/get_all_bat_data/")
async def all_bat_data():
    query = "SELECT * FROM audiofiles"
    global wurb_rec_manager
    c = await wurb_rec_manager.wurb_database.get_cursor()
    if c is not None:
        result = c.execute(query)
        bat_data = [dict(zip([key[0] for key in c.description], row)) for row in result]

        return bat_data
    else:
        return 0

@app.on_event("startup")
async def startup_event():
    """ """
    try:
        global wurb_rec_manager
        await wurb_rec_manager.startup()
        # Logging debug.
        wurb_rec_manager.wurb_logging.debug(message="API called: startup.")
    except Exception as e:
        # Logging error.
        message = "Called: startup: " + str(e)
        wurb_rec_manager.wurb_logging.error(message, short_message=message)


@app.on_event("shutdown")
async def shutdown_event():
    """ """
    try:
        global wurb_rec_manager
        # Logging debug.
        wurb_rec_manager.wurb_logging.debug(message="API called: shutdown.")
        await wurb_rec_manager.shutdown()
    except Exception as e:
        # Logging error.
        message = "Called: shutdown: " + str(e)
        wurb_rec_manager.wurb_logging.error(message, short_message=message)


@app.get("/")
async def webpage(request: fastapi.Request):
    try:
        global wurb_rec_manager
        # Logging debug.
        wurb_rec_manager.wurb_logging.debug(message="API called: webpage.")
        status_dict = await wurb_rec_manager.get_status_dict()
        location_status = wurb_rec_manager.wurb_settings.get_location_status()
        return templates.TemplateResponse(
            "wurb_rec_web.html",
            {
                "request": request,
                "rec_status": status_dict.get("rec_status", ""),
                "location_status": location_status,
                "device_name": status_dict.get("device_name", ""),
                "detector_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "wurb_version": wurb_rec.__version__,
            },
        )
    except Exception as e:
        # Logging error.
        message = "Called: webpage: " + str(e)
        wurb_rec_manager.wurb_logging.error(message, short_message=message)


@app.get("/start-rec/")
async def start_recording():
    try:
        global wurb_rec_manager
        # Logging debug.
        wurb_rec_manager.wurb_logging.debug(message="API called: start-rec.")
        await wurb_rec_manager.start_rec()
    except Exception as e:
        # Logging error.
        message = "Called: start_rec: " + str(e)
        wurb_rec_manager.wurb_logging.error(message, short_message=message)


@app.get("/stop-rec/")
async def stop_recording():
    try:
        global wurb_rec_manager
        # Logging debug.
        wurb_rec_manager.wurb_logging.debug(message="API called: stop-rec.")
        await wurb_rec_manager.stop_rec()
    except Exception as e:
        # Logging error.
        message = "Called: stop_rec: " + str(e)
        wurb_rec_manager.wurb_logging.error(message, short_message=message)


@app.get("/get-status/")
async def get_status():
    try:
        global wurb_rec_manager
        # Logging debug.
        wurb_rec_manager.wurb_logging.debug(message="API called: get-status.")
        status_dict = await wurb_rec_manager.get_status_dict()
        location_status = wurb_rec_manager.wurb_settings.get_location_status()
        return {
            "rec_status": status_dict.get("rec_status", ""),
            "location_status": location_status,
            "device_name": status_dict.get("device_name", ""),
            "detector_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
    except Exception as e:
        # Logging error.
        message = "Called: get_status: " + str(e)
        wurb_rec_manager.wurb_logging.error(message, short_message=message)


@app.post("/save-location/")
async def save_location(settings: LocationSettings):
    try:
        global wurb_rec_manager
        # Logging debug.
        wurb_rec_manager.wurb_logging.debug(message="API called: save-location.")
        await wurb_rec_manager.wurb_settings.save_location(settings.dict())
        await wurb_rec_manager.wurb_metadata.update_location(settings.dict())
    except Exception as e:
        # Logging error.
        message = "Called: save_location: " + str(e)
        wurb_rec_manager.wurb_logging.error(message, short_message=message)


@app.get("/get-location/")
async def get_location(default: bool = False):
    try:
        global wurb_rec_manager
        # Logging debug.
        wurb_rec_manager.wurb_logging.debug(message="API called: get-location.")
        current_location_dict = await wurb_rec_manager.wurb_settings.get_location()
        return current_location_dict
    except Exception as e:
        # Logging error.
        message = "Called: get_location: " + str(e)
        wurb_rec_manager.wurb_logging.error(message, short_message=message)


@app.get("/set-time/")
async def set_time(posixtime: str):
    try:
        global wurb_rec_manager
        # Logging debug.
        message = "API called: set-time: " + str(posixtime)
        wurb_rec_manager.wurb_logging.debug(message=message)
        posix_time_s = int(int(posixtime) / 1000)
        await wurb_rec_manager.wurb_rpi.set_detector_time(
            posix_time_s, cmd_source="by user"
        )
    except Exception as e:
        # Logging error.
        message = "Called: set_time: " + str(e)
        wurb_rec_manager.wurb_logging.error(message, short_message=message)


@app.get("/save-rec-mode/")
async def save_rec_mode(recmode: str):
    try:
        global wurb_rec_manager
        # Logging debug.
        wurb_rec_manager.wurb_logging.debug(message="API called: save-rec-mode.")
        await wurb_rec_manager.wurb_settings.save_rec_mode(recmode)
    except Exception as e:
        # Logging error.
        message = "Called: save_rec_mode: " + str(e)
        wurb_rec_manager.wurb_logging.error(message, short_message=message)


@app.post("/save-settings/")
async def save_settings(settings: DetectorSettings):
    try:
        global wurb_rec_manager
        # Logging debug.
        wurb_rec_manager.wurb_logging.debug(message="API called: save-settings.")
        await wurb_rec_manager.wurb_settings.save_settings(settings.dict())
    except Exception as e:
        # Logging error.
        message = "Called: save_settings: " + str(e)
        wurb_rec_manager.wurb_logging.error(message, short_message=message)


@app.post("/save-settings-user/")
async def save_settings_user(settings: DetectorSettings):
    try:
        global wurb_rec_manager
        # Logging debug.
        wurb_rec_manager.wurb_logging.debug(message="API called: save-settings-user.")
        await wurb_rec_manager.wurb_settings.save_settings(
            settings.dict(), settings_type="user-default"
        )
    except Exception as e:
        # Logging error.
        message = "Called: save-settings-user: " + str(e)
        wurb_rec_manager.wurb_logging.error(message, short_message=message)


@app.post("/save-settings-startup/")
async def save_settings_startup(settings: DetectorSettings):
    try:
        global wurb_rec_manager
        # Logging debug.
        wurb_rec_manager.wurb_logging.debug(
            message="API called: save-settings-startup."
        )
        await wurb_rec_manager.wurb_settings.save_settings(
            settings.dict(), settings_type="startup"
        )
    except Exception as e:
        # Logging error.
        message = "Called: save-settings-startup: " + str(e)
        wurb_rec_manager.wurb_logging.error(message, short_message=message)


@app.get("/get-settings/")
async def get_settings(default: bool = False):
    try:
        global wurb_rec_manager
        # Logging debug.
        wurb_rec_manager.wurb_logging.debug(message="API called: get-settings.")
        current_settings_dict = await wurb_rec_manager.wurb_settings.get_settings(
            default
        )
        return current_settings_dict
    except Exception as e:
        # Logging error.
        message = "Called: get_settings: " + str(e)
        wurb_rec_manager.wurb_logging.error(message, short_message=message)


@app.get("/load-settings/")
async def load_settings(settings_type: str):
    try:
        global wurb_rec_manager
        # Logging debug.
        wurb_rec_manager.wurb_logging.debug(message="API called: load-settings.")
        await wurb_rec_manager.wurb_settings.load_settings(settings_type)
    except Exception as e:
        # Logging error.
        message = "Called: load_settings: " + str(e)
        wurb_rec_manager.wurb_logging.error(message, short_message=message)


@app.get("/rpi-control/")
async def rpi_control(command: str):
    try:
        global wurb_rec_manager
        # Logging debug.
        message = "API called: rpi-control:" + command + "."
        wurb_rec_manager.wurb_logging.debug(message=message)
        await wurb_rec_manager.wurb_rpi.rpi_control(command)
    except Exception as e:
        # Logging error.
        message = "Called: rpi_control: " + str(e)
        wurb_rec_manager.wurb_logging.error(message, short_message=message)


@app.get("/rec-manual-trigger/")
async def rec_manual_trigger():
    try:
        global wurb_rec_manager
        # Logging debug.
        message = "API called: manual-trigger."
        wurb_rec_manager.wurb_logging.debug(message=message)
        await wurb_rec_manager.manual_trigger()
    except Exception as e:
        # Logging error.
        message = "Called: rec_manual_trigger: " + str(e)
        wurb_rec_manager.wurb_logging.error(message, short_message=message)


@app.get("/set-audio-feedback/")
async def set_audio_feedback(volume: str, pitch: str):
    try:
        global wurb_rec_manager
        # Logging debug.
        message = "API called: set-audio-feedback."
        wurb_rec_manager.wurb_logging.debug(message=message)
        await wurb_rec_manager.wurb_settings.set_audio_feedback(volume, pitch)
    except Exception as e:
        # Logging error.
        message = "Called: set_audio_feedback: " + str(e)
        wurb_rec_manager.wurb_logging.error(message, short_message=message)


@app.websocket("/ws")
async def websocket_endpoint(websocket: fastapi.WebSocket):
    try:
        global wurb_rec_manager
        # Logging debug.
        wurb_rec_manager.wurb_logging.debug(message="API Websocket initiated.")
        #
        wurb_settings = wurb_rec_manager.wurb_settings
        wurb_logging = wurb_rec_manager.wurb_logging
        #
        await websocket.accept()
        #
        # Get event notification objects.
        rec_manager_notification = await wurb_rec_manager.get_notification_event()
        location_changed_notification = await wurb_settings.get_location_event()
        latlong_changed_notification = await wurb_settings.get_latlong_event()
        settings_changed_notification = await wurb_settings.get_settings_event()
        logging_changed_notification = await wurb_logging.get_logging_event()
        bat_detected_notification = await wurb_rec_manager.wurb_recorder.get_bat_detected_event()
        # Update client.
        ws_json = {}
        status_dict = await wurb_rec_manager.get_status_dict()
        location_status = wurb_settings.get_location_status()
        ws_json["status"] = {
            "rec_status": status_dict.get("rec_status", ""),
            "location_status": location_status,
            "device_name": status_dict.get("device_name", ""),
            "detector_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        ws_json["location"] = await wurb_settings.get_location()
        ws_json["latlong"] = await wurb_settings.get_location()
        ws_json["settings"] = await wurb_settings.get_settings()
        ws_json["log_rows"] = await wurb_logging.get_client_messages()
        # Send update to client.
        await websocket.send_json(ws_json)
        # Loop.
        while True:
            # Wait for next event to happen.
            events = [
                asyncio.sleep(1.0),  # Update detector time field each second.
                rec_manager_notification.wait(),
                location_changed_notification.wait(),
                latlong_changed_notification.wait(),
                settings_changed_notification.wait(),
                logging_changed_notification.wait(),
                bat_detected_notification.wait(),
            ]
            await asyncio.wait(events, return_when=asyncio.FIRST_COMPLETED)

            # Prepare message to client.
            ws_json = {}
            status_dict = await wurb_rec_manager.get_status_dict()
            location_status = wurb_settings.get_location_status()
            ws_json["status"] = {
                "rec_status": status_dict.get("rec_status", ""),
                "location_status": location_status,
                "device_name": status_dict.get("device_name", ""),
                "detector_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            rec_manager_notification = await wurb_rec_manager.get_notification_event()
            if location_changed_notification.is_set():
                location_changed_notification = await wurb_settings.get_location_event()
                ws_json["location"] = await wurb_settings.get_location()
            if latlong_changed_notification.is_set():
                latlong_changed_notification = await wurb_settings.get_latlong_event()
                ws_json["latlong"] = await wurb_settings.get_location()
            if settings_changed_notification.is_set():
                settings_changed_notification = await wurb_settings.get_settings_event()
                ws_json["settings"] = await wurb_settings.get_settings()
            if logging_changed_notification.is_set():
                logging_changed_notification = await wurb_logging.get_logging_event()
                ws_json["log_rows"] = await wurb_logging.get_client_messages()

            # update chart data
            if bat_detected_notification.is_set():
                bat_detected_notification = await wurb_rec_manager.wurb_recorder.get_bat_detected_event()
                ws_json["bat_detected"] = await wurb_rec_manager.wurb_recorder.get_bat_data()
            # Send to client.
            await websocket.send_json(ws_json)

    except websockets.exceptions.ConnectionClosed as e:
        pass
    except Exception as e:
        # Logging error.
        message = "Called: websocket_endpoint: " + str(e)
        wurb_rec_manager.wurb_logging.error(message, short_message=None)


# Example:
# @app.get("/items/{item-id}")
# async def read_item(item-id: int, q: str = None, q2: int = None):
#    return {"item-id": item_id, "q": q, "q2": q2}
