#! /usr/bin/env python
# -*- encoding:utf-8 -*-
# FileName: commands.py

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

import os
import sys
import types
from QQWry import MQQWry
from qiubai import QiuBai
import random, time

commands = {}
acommands = {}
commandchrs = "--"

qb = QiuBai()

##################### 群聊消息／命令处理 ####################################

def cmd_blockme(myself, params):
    "停止抓取自己发送的链接标题"

    if params["nick"] not in myself.blockme:
        myself.blockme.append(params["nick"])
        msg=u"%s: 执行完毕，以后不再抓取你发的链接了" % params["nick"]
        myself.send2room(msg)

def cmd_joke(myself, params):
    "显示笑话"
    myself.send2room(qb.fetch())

def cmd_date(myself, params):
    "显示日期"

    try:
        from gi.repository import LunarDate
        import time
        import locale

        locale.setlocale(locale.LC_ALL, "")
        t = time.localtime()
        l = LunarDate.Date()
        l.set_solar_date(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour)
        tt = "%d:%d:%d" % (t.tm_hour, t.tm_min, t.tm_sec);
        format = u"\n公历：%(YEAR)年%(MONTH)月%(DAY)日\n农历：%(NIAN)年%(YUE)月%(RI)日\n干支：%(Y60)年%(M60)月%(D60)日\n生肖：%(shengxiao)\n"
        myself.send2room(l.strftime(format) + "时间：" + tt + l.strftime(" (%(SHI)时)\n今天是") + l.get_jieri(" "))
    except:
        myself.send2room("此命令当前不可用\n")

def cmd_help(myself, params):
    "Show this help message"

    msg = 'Commands: \n%s' % commandchrs + commandchrs.join(["%-20s%s\n" % (x, unicode(y.__doc__, "utf8") or "") for x, y in commands.items()])
    myself.room_state.send_message(msg)

def cmd_pkg(myself, params):
    "<pkg>      查询linux软件包"

    deletechars="""` ~!@#$%^&*()={[}]:;"'<,>.?/|\\"""
    if params["msg"].startswith("--pkg"):
        args = params['msg'].split()
        if len(args) == 2:
            pkg = args[1]
            if os.path.exists("/usr/bin/apt-cache"):
                cmd = "apt-cache search %s"
            elif os.path.exists("/usr/bin/eix"):
                cmd = "eix -c %s"
            elif os.path.exists("/usr/bin/pacman"):
                cmd = "pacman -Ss %s"
            else:
                return "No support command found!"
            try:
                fd = os.popen(cmd % str(pkg).translate(None, deletechars));
                msg = fd.read()
            except:
                msg = "no result"
            myself.send2nick(params["nick"], msg)

def cmd_usage(myself, params):
    "显示完整的帮助信息"

    readme = os.path.join(myself.xmppdog.base_dir, "README")
    buf = open(readme).read()
    msg = unicode("\n" + buf, 'utf8')
    myself.send2nick(params["nick"], msg)

def cmd_fetch(myself, params):
    "订阅，执行此命令后，聊天室的消息将会转发给自己一份"

    myjid = str(params['jid'])
    nick = params["nick"]
    if myjid not in myself.fetchlist:
        myself.fetchlist.append(myjid)

        num = len(myself.fetchlist)
        msg = u"/me \"%s\"订阅了本聊天室的消息，目前共有 %d 个订阅者\n%s" % (nick, num, "\n".join(myself.fetchlist))

        myself.send2room(msg)
        myself.send2nick(nick, "已经订阅成功")
    else:
        myself.send2nick(nick, "不能重复订阅聊天室消息")

def cmd_unfetch(myself, params):
    "取消订阅，执行此命令后，聊天室的消息将不再转发给自己"

    myjid = str(params['jid'])
    nick = params["nick"]
    if myjid in myself.fetchlist:
        myself.fetchlist.remove(myjid)
        num = len(myself.fetchlist)
        if num == 0:
            msg = u"/me \"%s\"取消了订阅本聊天室的消息，目前没有订阅者。" % nick
        else:
            msg = u"/me \"%s\"取消了订阅本聊天室的消息，目前共有 %d 个订阅者\n%s" % (nick, num, "\n".join(myself.fetchlist))

        myself.send2room(msg)
        myself.send2nick(nick, "成功取消订阅")
    else:
        myself.send2nick(nick, "你没有订阅过聊天室消息")

def cmd_unblockme(myself, params):
    "恢复抓取自己发送的链接标题"

    if params["nick"] in myself.blockme:
        myself.blockme.remove(params["nick"])
        msg=u"%s: 执行完毕，我将重新开始抓取你发的链接" % params["nick"]
        myself.send2room(msg)

def cmd_fuck(myself, params):
    "你敢试试吗？"

    fuck = os.path.join(myself.xmppdog.base_dir, "fuck.txt")
    fd = open(fuck)
    talks = fd.readlines()
    nick = params["nick"]
    args = params['msg'].split()

    if len(args) == 3:
        who = args[1]
        try:
            num = int(args[2])
        except ValueError:
            num = 1
        i = 0
        while i < num:
            i = i+1
            random.seed(time.time())
            cnt = talks[random.randint(0,len(talks)-1)][:-1].decode("utf-8")
            msg = u"%s: fuck %d 次! %s: \"%s\"" % (nick, i, who, cnt)
            myself.send2room(msg)
    else:
        random.seed(time.time())
        cnt = talks[random.randint(0,len(talks)-1)][:-1].decode("utf-8")
        msg = u"%s: fuck! %s" % (nick, cnt)
        myself.send2room(msg)

def cmd_ip(myself, params):
    "<IP>           查询ip地址"

    args = params['msg'].split()
    if len(args) == 2:
        try:
            Q=MQQWry()
            msg=u"%s-> %s" % (args[1], " ".join(Q[str(args[1])][2:]).decode("utf8") )
        except:
            msg = "查询IP失败。"
        myself.send2room(msg)

def cmd_version(myself, params):
    "显示xmppdog的版本相关信息"

    line = [
            "",
            "Homepage: http://xmppdog.googlecode.com",
            "$Revision$",
            "$Date: 2011-05-12 23:01:10 +0800 (四, 2011-05-12) $",
            "Jabber ID: %s@%s/%s" % (myself.xmppdog.cfg.get('login', 'user'), myself.xmppdog.cfg.get('login', 'host'), myself.xmppdog.cfg.get('login', 'resource')),
            "Admin: %s" % " ".join(myself.xmppdog.admin),
            "Python Version: %s" % sys.version,
            ]
    msg = "\n".join(line)
    myself.send2room(msg)

##################### 群聊消息／命令处理 ####################################

for i, func in globals().items():
    if isinstance(func, types.FunctionType):
        if i.startswith('cmd_'):
            commands[i.lower()[4:]] = func
        elif i.startswith('acmd_'):
            acommands[i.lower()[5:]] = func

if __name__=="__main__":
    pass
