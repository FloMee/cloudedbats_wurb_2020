

import sqlite3
import asyncio
import os

import wurb_rec


class WurbDatabase(object):

    def __init__(self, wurb_manager):

        self.wurb_manager = wurb_manager        
        self.database = None
        self.conn = None
        self.c = None
        self.setup_database()

    def setup_database(self):
        target_path = self.wurb_manager.wurb_rpi.get_wavefile_target_dir_path()
        self.database_path = str(target_path) + '/wurb_data.db'
        if not os.path.isfile(self.database_path):
            self.conn = sqlite3.connect(self.database_path)
            self.c = self.conn.cursor()
            self.c.execute('''CREATE TABLE audiofiles
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
            filepath text NOT NULL,
            datetime text NOT NULL,
            Bbar real,
            Malc real,
            Mbec real,
            MbraMmys real,
            Mdau real,
            Mnat real,
            NSL real,
            Paur real,
            Ppip real,
            Ppyg real,
            Rfer real,
            Rhip real)''')

        else: 
            self.conn = sqlite3.connect(self.database_path)
            self.c = self.conn.cursor()
    
    async def insert_data(self, data):
        try:
            self.c.execute('''INSERT INTO audiofiles (filepath, datetime,
            Bbar, Malc, Mbec, MbraMmys, Mdau,
            Mnat, NSL, Paur, Ppip, Ppyg, Rfer,
            Rhip) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',[data['filepath'], data['datetime'],
            data['batclassify']['Bbar'], data['batclassify']['Malc'], data['batclassify']['Mbec'], data['batclassify']['MbraMmys'], data['batclassify']['Mdau'],
            data['batclassify']['Mnat'], data['batclassify']['NSL'], data['batclassify']['Paur'], data['batclassify']['Ppip'], data['batclassify']['Ppyg'], data['batclassify']['Rfer'],
            data['batclassify']['Rhip']])
        except Exception as err:
            message = "Database Input Error: " +err
            self.wurb_manager.wurb_logging.error(message, short_message=message)
        finally:
            self.conn.commit()

    async def close(self):
        self.conn.close()



