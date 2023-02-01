#! /usr/bin/env python
# -*- coding:utf-8 -*-
import os

work_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.abspath(os.path.join(work_dir, '..', 'data'))
html_tmp_path = os.path.join(data_dir, 'descript')

if not os.path.exists(data_dir):
    os.makedirs(data_dir)
if not os.path.exists(html_tmp_path):
    os.makedirs(html_tmp_path)