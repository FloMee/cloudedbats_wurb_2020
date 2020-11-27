

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
            data['Bbar'], data['Malc'], data['Mbec'], data['MbraMmys'], data['Mdau'],
            data['Mnat'], data['NSL'], data['Paur'], data['Ppip'], data['Ppyg'], data['Rfer'],
            data['Rhip']])
        except Exception as err:
            print(err)
        finally:
            self.conn.commit()

    async def close(self):
        self.conn.close()



