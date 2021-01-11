import asyncio
import wurb_rec
import guano
import datetime

class WurbMetadata(object):

    def __init__(self, wurb_manager):

        self.wurb_manager = wurb_manager
        self.settingMetadata = None

    async def set_settingMetadata(self):
        self.settingMetadata = await self.wurb_manager.wurb_settings.get_settings()
        location = await self.wurb_manager.wurb_settings.get_location()
        self.settingMetadata.update({'deviceName': self.wurb_manager.wurb_recorder.device_name, 'Samplerate': self.wurb_manager.wurb_recorder.sampling_freq_hz})
        self.settingMetadata.update(location)
    
    async def append_settingMetadata(self, filepath):
        try:
            g = guano.GuanoFile(filepath)
            g["Filter HP"] = int(self.settingMetadata["detection_limit"])
            g["Length"] = int(self.settingMetadata["rec_length_s"]) # same with TE?
            g["Samplerate"] = int(self.settingMetadata["Samplerate"])
            g["Note"] = "Recorded with a RaspberryPi and the {}; sesitivity: {}dB".format(self.settingMetadata["deviceName"], self.settingMetadata["detection_sensitivity"])
            # if metatdata["rec_type"] == "TE":
            #    g["TE"] = 10
            if self.settingMetadata["geo_source_option"] == "geo-usb-gps":
                 g["Loc Position"] = (float(self.settingMetadata["latitude_dd"]), float(self.settingMetadata["longitude_dd"]))
            if self.settingMetadata["geo_source_option"] == "geo-manual":
                 g["Loc Position"] = (float(self.settingMetadata["manual_latitude_dd"]), float(self.settingMetadata["manual_longitude_dd"]))
            
            
            g.write(make_backup=False)
        except Exception as e:
            message = "Guano SettingMetadata error: " + str(e)
            self.wurb_manager.wurb_logging.error(message, short_message=message)

    async def append_fileMetadata(self, metadata):
        # detect highest probability in classification
        prob = 0
        bat = ""
        for i in metadata["batclassify"]:
            if metadata["batclassify"][i]>prob:
                prob=metadata["batclassify"][i]
                bat=i
        
        # alternativ algorith to detect highest prob in classification
        # bc = item["batclassify"]
        # bc_sort = dict(sorted(bc.items(), key = lambda kv: kv[1], reverse = True))
        # bat = next(iter(bc_sort))
        try:
            
            g = guano.GuanoFile(metadata["filepath"])
            g["Original Filename"] = metadata["filename"]
            g["Timestamp"] = metadata["datetime"]
            g["Species Auto ID"] = bat

            g.write(make_backup=False)

        except Exception as e:
            message = "Guano FileMetadata error: " + str(e)
            self.wurb_manager.wurb_logging.error(message, short_message=message)

        return bat, prob
            




