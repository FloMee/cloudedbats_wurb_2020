

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
            (filepath text NOT NULL,
            datetime text NOT NULL,
            auto_batid text,
            auto_id_prob real)''')

        else: 
            self.conn = sqlite3.connect(self.database_path)
            self.c = self.conn.cursor()

        message = "Sound_database: Database setup completed"
        self.wurb_manager.wurb_logging.debug(message, short_message=message)
    
    async def insert_data(self, data, bat, prob):
        try:
            self.c.execute('''INSERT INTO audiofiles (filepath, datetime,
            auto_batid, auto_id_prob) VALUES (?,?,?,?)''',[data['filepath'], data['datetime'], bat, prob])
        except Exception as err:
            message = "Database Input Error: " +err
            self.wurb_manager.wurb_logging.error(message, short_message=message)
        finally:
            self.conn.commit()

    async def close(self):
        self.conn.close()



