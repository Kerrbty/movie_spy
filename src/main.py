#! /usr/bin/env python
# -*- coding:utf-8 -*-

import os, sys
import sqlite3
import time
import traceback
import re

work_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(work_dir)
from module.movie import get_movie_info, get_other_subject_movie, search_by_rating, search_by_ratingyear, get_next_year, get_next_rating
from module import sql

movie_obj = sql.movie()
empty_ids = []
movie_id_list = []

# 日志打印时间
def logger(*nums):
    print(time.strftime("[%Y-%m-%d][%H:%M:%S] ", time.localtime()), end="")
    for argv in nums:
        print(argv, end=" ")
    print()
    sys.stdout.flush()

# 从网上更新指定id电影信息 
def update_movie(id, force = False):
    global empty_ids
    global movie_id_list
    try:
        info,jmp_id = get_movie_info(id, force)
        if info:
            movie_obj.update_move2sql(info)
            return 1
        else:
            empty_ids.append(id)
            if jmp_id != 0:
                logger(str(id) + ' 302 to ' + str(jmp_id))
                movie_id_list.append(jmp_id)
            return 0
    except:
        return -1

# 从网上更新指定id电影信息 
def insert_movie(id):
    global empty_ids
    global movie_id_list
    try:
        info,jmp_id = get_movie_info(id, False)
        if info and info['id']!=0:
            movie_obj.save_movie2sql(info)
            return 1
        else:
            empty_ids.append(id)
            if jmp_id != 0:
                logger(str(id) + ' 302 to ' + str(jmp_id))
                movie_id_list.append(jmp_id)
            return 0
    except Exception as e:
        # print(traceback.format_exc())
        return -1
    

# 更新数据库中已经存在的, 晚于xx年的电影信息(近几年新电影) 
def update_year_movie(after_year):
    ncount = 0
    dbinfo = movie_obj.get_movie_after_year(after_year)
    for info in dbinfo:
        if update_movie(info['id'], True):
            ncount += 1
    return ncount

# 在指定的id页面获取相关电影 
def get_next_movie(id):
    global empty_ids
    next_list = []
    movie_list = get_other_subject_movie(id)
    if movie_list:
        for i in movie_list:
            # 不在数据库中 
            if not movie_obj.check_movie_in_sql(i): 
                # 不在已查的空列表中 
                if i not in empty_ids:
                    next_list.append(i)
    if id in next_list:
        next_list.remove(id)
    return next_list

# 遍历所有id(容易被封IP) 
def enum_all_movie_id():
    ncount = 0
    # for id in range(10000000, 100000000, 1):
    for id in range(25745752, 25745755):
        if not movie_obj.check_movie_in_sql(id):
            insert_movie(id)
            ncount = ncount+1
    return ncount

# 已爬或者已经证明不是movie的id记录文件，爬虫随时可以重启继续 
def read_from_file(file):
    if not os.path.exists(file):
        return []
    with open(file, 'r') as fp:
        ids_list = fp.read()
        return eval(ids_list)
    return None

def write_to_file(ids_list, file):
    with open(file, 'w') as fp:
        fp.write(str(ids_list))

# 页面关联搜索 
def spy_movie():
    global empty_ids
    global movie_id_list
    # 获取数据 
    movie_id_list = read_from_file('movieids.txt')
    empty_ids = read_from_file('emptyids.txt')
    # 遍历 
    while len(movie_id_list)>0:
        movie_id = movie_id_list[0]
        movie_id_list.pop(0) # movie_id_list = movie_id_list[1:] 
        # 是否已知的无数据 
        if movie_id in empty_ids:
            print('skip ', movie_id)
            continue
        # 先测试是否已经获取过信息 
        if not movie_obj.check_movie_in_sql(movie_id):
            logger(movie_id)
            n_retry_times = 0
            n_sleep_time = 2
            n_open_browser_next = 2
            while insert_movie(movie_id) == -1:
                n_retry_times = n_retry_times + 1  # 重试次数 统计 
                n_sleep_time = n_sleep_time + 1 # 每重试一次，休眠时间加长 
                time.sleep(n_sleep_time)
                # 重试超过下一次打开浏览器次数，打开浏览器要求拼图反爬虫 
                if n_retry_times > n_open_browser_next:
                    os.system('start "" "https://movie.douban.com/subject/{}/"'.format(movie_id))
                    logger('请及时通过机器人检测哦....', n_sleep_time)
                    time.sleep(10)
                    n_open_browser_next = n_open_browser_next*2
        # 不管有没有搜索过数据，都重新把该页面链接的其他电影加入列表 
        movie_id_list += get_next_movie(movie_id)
        movie_id_list = list(set(movie_id_list))
        # 存储当前进度 
        write_to_file(movie_id_list, 'movieids.txt')
        # time.sleep(0.3) 
        empty_ids = list(set(empty_ids))
        write_to_file(empty_ids, 'emptyids.txt')

# 用年代和评分同时搜索 
def search_from_json():
    year = 1880
    start_index_pre = 0
    start_rating = 0
    while year < 2024:
        rating = start_rating
        start_index = start_index_pre
        start_index_pre = 0
        start_rating = 0
        while rating<100:
            write_to_file("year:"+str(year)+",rating:"+str(rating)+",index:"+str(start_index), "crtmp.txt")
            # 尽量不然禁用搜索 
            time.sleep(6.5*60)
            # 获取数据 
            status, movie_list = search_by_ratingyear(rating/10, get_next_rating(year, rating)/10, start_index, year)
            if not status:
                time.sleep(15*60)
            elif len(movie_list) == 0:
                rating = get_next_rating(year, rating)
                start_index = 0
            else:
                next_list = []
                for i in movie_list:
                    # 不在数据库中 
                    if not movie_obj.check_movie_in_sql(i): 
                        # 不在已查的空列表中 
                        if i not in empty_ids:
                            next_list.append(i)
                logger("count: ", len(next_list))
                if len(next_list)>0:
                    write_to_file(next_list, 'movieids.txt')
                    spy_movie()
                # 下一组 
                start_index = start_index + 20
        year = get_next_year(year) + 1

# 仅用评分搜索 
def search_from_json2():
    # 电影集中在 0、4.8、5.1、5.2、5.3、5.7、6.0、6.7 
    rating = 0  # 0~100 
    start_index = 0 # 当前搜索起始条目 
    # 
    search_count = 0
    while rating<100:
        # 尽量不然禁用搜索 
        search_count = search_count + 1
        if search_count%3 == 0:
            time.sleep(5*60)
        else:
            time.sleep(60)
        # 获取数据 
        try:
            status, movie_list = search_by_rating(rating/10, (rating+1)/10, start_index)
        except:
            status = False
        if not status:
            time.sleep(10*60)
        elif len(movie_list) == 0:
            rating = rating + 1
            start_index = 0
        else:
            next_list = []
            for i in movie_list:
                # 不在数据库中 
                if not movie_obj.check_movie_in_sql(i): 
                    # 不在已查的空列表中 
                    if i not in empty_ids:
                        next_list.append(i)
            if len(next_list)>0:
                write_to_file(next_list, 'movieids.txt')
                spy_movie()
            # 下一组 
            start_index = start_index + 20

# 使用别人的数据进行补充 
def spy_from_csv_data():
    csv_file = os.path.join(work_dir, 'data', 'movie.csv')
    with open(csv_file, "r", encoding="utf-8") as fp:
        next_list = []
        while True:
            line = fp.readline()
            if not line:
                break
            groups = line.split(',')
            if len(groups)>0 and re.match(r'^\d+$', groups[0]):
                if not movie_obj.check_movie_in_sql(groups[0]): 
                    # 不在已查的空列表中 
                    next_list.append(groups[0])
        if len(next_list)>0:
            write_to_file(next_list, 'movieids.txt')
            spy_movie()

# 1800年的电影如果date里面有日期，则用date里面的年份 
def Replace_Year():
    update_idlist = {}
    for id_year_date in movie_obj.get_movie_year():
        if id_year_date[2] and int(id_year_date[1]) == 1800:
            years = re.findall('^\d{4}', id_year_date[2])
            # print(id_year_date[2], '->', years)
            if len(years)>0:
                if int(id_year_date[1]) != int(years[0]):
                    update_idlist[id_year_date[0]] = int(years[0])
    for id in update_idlist.keys():
        movie_obj.update_year(id, update_idlist[id])

if __name__=='__main__':
    # Replace_Year()
    # spy_movie() # 从某个点开始爬 
    # spy_from_csv_data() # 使用别人爬的结果进行爬 
    # search_from_json2() # 使用评分爬 
    # search_from_json() # 使用评分和年代爬 
    