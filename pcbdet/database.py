import os
import os.path as osp
from pathlib import Path
import sqlite3
import time
import datetime

class PcbdetDataBase:
    def __init__(self):
        self.pcbdet_info = sqlite3.connect("pcbdet_info.db")
        self.pcbdet_cursor = self.pcbdet_info.cursor()

    def init_user_table(self):
        user_info_table = "CREATE TABLE IF NOT EXISTS uesr_info \
                             (UserID INT PRIMARY KEY NOT NULL, \
                             TrueName VARCHAR, \
                             UserName VARCHAR, \
                             UserPassword VARCHAR, \
                             UserSex VARCHAR, \
                             UserAge INTEGER, \
                             UserPhone VARCHAR)"
        self.pcbdet_cursor.execute(user_info_table)

        fetch_admin = self.pcbdet_cursor.execute(F"SELECT * FROM uesr_info WHERE UserID==1").fetchall()
        if len(fetch_admin) == 0:
            admin_info = "1, 'xxx', 'admin', 'admin@1234', 'man', 23, '15070700230'"
            self.pcbdet_cursor.execute("INSERT INTO uesr_info VALUES (%s)"%admin_info)
            self.pcbdet_info.commit()
            fetch_admin = self.pcbdet_cursor.execute(F"SELECT * FROM uesr_info").fetchall()
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 账户信息: ", fetch_admin)

    def close_user_table(self, close_database=True):
        self.pcbdet_cursor.close()
        if close_database:
            self.pcbdet_info.close()

    def init_defect_table(self):
        defect_info_table = "CREATE TABLE IF NOT EXISTS defect_info \
                             (DefectID                INT PRIMARY KEY NOT NULL, \
                             DetectTime               VARCHAR NOT NULL, \
                             DefectType               VARCHAR NOT NULL, \
                             FromImage                VARCHAR NOT NULL, \
                             ImageHeight              INT NOT NULL, \
                             ImageWidth               INT NOT NULL, \
                             DefectCoordLeftTopX      FLOAT NOT NULL, \
                             DefectCoordLeftTopY      FLOAT NOT NULL, \
                             DefectCoordRightDownX    FLOAT NOT NULL, \
                             DefectCoordRightDownY    FLOAT NOT NULL, \
                             DefectConf               FLOAT NOT NULL)"
        self.pcbdet_cursor.execute(defect_info_table)

    def insert_one_data_to_defect(self, data: dict):
        fetch_data = self.pcbdet_cursor.execute(f"SELECT * FROM defect_info").fetchall()
        if len(fetch_data) == 0:
            defect_info = f"1, '20240314', 'bit', 'datasets/0000.jpg', 480, 640, 23.2, 54.5, 157.2, 166.7, 0.8"
            self.pcbdet_cursor.execute("INSERT INTO defect_info VALUES (%s)"%defect_info)
            self.pcbdet_info.commit()
            fetch_data = self.pcbdet_cursor.execute(f"SELECT * FROM defect_info").fetchall()
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] PCB 缺陷信息: ", fetch_data)

    def fetch_all_data(self):
        return self.pcbdet_cursor.execute(f"SELECT * FROM defect_info").fetchall()

    def obt_table_name(self):
        self.pcbdet_cursor.execute('pragma table_info(defect_info)')
        col_name = self.pcbdet_cursor.fetchall()
        col_name = [x[1] for x in col_name]

        return col_name

    def close_defect_table(self, close_database=True):
        self.pcbdet_cursor.close()
        if close_database:
            self.pcbdet_info.close()

    def delete_table(self):
        self.pcbdet_cursor.close()
        self.pcbdet_info.close()
        self.pcbdet_cursor.execute(f"DROP TABLE table_name")