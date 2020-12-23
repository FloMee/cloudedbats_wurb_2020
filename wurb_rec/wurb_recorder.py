#!/usr/bin/python3
# -*- coding:utf-8 -*-
# Project: http://cloudedbats.org, https://github.com/cloudedbats
# Copyright (c) 2020-present Arnold Andreasson
# License: MIT License (see LICENSE.txt or http://opensource.org/licenses/mit).

import asyncio
import time
import wave
import pathlib
import psutil
from collections import deque
import sounddevice
#import os
import glob
import shutil
import json
import pexpect as p
import sqlite3 as sq3
import guano
import datetime


# CloudedBats.
import wurb_rec


class UltrasoundDevices(object):
    """ """

    def __init__(self, wurb_manager):
        """ """
        self.wurb_manager = wurb_manager
        # Ultrasound microphones supported by default:
        # - Pettersson: M500-384, u384, u256.
        # - Dodotronic: UltraMic 192K, 200K, 250K, 384K.
        self.default_name_part_list = ["Pettersson", "UltraMic"]
        self.device_name = ""
        self.sampling_freq_hz = 0
        self.check_interval_s = 5.0
        self.notification_event = None
        self.recorder_m500 = wurb_rec.WurbRecorderM500()

    async def check_devices(self):
        """ For asyncio events. """
        try:
            # Check default ALSA connected microphones.
            lock = asyncio.Lock()
            async with lock:
                # Refresh device list.
                sounddevice._terminate()
                sounddevice._initialize()
                await asyncio.sleep(0.2)
            #
            await self.set_connected_device("", 0)
            device_dict = None
            device_name = ""
            sampling_freq_hz = 0
            for device_name_part in self.default_name_part_list:
                try:
                    device_dict = sounddevice.query_devices(device=device_name_part)
                    if device_dict:
                        device_name = device_dict["name"]
                        if ":" in device_name:
                            # Extract name only.
                            device_name = device_name.split(":")[0]
                        sampling_freq_hz = int(device_dict["default_samplerate"])
                    break
                except:
                    pass
            # Check if Pettersson M500.
            if not device_name:
                if self.recorder_m500.is_m500_available():
                    device_name = self.recorder_m500.get_device_name()
                    sampling_freq_hz = self.recorder_m500.get_sampling_freq_hz()
            # Check if another ALSA mic. is specified in advanced settings.
            if not device_name:
                settings_device_name_part = "GoMic"  # TODO: From settings.
                settings_sampling_freq_hz = 0  # TODO: From settings.
                # settings_sampling_freq_hz = 44100  # TODO: From settings.
                if settings_device_name_part:
                    device_dict = None
                    device_name = ""
                    sampling_freq_hz = 0
                    try:
                        device_dict = sounddevice.query_devices(
                            device=settings_device_name_part
                        )
                        if device_dict:
                            device_name = device_dict["name"]
                            if ":" in device_name:
                                # Extract name only.
                                device_name = device_name.split(":")[0]
                            if settings_sampling_freq_hz > 0:
                                sampling_freq_hz = settings_sampling_freq_hz
                            else:
                                sampling_freq_hz = int(
                                    device_dict["default_samplerate"]
                                )
                    except:
                        pass
            # Done.
            await self.set_connected_device(device_name, sampling_freq_hz)

        except Exception as e:
            # Logging error.
            message = "Rec. check_devices: " + str(e)
            self.wurb_manager.wurb_logging.error(message, short_message=message)

    async def reset_devices(self):
        """ For asyncio events. """
        try:
            await self.set_connected_device("", 0)

        except Exception as e:
            # Logging error.
            message = "Recorder: reset_devices: " + str(e)
            self.wurb_manager.wurb_logging.error(message, short_message=message)

    async def get_notification_event(self):
        """ """
        try:
            if self.notification_event == None:
                self.notification_event = asyncio.Event()
            return self.notification_event
        except Exception as e:
            # Logging error.
            message = "Recorder: get_notification_event: " + str(e)
            self.wurb_manager.wurb_logging.error(message, short_message=message)

    async def get_connected_device(self):
        """ """
        try:
            return self.device_name, self.sampling_freq_hz
        except Exception as e:
            # Logging error.
            message = "Recorder: get_connected_device: " + str(e)
            self.wurb_manager.wurb_logging.error(message, short_message=message)

    async def set_connected_device(self, device_name, sampling_freq_hz):
        """ """
        try:
            self.device_name = device_name
            self.sampling_freq_hz = sampling_freq_hz
            # Create a new event and release all from the old event.
            old_notification_event = self.notification_event
            self.notification_event = asyncio.Event()
            if old_notification_event:
                old_notification_event.set()
        except Exception as e:
            # Logging error.
            message = "Recorder: set_connected_device: " + str(e)
            self.wurb_manager.wurb_logging.error(message, short_message=message)


class WurbRecorder(wurb_rec.SoundStreamManager):
    """ """

    def __init__(self, wurb_manager, queue_max_size=1200):
        """ """
        super().__init__(queue_max_size)
        self.wurb_manager = wurb_manager
        self.wurb_settings = wurb_manager.wurb_settings
        self.wurb_logging = wurb_manager.wurb_logging
        self.rec_status = ""
        self.device_name = ""
        self.sampling_freq_hz = 0
        self.notification_event = None
        self.rec_start_time = None
        self.restart_activated = False
        # Config.
        self.max_adc_time_diff_s = 10  # Unit: sec.
        self.rec_length_s = 6  # Unit: sec.
        self.rec_timeout_before_restart_s = 30  # Unit: sec.

        self.bat_detected_event = None
        self.bat_data = {}


    async def get_bat_data(self):
        try:            
            return self.bat_data

        except Exception as e:
            messsage = "Recorder: get_bat_data: " +  str(e)
            self.wurb_manager.wurb_logging.error(message, short_message=message)

    async def set_bat_data(self, bat, amount = 1):
        try:
            self.bat_data = {"bat": bat, "amount": amount}
            # Create a new event and release all from the old event.
            old_bat_detected_event = self.bat_detected_event
            self.bat_detected_event = asyncio.Event()
            if old_bat_detected_event:
                old_bat_detected_event.set()

        except Exception as e:
            messsage = "Recorder: set_bat_data: " +  str(e)
            self.wurb_manager.wurb_logging.error(message, short_message=message)
        

    async def get_bat_detected_event(self):
        """"""
        try:
            if self.bat_detected_event == None:
                self.bat_detected_event = asyncio.Event()
            return self.bat_detected_event
        except Exception as e:
            messsage = "Recorder: bat_detected_event: " +  str(e)
            self.wurb_manager.wurb_logging.error(message, short_message=message)

    async def get_notification_event(self):
        """ """
        try:
            if self.notification_event == None:
                self.notification_event = asyncio.Event()
            return self.notification_event
        except Exception as e:
            # Logging error.
            message = "Recorder: get_notification_event: " + str(e)
            self.wurb_manager.wurb_logging.error(message, short_message=message)

    async def get_rec_status(self):
        """ """
        try:
            return self.rec_status
        except Exception as e:
            # Logging error.
            message = "Recorder: get_rec_status: " + str(e)
            self.wurb_manager.wurb_logging.error(message, short_message=message)

    async def set_rec_status(self, rec_status):
        """ """
        try:
            self.rec_status = rec_status
            # Create a new event and release all from the old event.
            old_notification_event = self.notification_event
            self.notification_event = asyncio.Event()
            if old_notification_event:
                old_notification_event.set()
        except Exception as e:
            # Logging error.
            message = "Recorder: set_rec_status: " + str(e)
            self.wurb_manager.wurb_logging.error(message, short_message=message)

    async def set_device(self, device_name, sampling_freq_hz):
        """ """
        try:
            self.device_name = device_name
            self.sampling_freq_hz = sampling_freq_hz
        except Exception as e:
            # Logging error.
            message = "Recorder: set_device: " + str(e)
            self.wurb_manager.wurb_logging.error(message, short_message=message)

    # async def put_on_fromsourcequeue(self, send_dict):
    #     """ """
    #     # Compare real time and stream time.
    #     adc_time = send_dict["adc_time"]
    #     time_now = time.time()
    #     # Restart if it differ too much.
    #     if abs(adc_time - time_now) > self.max_adc_time_diff_s:
    #         # Check if restart already is requested.
    #         if self.restart_activated:
    #             return
    #         # Logging.
    #         message = "Warning: Time diff. detected. Rec. will be restarted."
    #         self.wurb_logging.info(message, short_message=message)
    #         # Restart recording.
    #         self.restart_activated = True
    #         loop = asyncio.get_event_loop()
    #         asyncio.run_coroutine_threadsafe(
    #             self.wurb_manager.restart_rec(), loop,
    #         )
    #         await self.remove_items_from_queue(self.from_source_queue)
    #         await self.from_source_queue.put(False)  # Flush.
    #         return
    #     # Put buffer on queue.
    #     try:
    #         if not self.from_source_queue.full():
    #             await self.from_source_queue.put_nowait(send_dict)
    #         else:
    #             await self.remove_items_from_queue(self.from_source_queue)
    #             await self.from_source_queue.put(False)  # Flush.
    #             print("DEBUG: from_source_queue id FULL. Queues are flushed.")
    #     except QueueFull:
    #         print("EXCEPTION: put_on_queue_from_source: QueueFull.")
    #     except Exception as e:
    #         print("EXCEPTION: put_on_queue_from_source: ", e)

    async def sound_source_worker(self):
        """ Abstract worker method for sound sources. Mainly files or streams.
            Test implementation to be used as template.
        """
        self.rec_start_time = None
        loop = asyncio.get_event_loop()
        sound_source_event = asyncio.Event()
        self.restart_activated = False

        # Use another implementation if Pettersson M500.
        recorder_m500 = wurb_rec.WurbRecorderM500(
            wurb_manager=self.wurb_manager,
            asyncio_loop=loop,
            asyncio_queue=self.from_source_queue,
        )
        if self.device_name == recorder_m500.get_device_name():
            # Logging.
            message = "Recorder: M500 started."
            self.wurb_manager.wurb_logging.info(message, short_message=message)
            await self.set_rec_status("Recording.")
            try:
                await loop.run_in_executor(
                    None, recorder_m500.start_streaming, 
                )            
            except asyncio.CancelledError:
                recorder_m500.stop_streaming()
            except Exception as e:
                # Logging error.
                message = "Recorder: sound_source_worker: " + str(e)
                self.wurb_manager.wurb_logging.error(message, short_message=message)
            finally:
                await self.set_rec_status("Recording finished.")
            return

        # Standard ASLA microphones.
        def audio_callback(indata, frames, cffi_time, status):
            """ Locally defined callback.
                This is called (from a separate thread) for each audio block. """
            try:
                if status:
                    print("DEBUG: audio_callback Status:", status)

                input_buffer_adc_time = cffi_time.inputBufferAdcTime
                if self.rec_start_time == None:
                    # Adjust first buffer.
                    input_buffer_adc_time = input_buffer_adc_time + 0.121
                    self.rec_start_time = time.time() - input_buffer_adc_time
                # Round to half seconds.
                buffer_adc_time = (
                    int((self.rec_start_time + input_buffer_adc_time) * 2) / 2
                )
                # print(
                #     "DEBUG: adc_time: ",
                #     buffer_adc_time,
                #     "   ",
                #     time.strftime("%Y%m%dT%H%M%S%z", time.localtime(buffer_adc_time)),
                # )
                # Convert and copy buffer.
                indata_raw = indata[:, 0]  # Transform list of lists to list.
                indata_copy = indata_raw.copy()
                # Used to check time drift.
                detector_time = time.time()
                # Put together.
                send_dict = {
                    "status": "data",
                    "adc_time": buffer_adc_time,
                    "detector_time": detector_time,
                    "data": indata_copy,
                }
                # Add to queue.
                # Note: Maybe "call_soon_threadsafe" is faster than "run_coroutine_threadsafe".
                try:
                    if not self.from_source_queue.full():
                        loop.call_soon_threadsafe(
                            self.from_source_queue.put_nowait, send_dict
                        )
                except Exception as e:
                    print("DEBUG: Failed to put buffer on queue: ", e)
                    pass

                # # Add to queue. Should be attached to the main async loop.
                # asyncio.run_coroutine_threadsafe(
                #     self.put_on_fromsourcequeue(send_dict), loop,
                # )

            except Exception as e:
                # Logging error.
                message = "Recorder: audio_callback: " + str(e)
                self.wurb_manager.wurb_logging.error(message, short_message=message)
                # Exit recording loop.
                loop.call_soon_threadsafe(sound_source_event.set())

            """ End of locally defined callback. """

        try:
            # print(
            #     "DEBUG: Rec started: ", self.device_name, "   ", self.sampling_freq_hz
            # )
            # time_start = time.time()
            # print(
            #     "DEBUG: Rec start: ",
            #     time_start,
            #     "   ",
            #     time.strftime("%Y%m%dT%H%M%S%z", time.localtime(time_start)),
            # )

            blocksize = int(self.sampling_freq_hz / 2)

            # Start streaming from the microphone.
            stream = sounddevice.InputStream(
                device=self.device_name,
                samplerate=self.sampling_freq_hz,
                channels=1,
                dtype="int16",
                blocksize=blocksize,
                callback=audio_callback,
            )

            await self.set_rec_status("Recording.")

            with stream:
                await sound_source_event.wait()

        except asyncio.CancelledError:
            pass
        except Exception as e:
            # Logging error.
            message = "Recorder: sound_source_worker: " + str(e)
            self.wurb_manager.wurb_logging.error(message, short_message=message)
        finally:
            await self.set_rec_status("Recording finished.")

    async def sound_process_worker(self):
        """ Abstract worker for sound processing algorithms.
            Test implementation to be used as template.
        """

        try:
            # Get rec length from settings.
            self.rec_length_s = int(self.wurb_settings.get_setting("rec_length_s"))
            #
            self.process_deque = deque()  # Double ended queue.
            self.process_deque.clear()
            self.process_deque_length = self.rec_length_s * 2
            self.detection_counter_max = self.process_deque_length - 3  # 1.5 s before.
            #
            first_sound_detected = False
            sound_detected = False
            sound_detected_counter = 0
            sound_detector = wurb_rec.SoundDetection(self.wurb_manager).get_detection()
            max_peak_freq_hz = None
            max_peak_dbfs = None

            while True:
                try:
                    try:
                        # item = await self.from_source_queue.get()
                        try:
                            item = await asyncio.wait_for(
                                self.from_source_queue.get(),
                                timeout=self.rec_timeout_before_restart_s,
                            )
                        except asyncio.TimeoutError:
                            # Check if restart already is requested.
                            if self.restart_activated:
                                return
                            # Logging.
                            message = (
                                "Lost connection with the microphone. Rec. restarted."
                            )
                            self.wurb_logging.warning(message, short_message=message)
                            # Restart recording.
                            self.restart_activated = True
                            loop = asyncio.get_event_loop()
                            asyncio.run_coroutine_threadsafe(
                                self.wurb_manager.restart_rec(), loop,
                            )
                            await self.remove_items_from_queue(self.from_source_queue)
                            await self.from_source_queue.put(False)  # Flush.
                            return
                        #
                        try:
                            # print("REC PROCESS: ", item["adc_time"], item["data"][:5])
                            if item == None:
                                first_sound_detected == False
                                sound_detected_counter = 0
                                self.process_deque.clear()
                                await self.to_target_queue.put(None)  # Terminate.
                                break
                            elif item == False:
                                first_sound_detected == False
                                sound_detected_counter = 0
                                self.process_deque.clear()
                                await self.remove_items_from_queue(self.to_target_queue)
                                await self.to_target_queue.put(False)  # Flush.
                            else:
                                # Compare real time and stream time.
                                adc_time = item["adc_time"]
                                detector_time = item["detector_time"]
                                # Restart if it differ too much.
                                if (
                                    abs(adc_time - detector_time)
                                    > self.max_adc_time_diff_s
                                ):
                                    # Check if restart already is requested.
                                    if self.restart_activated:
                                        return
                                    # Logging.
                                    message = "Warning: Time diff. detected. Rec. will be restarted."
                                    self.wurb_logging.info(
                                        message, short_message=message
                                    )
                                    # Restart recording.
                                    self.restart_activated = True
                                    loop = asyncio.get_event_loop()
                                    asyncio.run_coroutine_threadsafe(
                                        self.wurb_manager.restart_rec(), loop,
                                    )
                                    await self.remove_items_from_queue(
                                        self.from_source_queue
                                    )
                                    await self.from_source_queue.put(False)  # Flush.
                                    return

                                # Store in list-
                                new_item = {}
                                new_item["status"] = "data-Counter-" + str(
                                    sound_detected_counter
                                )
                                new_item["adc_time"] = item["adc_time"]
                                new_item["data"] = item["data"]

                                self.process_deque.append(new_item)
                                # Remove oldest items if the list is too long.
                                while (
                                    len(self.process_deque) > self.process_deque_length
                                ):
                                    self.process_deque.popleft()

                                # Check for sound.
                                detection_result = sound_detector.check_for_sound(
                                    (item["adc_time"], item["data"])
                                )
                                (
                                    sound_detected,
                                    peak_freq_hz,
                                    peak_dbfs,
                                ) = detection_result

                                if (not first_sound_detected) and sound_detected:
                                    first_sound_detected = True
                                    sound_detected_counter = 0
                                    max_peak_freq_hz = peak_freq_hz
                                    max_peak_dbfs = peak_dbfs
                                    # Log first detected sound.
                                    if max_peak_dbfs and peak_dbfs:
                                        # Logging.
                                        message = (
                                            "Sound peak: "
                                            + str(round(peak_freq_hz / 1000.0, 1))
                                            + " kHz / "
                                            + str(round(peak_dbfs, 1))
                                            + " dBFS."
                                        )
                                        self.wurb_logging.info(
                                            message, short_message=message
                                        )

                                # Accumulate in file queue.
                                if first_sound_detected == True:
                                    sound_detected_counter += 1
                                    if max_peak_dbfs and peak_dbfs:
                                        if peak_dbfs > max_peak_dbfs:
                                            max_peak_freq_hz = peak_freq_hz
                                            max_peak_dbfs = peak_dbfs
                                    if (
                                        sound_detected_counter
                                        >= self.detection_counter_max
                                    ) and (
                                        len(self.process_deque)
                                        >= self.process_deque_length
                                    ):
                                        first_sound_detected = False
                                        sound_detected_counter = 0
                                        # Send to target.
                                        for index in range(
                                            0, self.process_deque_length
                                        ):
                                            to_file_item = self.process_deque.popleft()
                                            #
                                            if index == 0:
                                                to_file_item["status"] = "new_file"
                                                to_file_item[
                                                    "max_peak_freq_hz"
                                                ] = max_peak_freq_hz
                                                to_file_item[
                                                    "max_peak_dbfs"
                                                ] = max_peak_dbfs
                                            if index == (self.process_deque_length - 1):
                                                to_file_item["status"] = "close_file"
                                            #
                                            if not self.to_target_queue.full():
                                                await self.to_target_queue.put(
                                                    to_file_item
                                                )

                                            # await asyncio.sleep(0)

                            # status = item.get('status', '')
                            # adc_time = item.get('time', '')
                            # data = item.get('data', '')
                            # print("DEBUG: Process status:", status, " time:", adc_time, " data: ", len(data))
                        finally:
                            self.from_source_queue.task_done()
                            await asyncio.sleep(0)

                    except asyncio.QueueFull:
                        await self.remove_items_from_queue(self.to_target_queue)
                        self.process_deque.clear()
                        await self.to_target_queue.put(False)  # Flush.
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    # Logging error.
                    message = "Recorder: sound_process_worker(1): " + str(e)
                    self.wurb_manager.wurb_logging.error(message, short_message=message)

            # While end.

        except Exception as e:
            # Logging error.
            message = "Recorder: sound_process_worker(2): " + str(e)
            self.wurb_manager.wurb_logging.error(message, short_message=message)
        finally:
            pass

    async def sound_target_worker(self):
        """ Worker for sound targets. Mainly files or streams.
         """
        wave_file_writer = None
        try:
            while True:
                try:
                    item = await self.to_target_queue.get()
                    try:
                        if item == None:
                            # Terminated by process.
                            self.to_classify_queue.put(None)
                            break
                        elif item == False:
                            await self.remove_items_from_queue(self.to_target_queue)
                            if wave_file_writer:
                                wave_file_writer.close()
                        else:
                            # New.
                            if item["status"] == "new_file":
                                if wave_file_writer:
                                    wave_file_writer.close()

                                wave_file_writer = WaveFileWriter(self.wurb_manager)
                                max_peak_freq_hz = item.get("max_peak_freq_hz", None)
                                max_peak_dbfs = item.get("max_peak_dbfs", None)
                                wave_file_writer.create(
                                    item["adc_time"], max_peak_freq_hz, max_peak_dbfs
                                )
                            # Data.
                            if wave_file_writer:
                                data_array = item["data"]
                                wave_file_writer.write(data_array)
                            # File.
                            if item["status"] == "close_file":
                                if wave_file_writer:
                                    wave_file_writer.close()
                                    wave_filename = wave_file_writer.filename
                                    wave_file_writer = None
                                    await self.to_classify_queue.put(wave_filename)
                    finally:
                        self.to_target_queue.task_done()
                        await asyncio.sleep(0)

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    # Logging error.
                    message = "Recorder: sound_target_worker: " + str(e)
                    self.wurb_manager.wurb_logging.error(message, short_message=message)
        except Exception as e:
            # Logging error.
            message = "Recorder: sound_target_worker: " + str(e)
            self.wurb_manager.wurb_logging.error(message, short_message=message)
        finally:
            pass
    
    async def sound_classify_worker(self):
        target_path = self.wurb_manager.wurb_rpi.get_wavefile_target_dir_path()
        analyzed_path = self.wurb_manager.wurb_rpi.get_wavefile_analyzed_dir_path()
        try:
            proc = p.spawn("BatClassify", timeout=None)           
            # waiting 40 seconds to be sure models for batclassify are loaded
            await asyncio.sleep(40)
            message = "Process BatClassify started"
            self.wurb_logging.info(message, short_message=message)
            while True:
                try:
                    item = await self.to_classify_queue.get()
                    if item == None:
                        self.to_database_queue.put(None)
                        break
                    else:
                        try:
                            if target_path.exists():
                                if not analyzed_path.exists():
                                    analyzed_path.mkdir()                             
                                
                                filepath = str(target_path) + "/" + item
                                proc.expect('inputfile:')   
                                proc.sendline(filepath)
                                message = "Analysing sound file..."
                                #message = "Audiodatei {} wird analysiert".format(item)
                                self.wurb_manager.wurb_logging.info(message, short_message = message)                            
                                proc.expect('\n')
                                proc.expect('\n')
                                stdout = proc.before.decode()                      
                                stdout = json.loads(stdout)

                                await self.to_database_queue.put({"filename": item, "batclassify": stdout, "filepath": filepath})                           
                                
                        # except Exception as e:
                        #     message = "Recorder: sound_classify_worker: " + str(e)
                        #     self.wurb_manager.wurb_logging.error(message, short_message=message)
                        finally:
                            self.to_classify_queue.task_done


                except asyncio.CancelledError:
                    proc.close()
                    break
                except Exception as e:
                    message = "Recorder: sound_classify_worker: " + str(e)
                    self.wurb_manager.wurb_logging.error(message, short_message=message)
                    
                finally:                                        
                    await asyncio.sleep(10)
        
        except asyncio.CancelledError:
            proc.close()
        except Exception as e:
            message = "Recorder: sound_classify_worker: " + str(e)
            self.wurb_manager.wurb_logging.error(message, short_message=message)
        finally:
            pass

    async def sound_database_worker(self):
        target_path = self.wurb_manager.wurb_rpi.get_wavefile_target_dir_path()
        analyzed_path = self.wurb_manager.wurb_rpi.get_wavefile_analyzed_dir_path()
        database = self.wurb_manager.wurb_database
        #Metadata
        # metadata = await self.wurb_settings.get_settings()
        # location = await self.wurb_settings.get_location()
        # metadata.update({'deviceName': self.device_name, 'Samplerate': self.sampling_freq_hz})
        # metadata.update(location)
        # # {'rec_mode': 'rec-mode-manual', 'file_directory': 'recorded_files',
        # #  'filename_prefix': 'wurb', 'detection_limit': 18.0, 'detection_sensitivity': -50.0,
        # #  'detection_algorithm': 'detection-simple', 'rec_length_s': '6', 'rec_type': 'FS',
        # #  'scheduler_start_event': 'on-sunset', 'scheduler_start_adjust': -15.0, 'scheduler_stop_event': 'off-sunrise',
        # #  'scheduler_stop_adjust': 15.0, 'scheduler_post_action': 'post-none', 'scheduler_post_action_delay': 5.0,
        # #  'deviceName': 'UltraMic384K 16bit r0', 'Samplerate': 384000, 'geo_source_option': 'geo-manual',
        # #  'latitude_dd': 0.0, 'longitude_dd': 0.0, 'manual_latitude_dd': 0.0, 'manual_longitude_dd': 0.0}
        
        try:
            while True:
                try:
                    item = await self.to_database_queue.get()
                    message = "Sound_database_worker: got item from queue"
                    self.wurb_manager.wurb_logging.debug(message, short_message=message)
                    if item == None:
                        message = "Sound_database_worker: terminated with item: None"
                        self.wurb_manager.wurb_logging.debug(message, short_message=message)
                        break
                    else:
                        # extract datatime String from filename
                        
                        dtime = item["filename"].split('_')[1]
                        item.update({'datetime': dtime})
                        

                        message = "Sound_database_worker: extracted datetime from item"
                        self.wurb_manager.wurb_logging.debug(message, short_message=message)
                        
                        # adding metadata to soundfile                     
                        await self.wurb_manager.wurb_metadata.append_settingMetadata(item["filepath"])                            
                        bat, prob = await self.wurb_manager.wurb_metadata.append_fileMetadata(item)
                        print(bat)
                        
                        message = "Sound_database_worker: added metadata to soundfile"
                        self.wurb_manager.wurb_logging.debug(message, short_message=message)

                        #move file and do database entry
                        try:
                            shutil.move(item["filepath"], str(analyzed_path)+"/"+item["filename"])
                            
                            await database.insert_data(item, bat, prob)
                            #message = "{} mit {:3.1f}%-iger Wahrscheinlichkeit detectiert".format(bat, prob*100)
                            message = "{} detected, probability: {:1.2f}%".format(bat, prob)
                            #message = "Discrimination-Data for {} moved to database".format(item["filename"])
                            self.wurb_manager.wurb_logging.info(message, short_message = message)

                            await self.set_bat_data(bat)
                        except Exception as e:
                            message = "Recorder: sound_database_worker: " + str(e)
                            self.wurb_manager.wurb_logging.error(message, short_message=message)
                        finally:
                            self.to_database_queue.task_done                   


                except asyncio.CancelledError:                   
                    break
                except Exception as e:
                    message = "Recorder: sound_database_worker: " + str(e)
                    self.wurb_manager.wurb_logging.error(message, short_message=message)
                    
                finally:                                        
                    await asyncio.sleep(1)
        
        except asyncio.CancelledError:                   
            pass
        except Exception as e:
            message = "Recorder: sound_database_worker: " + str(e)
            self.wurb_manager.wurb_logging.error(message, short_message=message)
        finally:
            pass
            


class WaveFileWriter:
    """ Each file is connected to a separate file writer object 
        to avoid concurrency problems. """

    def __init__(self, wurb_manager):
        """ """
        self.wurb_manager = wurb_manager
        self.wurb_recorder = wurb_manager.wurb_recorder
        self.wurb_settings = wurb_manager.wurb_settings
        self.wurb_logging = wurb_manager.wurb_logging
        self.wurb_rpi = wurb_manager.wurb_rpi
        self.rec_target_dir_path = None
        self.wave_file = None
        self.filename = None
        # self.size_counter = 0

    def create(self, start_time, max_peak_freq_hz, max_peak_dbfs):
        """ """
        rec_file_prefix = self.wurb_settings.get_setting("filename_prefix")
        rec_type = self.wurb_settings.get_setting("rec_type")
        sampling_freq_hz = self.wurb_recorder.sampling_freq_hz
        if rec_type == "TE":
            sampling_freq_hz = int(sampling_freq_hz / 10.0)
        self.rec_target_dir_path = self.wurb_rpi.get_wavefile_target_dir_path()
        rec_datetime = self.get_datetime(start_time)
        rec_location = self.get_location()
        rec_type_str = self.create_rec_type_str(
            self.wurb_recorder.sampling_freq_hz, rec_type
        )

        # Peak info to filename.
        peak_info_str = ""
        if max_peak_freq_hz and max_peak_dbfs:
            peak_info_str += "_"  # "_Peak"
            peak_info_str += str(int(round(max_peak_freq_hz / 1000.0, 0)))
            peak_info_str += "kHz"
            peak_info_str += str(int(round(max_peak_dbfs, 0)))
            peak_info_str += "dB"

        if self.rec_target_dir_path is None:
            self.wave_file = None
            return

        # Filename example: "WURB1_20180420T205942+0200_N00.00E00.00_TE384.wav"
        filename = rec_file_prefix
        filename += "_"
        filename += rec_datetime
        filename += "_"
        filename += rec_location
        filename += "_"
        filename += rec_type_str
        filename += peak_info_str
        filename += ".wav"
        self.filename = filename

        # Create directories.
        if not self.rec_target_dir_path.exists():
            self.rec_target_dir_path.mkdir(parents=True)
        # Open wave file for writing.
        filenamepath = pathlib.Path(self.rec_target_dir_path, filename)
        self.wave_file = wave.open(str(filenamepath), "wb")
        self.wave_file.setnchannels(1)  # 1=Mono.
        self.wave_file.setsampwidth(2)  # 2=16 bits.
        self.wave_file.setframerate(sampling_freq_hz)
        # Logging.
        target_path_str = str(self.rec_target_dir_path)
        target_path_str = target_path_str.replace("/media/pi/", "USB:")
        target_path_str = target_path_str.replace("/home/pi/", "SD-card:/home/pi/")
        message_rec_type = ""
        if rec_type == "TE":
            message_rec_type = "(TE) "
        message = "Sound file " + message_rec_type + "to: " + target_path_str
        self.wurb_logging.info(message, short_message=message)
        # Logging debug.
        message = "Filename: " + filename
        self.wurb_logging.debug(message=message)

    def write(self, buffer):
        """ """
        if self.wave_file is not None:
            self.wave_file.writeframes(buffer)
            # self.size_counter += len(buffer) / 2  # Count frames.

    def close(self):
        """ """
        if self.wave_file is not None:
            self.wave_file.close()
            self.wave_file = None
        # Copy settings to target directory.
        try:
            if self.rec_target_dir_path is not None:
                from_dir = self.wurb_settings.settings_dir_path
                log_file_name = self.wurb_settings.settings_file_name
                from_file_path = pathlib.Path(from_dir, log_file_name)
                to_file_path = pathlib.Path(self.rec_target_dir_path, log_file_name)
                to_file_path.write_text(from_file_path.read_text())
                # Logging debug.
                self.wurb_logging.debug(message="File closed.")
        except Exception as e:
            # Logging error.
            message = "Recorder: Copy settings to wave file directory: " + str(e)
            self.wurb_manager.wurb_logging.error(message, short_message=message)

    def get_datetime(self, start_time):
        """ """
        datetime_str = time.strftime("%Y%m%dT%H%M%S%z", time.localtime(start_time))
        return datetime_str

    def get_location(self):
        """ """
        latlongstring = ""
        try:
            location_dict = self.wurb_settings.get_location_dict()
            latitude_dd = float(location_dict.get("latitude_dd", "0.0"))
            longitude_dd = float(location_dict.get("longitude_dd", "0.0"))
            if latitude_dd >= 0:
                latlongstring += "N"
            else:
                latlongstring += "S"
            latlongstring += str(abs(latitude_dd))
            #
            if longitude_dd >= 0:
                latlongstring += "E"
            else:
                latlongstring += "W"
            latlongstring += str(abs(longitude_dd))
        except:
            latlongstring = "N00.00E00.00"

        return latlongstring

    def create_rec_type_str(self, sampling_freq_hz, rec_type):
        """ """
        try:
            sampling_freq_khz = sampling_freq_hz / 1000.0
            sampling_freq_khz = int(round(sampling_freq_khz, 0))
        except:
            sampling_freq_khz = "FS000"

        return rec_type + str(sampling_freq_khz)
