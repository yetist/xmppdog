#! /usr/bin/env python
# -*- encoding:utf-8 -*-
# FileName: qb.py

"This file is part of ____"
 
__author__   = "yetist"
__copyright__= "Copyright (C) 2011 yetist <xiaotian.wu@i-soft.com.cn>"
__license__  = """
This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""
import time
import urllib
import urllib2
import re
import md5
from BeautifulSoup import BeautifulSoup,Tag,NavigableString
from BeautifulSoup import BeautifulStoneSoup

def recurTags(tag):
    if isinstance(tag,Tag):
        if tag.has_key('class') and tag['class'] == 'tags':
            return ''

        tmpStr = ''
        for t in tag.contents:
            tmpStr += '\n'
            tmpStr += recurTags(t)

        return tmpStr

    elif isinstance(tag,NavigableString):
        if tag.string is not None:
            return tag.string
        else:
            return ''
    else:
        return repr(tag)

class QiuBai:
    def __init__(self):
        self.hotmsg = {}
        self.lastmsg = {}
        self.qb="http://www.qiushibaike.com/groups/2/latest"
        self.qbhot="http://www.qiushibaike.com/groups/2/hottest/day"
        self.hpage = 0
        self.lpage = 0
        self.down(True)

    def down(self, hot):
        if hot:
            self.QBDown(self.qbhot, self.hpage)
            self.hpage = self.hpage + 1
        else:
            self.QBDown(self.qb, self.lpage)
            self.lpage = self.lpage + 1

    def fetch(self, hot=True):
        if hot: 
            if len(self.hotmsg) == 0:
                self.down(hot)
            (k,v) = self.hotmsg.popitem()
        else:
            if len(self.lastmsg) == 0:
                self.down(hot)
            (k,v) = self.lastmsg.popitem()
        return v

    def QBDown(self, url, page, hot=True):
        qb_url = "%s/page/%d" % (url, page+1)
        user_agent = 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'
        values = {'name' : 'DanteZhu',
            'location' : 'China',
            'language' : 'Python' }
        headers = { 'User-Agent' : user_agent }

        data = urllib.urlencode(values)
        req = urllib2.Request(qb_url, data, headers)
        response = urllib2.urlopen(req)
        the_page = response.read()
        soup = BeautifulSoup(the_page,convertEntities=BeautifulStoneSoup.HTML_ENTITIES)

        allTags = soup.findAll('div',attrs={'class' : re.compile(r'\s*qiushi_body\s*article\s*')})

        for tag in allTags:
            for art in tag.contents:
                tmpStr = recurTags(art).encode("utf8")
                tmpStr=tmpStr.replace("\r\n",'')
                strList=tmpStr.split("\n")
                cont = []
                for line in strList:
                    if len(line) > 0:
                        cont.append(line)
                msg = "".join(cont)
                if len(msg) > 8:
                    csum=md5.md5(msg)
                    if hot:
                        self.hotmsg[csum] = msg
                    else:
                        self.lastmsg[csum] = msg
            #print('\n#=============================================================================\n')

if __name__=="__main__":
#    qb="http://www.qiushibaike.com/groups/2/latest"
#    qbn="http://www.qiushibaike.com/groups/2/latest"
#    qbhot="http://www.qiushibaike.com/groups/2/hottest/day"
#    qbhotn="http://www.qiushibaike.com/groups/2/hottest/day"
#    QBShow(qb, 2)
#    for i in allmsg.keys():
#        print i, allmsg[i]
    a = QiuBai()
    print a.fetch()
