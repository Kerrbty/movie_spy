#! /usr/bin/env python
# -*- coding:utf-8 -*-
import sqlite3
import os, sys

work_dir = os.path.dirname(os.path.abspath(__file__))

MOVIE_TABLE = '''
    CREATE TABLE DoubanMovie(
        id INT PRIMARY KEY     NOT NULL,
        title      TEXT        NOT NULL,
        alias      TEXT,
        cover_url  TEXT,
        year       INT,
        date       CHAR(12),
        rating     CHAR(6),
        imdb       CHAR(12),
        type       CHAR(6),
        abstract   TEXT,
        abstract_2 TEXT,
        descript   TEXT
    );
'''



class database():
    # 初始化打开数据库 
    def __init__(self, file):
        if not os.path.exists(file):
            self._create_db(file)
        else:
            self._open_db(file)

    # 打开或者创建sqlite3数据库 
    def _open_db(self, file):
        self.db = sqlite3.connect(file)
    def _create_db(self, file):
        self._open_db(file)
        self.exec_write(MOVIE_TABLE)

    # 读写原始操作 
    def exec_read(self, sql):
        return self.db.execute(sql)
    def exec_write(self, sql):
        c = self.db.cursor()
        c.execute(sql)
        c.close()
        self.db.commit()
    
    # 关闭时候处理 
    def __del__(self):
        self.db.close()

class movie():
    def __init__(self):
        self.mdb_file = os.path.abspath(os.path.join(work_dir, '..', 'data', 'movie.db'))
        self.mdb = database(self.mdb_file)

    def __del__(self):
        pass
    
    # 检测电影id号是否在数据库 
    def check_movie_in_sql(self, movie_id):
        sqlstr = 'select count(*) from DoubanMovie where id="{0}";'.format(movie_id)
        conn = self.mdb.exec_read(sqlstr)
        for row in conn:
            if row[0] != 0:
                return True
            return False
        return False

    # 晚与某年的所有电影 
    def get_movie_after_year(self, year):
        sqlstr = 'select id from DoubanMovie where year>{0};'.format(int(year))
        return self.mdb.exec_read(sqlstr)
    
    def get_all_movie_id(self):
        sqlstr = 'select id from DoubanMovie'
        return self.mdb.exec_read(sqlstr).fetchall()

    # 插入数据 
    def save_movie2sql(self, info):
        sqlstr = 'INSERT INTO DoubanMovie (id,title,alias,cover_url,year,date,rating,imdb,type,abstract,abstract_2,descript) VALUES ({});'.format(
            '{},'.format(info.get('id')) + 
            '"{}",'.format(info.get('title').replace('"', '&quot;')) +
            '"{}",'.format(info.get('alias').replace('"', '&quot;')) +
            '"{}",'.format(info.get('cover_url')) +
            '{},'.format(info.get('year')) + 
            '"{}",'.format(info.get('date')) + 
            '"{}",'.format(info.get('rating')) +
            '"{}",'.format(info.get('imdb')) +
            '"{}",'.format(info.get('type')) +
            '"{}",'.format(info.get('abstract').replace('"', '&quot;')) + 
            '"{}",'.format(info.get('abstract_2').replace('"', '&quot;')) + 
            '"{}"'.format(info.get('descript').replace('"', '&quot;'))
            )
        # print(sqlstr)
        try:
            self.mdb.exec_write(sqlstr)
        except:
            print(info)
            exit(0)
    
    # 更新数据 
    def update_move2sql(self, info):
        sqlstr = 'UPDATE INTO DoubanMovie SET {0} WHERE {1};'.format(
            'title="{}",'.format(info.get('title')) +
            'alias="{}",'.format(info.get('alias')) +
            'cover_url="{}",'.format(info.get('cover_url')) +
            'year={},'.format(info.get('year')) + 
            'date="{}",'.format(info.get('date')) + 
            'rating="{}",'.format(info.get('rating')) +
            'imdb="{}",'.format(info.get('imdb')) +
            'type="{}",'.format(info.get('type')) +
            'abstract="{}",'.format(info.get('abstract')) + 
            'abstract_2="{}"'.format(info.get('abstract_2')) + 
            'descript="{}"'.format(info.get('descript')),
            'id={},'.format(info.get('id'))
            )
        self.mdb.exec_write(sqlstr)
