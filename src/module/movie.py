#! /usr/bin/env python
# -*- coding:utf-8 -*-
import requests
import re
import os
import sys
import time
import json
import urllib3
from urllib.parse import urlparse
from bs4 import BeautifulSoup
urllib3.disable_warnings()

http_headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
    'Cookie': '自行加入浏览器cookie。需要人工验证时，自动会弹出浏览器',
    'Referer': 'https://accounts.douban.com/'
}

Search_Rating_Url = 'https://movie.douban.com/j/new_search_subjects?sort=T&range={0},{1}&tags=&start={2}'

Search_Rating_year_Url = 'https://movie.douban.com/j/new_search_subjects?sort=T&range={0},{1}&tags=&start={2}&year_range={3},{4}'


work_dir = os.path.dirname(os.path.abspath(__file__))
html_tmp_path = os.path.abspath(os.path.join(work_dir, '..', 'data', 'descript'))

# 日志打印时间
def logger(*nums):
    print(time.strftime("[%Y-%m-%d][%H:%M:%S] ", time.localtime()), end="")
    for argv in nums:
        print(argv, end=" ")
    print()
    sys.stdout.flush()

# 猜测网页编码 
def get_encoding(html):
    if re.search('charset="gb2312"', html) or re.search('charset=gb2312', html):
        return "gb2312"
    elif re.search('charset="gbk"', html) or re.search('charset=gbk', html):
        return "gbk"
    elif re.search('charset="utf-8"', html) or re.search('charset=utf-8', html):
        return "utf-8"
    else:
        return "utf-8"

# 获取网页文本
def _http_request(url, data = None, post = False):
    try:
        # 获取网页
        http = requests.session()
        http.keep_alive = False
        if post:
            r = http.post(url, timeout=3, headers=http_headers, data=data, verify=False)
        else:
            r = http.get(url, timeout=3, headers=http_headers, verify=False)
        # 设置网页编码
        r.encoding = get_encoding(r.text)
        # 记录cookie
        if r.cookies:
            cookie = ''
            for k,v in r.cookies.items():
                cookie = cookie + str(k) + '=' + str(v) + ';'
            http_headers["Cookie"] = cookie
        # 返回页面数据 
        return r.text
    except:
        return None

def get_html(url, retry = 5):
    times = 0
    html = None
    while times < retry:
        html = _http_request(url)
        if html:
            break
        times = times+1
    return html

# 获取电影名 和 年份 
def get_name_year(html):
    title = None
    year = '1800'
    # 方法一: 
    title_list = re.findall(r'property="v:itemreviewed">(.*?)</span>', html)
    year_list = re.findall(r'class="year">\((\d+)\)</span>', html)
    if len(title_list)>0:
        title = title_list[0]
    if len(year_list)>0:
        year = year_list[0]
    # 方法二: 
    if not title or not year:
        htitle = re.findall(r'type="hidden" name="title" value="(.*?)\((\d+)\)', html)
        if len(htitle)>0:
            title, year = htitle[0]
            title = title.replace('\u200e', '')
    # 方法三: 
    if not title or not year:
        htitle = re.findall(r'<strong>(.*?)\((\d+)\)</strong>', html)
        if len(htitle)>0:
            title, year = htitle[0]
    # 方法四: 
    if not title or not year:
        htitle = re.findall(r'data-name="(.*?)\((\d+)\)"', html)
        if len(htitle)>0:
            title, year = htitle[0]
    # 方法五：
    if year == '1800':
        years_list = re.findall(r'property="v:initialReleaseDate" content="(\d+)">(\d+)</span>', html)
        if len(years_list)>0:
            year = years_list[0][0]
    title = title.replace('\u200e', '')
    year = year.replace('２', '2').replace('１', '1').replace('０', '0')
    return title, int(year)

# 获取电影别名 
def get_alias(html):
    alias_list = re.findall(r'又名:</span>(.*?)<br/>', html)
    if len(alias_list)>0:
        return alias_list[0]
    return ''

# 获取电影海报 
def get_poster(html):
    poster_list = re.findall(r'src="(.*?)" title="点击看更多海报"', html)
    if len(poster_list)>0:
        poster = poster_list[0]
        return poster.replace('s_ratio_poster', 'l')
    image_list = re.findall(r'"image": "(.*?)",', html)
    if len(image_list)>0:
        poster = image_list[0]
        return poster.replace('s_ratio_poster', 'l')
    return ''

# IMDb id 
def get_imdb(html):
    imbi_list = re.findall(r'IMDb:</span>(.*?)<br>', html)
    if len(imbi_list)>0:
        return imbi_list[0].strip()
    return ''

# 上映日期 
def get_date(html):
    date_list = re.findall(r'property="v:initialReleaseDate" content="(.*?)"', html)
    if len(date_list)>0:
        return date_list[0].strip()
    datePublished = re.findall(r'"datePublished": "(.*?)",', html)
    if len(datePublished)>0:
        return datePublished[0]
    return ''

# 得分(star星评/value十分制/count评价人数)
def get_rating(html):
    # 得分 / 评价人数 / 星评 
    rating = {'value': '0', 'count': '0', 'star': '0'}
    aggregateRating = re.findall(r'("aggregateRating": {[^}]*})', html)
    if len(aggregateRating) > 0:
        json_rate = json.loads('{' + aggregateRating[0] + '}')
        rating['count'] = json_rate['aggregateRating']['ratingCount']
        rating['value'] = json_rate['aggregateRating']['ratingValue']
    bigstar = re.findall(r'bigstar(\d+)', html)
    if len(bigstar)>0:
        rating['star'] = int(bigstar[0])/10
    if rating['count'] == '0':
        votes_list = re.findall(r'property="v:votes">(\d+)</span>', html)
        if len(votes_list)>0:
            rating['count'] = votes_list[0]
    if rating['value'] == '0': 
        average_list = re.findall(r'property="v:average">(.*?)</strong>', html)
        if len(average_list)>0:
            rating['value'] = average_list[0]
    return "{0}/{1}/{2}".format(rating['star'], rating['value'], rating['count'])

# 猜测是电影还是电视剧 
def get_type(html):
    answerObj = re.findall(r'var answerObj = ({[^}]*?})', html)
    if len(answerObj)>0:
        answerjson = answerObj[0].replace(' ', '').replace('\r', '').replace('\n', '')
        answerjson = answerjson.replace('{', '{"').replace(':', '":').replace(',', ',"').replace('\'', '"')
        json_answer = json.loads(answerjson)
        if json_answer['TYPE'] == 'movie':
            return 'movie'
        elif json_answer['TYPE'] == 'tv':
            return 'tv'
    type_list = re.findall(r'data-type="电影"', html)
    if len(type_list)>0:
        return 'movie'
    else:
        return 'tv'

# 类型/制片国家/语言/片长 
def get_info(html):
    movie = {'type': '', 'country': '', 'language': '', 'time': ''}
    country_list = re.findall(r'制片国家/地区:</span>(.*?)<br/>', html)
    if len(country_list)>0:
        movie['country'] = country_list[0].strip()
    type_list = re.findall(r'property="v:genre">(.*?)</span>', html)
    for i in type_list:
        movie['type'] = movie['type'] + '/' + i.strip()
    language_list = re.findall(r'语言:</span>(.*?)<br/>', html)
    if len(language_list)>0:
        movie['language'] = language_list[0].strip()
    continuance = re.findall(r'property="v:runtime" content="(\d+)"', html)
    if len(continuance)>0:
        movie['time'] = continuance[0]
    return '{0}/{1}/{2}/{3}分钟'.format(movie['type'], movie['country'], movie['language'], movie['time'])

# 演员列表 
def get_rotes(html):
    actors = re.findall(r'"actor":\s+\[([^\x5d]*?)\]', html)
    if len(actors)>0:
        name_list = re.findall(r'"name": "(.*?)"', actors[0])
        return '/'.join(name_list)
    actor_list = re.findall(r'property="video:actor" content="(.*?)"', html)
    if len(actor_list)>0:
        return '/'.join(actor_list)
    starring_list = re.findall(r'rel="v:starring">(.*?)</a>', html)
    if len(starring_list)>0:
        return '/'.join(starring_list)
    return None

# 影视简介 
def get_descript(html):
    hidden_desp = re.findall(r'class="all hidden"[^>]*>([\w|\W]*?)</span>', html)
    if len(hidden_desp)>0:
        desc0 = hidden_desp[0].replace(' ', '').replace('\n', '').replace('\r', '')
        return desc0
    descripts = re.findall(r'property="v:summary"[^>]*>([\w|\W]*?)</span>', html)
    if len(descripts)>0:
        desc = descripts[0].replace(' ', '').replace('\n', '').replace('\r', '')
        return desc
    descripts2 = re.findall(r'"description": ".*?",', html)
    if len(descripts2)>0:
        return descripts2[0]
    descripts3 = re.findall(r'property="og:description" content=".*?"', html)
    if len(descripts3)>0:
        return descripts3[0]

# 从缓存或者网上更新页面(抛出异常表示禁止访问，IP被限制) 
def get_page(url, tmp_path, force = False):
    pagehtml = None
    # 是否强制更新文件 
    if force and os.path.exists(tmp_path):
        os.remove(tmp_path)
    # 如果已经有缓存，使用缓存，如果没有下载电影信息 
    if os.path.exists(tmp_path):
        with open(tmp_path, 'rb') as fp:
            pagehtml = fp.read().decode('utf-8')
    else:
        pagehtml = get_html(url)
        # 空页面不记录文件 
        if pagehtml:
            with open(tmp_path, 'wb') as fp:
                fp.write(pagehtml.encode('utf-8'))
        else:
            raise Exception('page empty.') 
    # 检测电影是否存在  
    title = re.findall(r'<title>([\w|\W]*?)</title>', pagehtml)
    if len(title)>0:
        if title[0].strip()=='页面不存在' or title[0].strip()=='条目不存在':
            # 不存在的页面需要删除 
            os.remove(tmp_path)
            return None,0
        elif title[0].strip()=='豆瓣 - 登录跳转页':
            ids_page = re.findall(r'%2Fsubject%2F(\d+)%2F', pagehtml)
            if len(ids_page)>0:
                # 跳转的页面需要删除 
                os.remove(tmp_path)
                return None,ids_page[0]
            return None,0
        elif title[0].strip()=='禁止访问':
            # IP被禁的页面需要删除 
            os.remove(tmp_path)
            raise Exception('禁止访问.') 
    else:
        # 条目不存在的另一种形式 
        if re.match(r'^<script>var d=\[navigator.platform', pagehtml):
            # 跳转的页面需要删除 
            os.remove(tmp_path)
            return None,0
    return pagehtml,0

# 电影页面关联的所有相关电影id 
def get_other_subject_movie(id):
    # 电影页面 
    movie_url = 'https://movie.douban.com/subject/{}/'.format(id)
    # 从文件中读取还是从网上下载 
    cached_file_name = os.path.join(html_tmp_path, str(id)+'.html')
    pagehtml,jmp_id = get_page(movie_url, cached_file_name)
    if not pagehtml:
        return None
    subject_list = re.findall(r'/subject/(\d+)/', pagehtml)
    return list(set(subject_list))

# 是否更新现有电影信息 
def get_movie_info(id, force = False):
     # 电影页面 
    movie_url = 'https://movie.douban.com/subject/{}/'.format(id)
     # 从文件中读取还是从网上下载 
    cached_file_name = os.path.join(html_tmp_path, str(id)+'.html')
    pagehtml,jmp_id = get_page(movie_url, cached_file_name, force)
    if not pagehtml:
        return None,jmp_id
    # 初始化数据，以防中间有空数据 
    movie_info = {
        'id': id, 
        'title': '',
        'alias': '',
        'cover_url': '',
        'year': 1900,
        'date': '',
        'rating': '',
        'imdb': '',
        'type': '',
        'abstract': '',
        'abstract_2': '',
        'descript': ''
    }
    # 获取电影id 
    movie_info['id'] = id
    # 获取影片名和年份 
    movie_info['title'], movie_info['year'] = get_name_year(pagehtml)
    # 别名
    movie_info['alias'] = get_alias(pagehtml)
    # 封面图
    movie_info['cover_url'] = get_poster(pagehtml)
    # 上映日期
    movie_info['date'] = get_date(pagehtml)
    # 评分信息 
    movie_info['rating'] = get_rating(pagehtml)
    # IMdb id
    movie_info['imdb'] = get_imdb(pagehtml)
    # 类型(猜测)
    movie_info['type'] = get_type(pagehtml)
    # 类型/制片国家/语言/片长(card_subtitle) 
    movie_info['abstract'] = get_info(pagehtml)
    # 演员列表(abstract) 
    movie_info['abstract_2'] = get_rotes(pagehtml)
    # 影片简介 
    movie_info['descript'] = get_descript(pagehtml)

    return movie_info, 0

    # http://1.15.242.194:5000/api/v2/search/movie?q=%E7%BE%8E%E4%BA%BA%E9%B1%BC 


#######################################################################################################
# 搜索: 
# https://movie.douban.com/j/new_search_subjects?sort=U&range=0,10&tags=电影,青春&start=0&genres=剧情&countries=中国大陆&year_range=2019,2019
# 一次最多返回20部电影 
# range=0,10 评分区间筛选(可以0.1间隔采样) 
# start=0 控制起始id 
# year_range=2019,2019 年份
# tags 电影形式
# genres 电影类型
# country 国家

# https://movie.douban.com/j/new_search_subjects?sort=T&range=0,20&tags=&start=0
def search_by_rating(start_rating, end_rating, start_index):
    movie_id_list = []
    search_url = Search_Rating_Url.format(start_rating, end_rating, start_index)
    logger(search_url)
    pagejson = get_html(search_url)
    if pagejson:
        jvdata = json.loads(pagejson)
        if 'data' in jvdata:
            for movie_info in jvdata['data']:
                movie_id_list.append(movie_info['id'])
            return True, movie_id_list
        elif 'r' in jvdata:
            print(sys._getframe().f_code.co_name + "(" + str(sys._getframe().f_lineno) + "): " + str(pagejson))
            return False, []
        else:
            print(sys._getframe().f_code.co_name + "(" + str(sys._getframe().f_lineno) + "): " + str(pagejson))
            raise Exception("err")
    else:
        print(sys._getframe().f_code.co_name + "(" + str(sys._getframe().f_lineno) + "): " + str(pagejson))
        return True, []
        
# https://movie.douban.com/j/new_search_subjects?sort=T&range=0,20&tags=&start=0&year_range=2019,2019 
def search_by_ratingyear(start_rating, end_rating, start_index, year):
    movie_id_list = []
    search_url = Search_Rating_year_Url.format(start_rating, end_rating, start_index, year, get_next_year(year))
    logger(search_url)
    pagejson = get_html(search_url)
    if pagejson:
        # print(pagejson)
        try:
            jvdata = json.loads(pagejson)
        except:
            print(pagejson)
            return False, []
        if 'data' in jvdata:
            for movie_info in jvdata['data']:
                movie_id_list.append(movie_info['id'])
            return True, movie_id_list
        elif 'r' in jvdata:
            print(sys._getframe().f_code.co_name + "(" + str(sys._getframe().f_lineno) + "): " + str(pagejson))
            return False, []
        else:
            print(sys._getframe().f_code.co_name + "(" + str(sys._getframe().f_lineno) + "): " + str(pagejson))
            raise Exception("err")
    else:
        print(sys._getframe().f_code.co_name + "(" + str(sys._getframe().f_lineno) + "): " + str(pagejson))
        return False, []
    
def get_next_year(year):
    if year < 1900:
        return year+9
    elif year < 1980:
        return year+4
    elif year < 2005:
        return year+2
    else:
        return year
    
def get_next_rating(year, rating):
    if year < 1930:
        return rating+50
    elif year < 1980:
        return rating+40
    elif year < 2005:
        return rating+20
    else:
        return rating+10