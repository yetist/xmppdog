#! /usr/bin/env python
# -*- encoding:utf-8 -*-
# FileName: date.py

"This file is part of ____"
 
__author__   = "yetist"
__copyright__= "Copyright (C) 2009 yetist <yetist@gmail.com>"
__license__  = """
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
import liblunar
import time
import locale

def do_date():
    locale.setlocale(locale.LC_ALL, "")
    t = time.localtime()
    l=liblunar.Date()
    l.set_solar_date(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour)
    tt = "%d:%d:%d" % (t.tm_hour, t.tm_min, t.tm_sec);
    format = "\n公历：%(YEAR)年%(MONTH)月%(DAY)日\n农历：%(NIAN)年%(YUE)月%(RI)日\n干支：%(Y60)年%(M60)月%(D60)日\n生肖：%(shengxiao)\n节日：%(jieri)\n时间：" +tt
    return l.strftime(format)
