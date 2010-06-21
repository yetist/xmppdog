#! /usr/bin/env python
# -*- encoding:utf-8 -*-
# FileName: chatroom.py

"This file is part of xmppdog"
 
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

import string
import curses
import os

import pyxmpp
from pyxmpp.jabber import delay
from xmppdog.plugin import PluginBase
from pyxmpp.jabber import muc,delay
from pyxmpp.message import Message

from QQWry import MQQWry

class Plugin(PluginBase):
    def __init__(self, app, name):
        PluginBase.__init__(self,app,name)
        self.conversations={}
        self.last_thread=0

    def unload(self):
        if self.xmppdog.room_manager is not None:
            for (room_id, room_nick ) in self.xmppdog.cfg.items("room"):
                room_jid=pyxmpp.JID(unicode(room_id))
                rs=self.xmppdog.room_manager.get_room_state(room_jid)
                if rs and rs.joined:
                    room_handler=rs.handler
                else:
                    room_handler=Room(room_jid, self.xmppdog.stream.me)
                room_handler.room_state.leave()
                self.xmppdog.room_manager.forget(rs)
            self.xmppdog.room_manager = None
        return True

    def session_started(self,stream):
        self.xmppdog.room_manager=muc.MucRoomManager(self.xmppdog.stream)
        self.xmppdog.room_manager.set_handlers()
        for (room_id, room_nick ) in self.xmppdog.cfg.items("room"):
            room_jid=pyxmpp.JID(unicode(room_id))
            if room_jid.resource or not room_jid.node:
                self.xmppdog.error("Bad room JID")
                return
            rs=self.xmppdog.room_manager.get_room_state(room_jid)
            if rs and rs.joined:
                room_handler=rs.handler
            else:
                room_handler=Room(room_jid, self.xmppdog.stream.me, self.xmppdog)
                self.xmppdog.room_manager.join(room_jid, room_nick, room_handler)

    def message_error(self,stanza):
        fr=stanza.get_from()
        thread=stanza.get_thread()
        key=fr.bare().as_unicode()

        conv=None
        if self.conversations.has_key(key):
            convs=self.conversations[key]
            for c in convs:
                if not thread and (not c.thread or not c.thread_inuse):
                    conv=c
                    break
                if thread and thread==c.thread:
                    conv=c
                    break
            if conv and conv.thread and not thread:
                conv.thread=None
            elif conv and thread:
                conv.thread_inuse=1

        if not conv:
            return 0

        conv.error(stanza)
        return 1

    def message_normal(self, stanza):
        #self.message_chat(stanza)
        fr=stanza.get_from()
        subject=stanza.get_subject()
        body=stanza.get_body()
        # 给Qomodev聊天室发送Bug报告
        if body:
            if fr.bare().as_utf8() == "bugs.linux-ren.org@jabber.org":
                room_jid=pyxmpp.JID(unicode("qomodev@conference.jabber.org"))
                if room_jid.resource or not room_jid.node:
                    self.xmppdog.error("Bad room JID")
                    return True
                rs=self.xmppdog.room_manager.get_room_state(room_jid)
                if rs and rs.joined:
                    room_handler=rs.handler
                    room_handler.room_state.send_message(body)
        return True

    def message_chat(self,stanza):
        fr=stanza.get_from()
        thread=stanza.get_thread()
        subject=stanza.get_subject()
        body=stanza.get_body()
        target = pyxmpp.JID(stanza.get_from())
        #if (stanza.get_from().bare().as_utf8() in self.xmppdog.admin):
        command = body.split()
        if (command[0] == ">room"):
            return self.cmd_room(stanza, command)
        elif (command[0] == ">fetch"):
            return self.cmd_fetch(stanza, command)
        if stanza.get_type()=="headline":
            # 'headline' messages should never be replied to
            return True
        #TODO:处理聊天室私聊信息:
        if fr.bare().as_unicode().find("conference") > 1:
            self.xmppdog.stream.send(Message(to_jid=target, body=body))
            return True

    def cmd_help (self):
        """
        Return help message.
        """
        lst=[]
        cmd=">room"
        sub_cmd=(
        "help            - this help message", 
        "nick <nick name> - set status", 
        "msg <message> -  send message to chatroom",
        "block <nick name> - block somebody", 
        "unblock <nick name> - unblock somebody", 
        )
        for i in sub_cmd:
            lst.append(" ".join([cmd, i]))
        return unicode("\n".join(lst), 'iso-8859-2')

    def cmd_room(self, stanza, command):
        fr=stanza.get_from()
        if command[1] == "msg" and len(command) > 1 :
            for rm_state in self.xmppdog.room_manager.rooms.values():
                rm_state.send_message((fr.bare().as_unicode().split("@")[0] + "->" + " ".join(command[2:])))

        if (fr.bare().as_unicode() not in self.xmppdog.admin):
            return

        target = pyxmpp.JID(stanza.get_from())
        if   len(command) == 1:
            msg = self.cmd_help()
            self.xmppdog.stream.send(Message(to_jid=target, body=msg))
        elif len(command) == 2:
            if (command[1] == "help"):
                msg = self.cmd_help()
                self.xmppdog.stream.send(Message(to_jid=target, body=msg))
        elif   len(command) == 3:
            if (command[1] == "nick"):
                for rm_state in self.xmppdog.room_manager.rooms.values():
                    rm_state.change_nick(command[2])
            elif (command[1] == "block"):
                for (room_id, room_nick ) in self.xmppdog.cfg.items("room"):
                    room_jid=pyxmpp.JID(unicode(room_id))
                    if room_jid.resource or not room_jid.node:
                        self.xmppdog.error("Bad room JID")
                        return True
                    rs=self.xmppdog.room_manager.get_room_state(room_jid)
                    if rs and rs.joined:
                        room_handler=rs.handler
                        room_handler.blockme.append(command[2])
                        msg=u"/me 忽略了 %s 的消息" % command[2]
                        room_handler.room_state.send_message(msg)
            elif (command[1] == "unblock"):
                for (room_id, room_nick ) in self.xmppdog.cfg.items("room"):
                    room_jid=pyxmpp.JID(unicode(room_id))
                    if room_jid.resource or not room_jid.node:
                        self.xmppdog.error("Bad room JID")
                        return True
                    rs=self.xmppdog.room_manager.get_room_state(room_jid)
                    if rs and rs.joined:
                        room_handler=rs.handler
                        room_handler.blockme.remove(command[2])
                        msg=u"/me 开始关注 %s 的消息" % command[2]
                        room_handler.room_state.send_message(msg)
        return True

    def cmd_fetch(self, stanza, command):
        fr=stanza.get_from().bare().as_unicode()
        target = pyxmpp.JID(stanza.get_from())
        if len(command) == 3:
            if (command[1] == "start"):
                room_jid=pyxmpp.JID(unicode(command[2]))
                if room_jid.resource or not room_jid.node:
                    self.xmppdog.error("Bad room JID")
                    return True
                rs=self.xmppdog.room_manager.get_room_state(room_jid)
                if rs and rs.joined:
                    room_handler=rs.handler
                    room_handler.fetchlist.append(fr)
                    msg=u"%s 订阅了本聊天室的消息" % fr
                    room_handler.room_state.send_message(msg)
            elif (command[1] == "stop"):
                room_jid=pyxmpp.JID(unicode(command[2]))
                if room_jid.resource or not room_jid.node:
                    self.xmppdog.error("Bad room JID")
                    return True
                rs=self.xmppdog.room_manager.get_room_state(room_jid)
                if rs and rs.joined:
                    room_handler=rs.handler
                    room_handler.fetchlist.remove(fr)
                    msg=u"%s 取消了订阅本聊天室的消息" % fr
                    room_handler.room_state.send_message(msg)
        return True

class Room(muc.MucRoomHandler):
    def __init__(self, room, me, app):
        muc.MucRoomHandler.__init__(self)
        self.room=room
        self.me=me
        self.xmppdog = app
        self.blockme=[]     #block 列表
        self.fetchlist=[]     #订阅本聊天室的jid列表
        self.deletechars="""` ~!@#$%^&*()={[}]:;"'<,>.?/|\\"""
        self.fparams={
            "room":self.room,
            "me":self.me,
        }

    def user_format_params(self,user):
        fparams=dict(self.fparams)
        fparams.update({
                "nick": user.nick,"jid": user.room_jid,
                "real_jid": user.real_jid, "role": user.role,
                "affiliation": user.affiliation,
                })
        if user.presence:
            fparams.update({
                    "show": user.presence.get_show(),
                    "status": user.presence.get_status(),
                    "available": user.presence.get_type()!="unavailable",
                    })
        else:
            fparams.update({
                    "show": u"",
                    "status": u"",
                    "available": False,
                    })
        return fparams

    def message_received(self,user,stanza):
        body=stanza.get_body()
        if not body:
            return
        if user:
            fparams=self.user_format_params(user)
        else:
            fparams=dict(self.fparams)
        d=delay.get_delay(stanza)
        if d:
            fparams["timestamp"]=d.get_datetime_local()
        if len(self.fetchlist) > 0:
            for i in self.fetchlist:
                target = pyxmpp.JID(i)
                msg = fparams["nick"] + ": " + body
                self.xmppdog.stream.send(Message(to_jid=target, body=msg))

        if body.startswith(u"/me "):
            fparams["msg"]=body[4:]
            return
        else:
            fparams["msg"]=body
        fr=stanza.get_from()
        if user is None:
            fparams["format"] = "muc.info"
            return
        elif fr==self.room_state.room_jid:
            fparams["format"] = "muc.me"
            return
        elif self.room_state.me.nick.lower() in body.lower():
            fparams["format"] = "muc.to_me"
        else:
            fparams["format"] = "muc.other"
        self.do_message(fparams)

    def do_message(self, fparams):
        if fparams.has_key("timestamp"):
            return
        #block msg from xmppdog.
        if fparams["nick"]=="xmppdog":
            return
        #td=datetime.datetime.now() - fparams["timestamp"]
        #if td.seconds > 10:
        if fparams["format"] == "muc.to_me":
            #block msg from xmppdog.
            #user = self.room_state.get_user(fparams['nick'], True)
            #if user.real_jid.resource.find("bot") >= 0:
            #    return
            self.cmd_callme(fparams)
        elif fparams["format"] == "muc.other":
            self.cmd_other(fparams)

    def cmd_callme(self, fparams):
        if fparams["nick"] in self.blockme:
            return
        fd = open(os.path.join(os.getcwd(), "random.txt"))
        talks = fd.readlines()
        import random,time
        random.seed(time.time())
        msg=u"%s: %s" % (fparams["nick"], talks[random.randint(0,len(talks)-1)][:-1].decode("utf-8"))
        self.room_state.send_message(msg)

    def send_priv_msg(self, nick, msg):
        user = self.room_state.get_user(nick, True)
        m=Message(to_jid=user.room_jid, stanza_type="chat", body=msg)
        self.xmppdog.stream.send(m)

    def cmd_other(self, fparams):
        if fparams["msg"].find("http://") >= 0 or fparams["msg"].find("https://") >= 0:
            if fparams["nick"] not in self.blockme:
                self.http_msg(fparams)
        if fparams["msg"].startswith(">date"):
            self.date_msg(fparams)
        if fparams["msg"].startswith(">blockme"):
            if fparams["nick"] not in self.blockme:
                self.blockme.append(fparams["nick"])
                msg=u"%s: 执行完毕，以后不再抓取你发的链接了" % fparams["nick"]
                self.room_state.send_message(msg)
        if fparams["msg"].startswith(">pkg"):
            args = fparams['msg'].split()
            if len(args) == 2:
                msg = self.pkg_info(args[1])
                self.send_priv_msg(fparams["nick"], msg)
        if fparams["msg"].startswith(">unblockme"):
            if fparams["nick"] in self.blockme:
                self.blockme.remove(fparams["nick"])
                msg=u"%s: 执行完毕，我将重新开始抓取你发的链接" % fparams["nick"]
                self.room_state.send_message(msg)
        if fparams["msg"].startswith(">ip"):
            args = fparams['msg'].split()
            if len(args) == 2:
                try:
                    Q=MQQWry()
                    msg=u"%s-> %s" % ( args[1], " ".join(Q[str(args[1])][2:]).decode("utf8") )
                except:
                    self.room_state.send_message(u"查询IP失败。")
                    return
                self.room_state.send_message(msg)
        if fparams["msg"].startswith(">help"):
            help = [
                    "",
                    ">help              显示帮助信息",
                    ">date              显示日期",
                    ">blockme           停止抓取自己发送的链接标题",
                    ">unblockme         恢复抓取自己发送的链接标题",
                    ">ip                查询ip地址",
                    ">weather <城市>    查询天气(未实现)",
                    ">version           显示xmppdog版本信息",
                    ">pkg    <pkg>      查询linux软件包",
                    ]
            msg = "\n".join(help)
            self.room_state.send_message(msg)
        if fparams["msg"].startswith(">version"):
            help = [
                    "",
                    "homepage: http://xmppdog.googlecode.com",
                    "$Revision$",
                    "$Date$",
                    ]
            msg = "\n".join(help)
            self.room_state.send_message(msg)
        elif fparams["msg"].startswith("~"):
            print "hello"

    def date_msg(self, fparams):
        import liblunar
        import time
        import locale

        locale.setlocale(locale.LC_ALL, "")
        t = time.localtime()
        l=liblunar.Date()
        l.set_solar_date(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour)
        tt = "%d:%d:%d" % (t.tm_hour, t.tm_min, t.tm_sec);
        format = "\n公历：%(YEAR)年%(MONTH)月%(DAY)日\n农历：%(NIAN)年%(YUE)月%(RI)日\n干支：%(Y60)年%(M60)月%(D60)日\n生肖：%(shengxiao)\n"
        self.room_state.send_message(l.strftime(format) + "时间：" + tt + l.strftime(" (%(SHI)时)\n今天是") + l.get_jieri(" "))

    def pkg_info(self, pkg):
        if os.path.exists("/usr/bin/apt-cache"):
            cmd = "apt-cache search %s"
        elif os.path.exists("/usr/bin/eix"):
            cmd = "eix -c %s"
        elif os.path.exists("/usr/bin/pacman"):
            cmd = "pacman -Ss %s"
        else:
            return "No support command found!"
        try:
            fd = os.popen(cmd % str(pkg).translate(None, self.deletechars));
            return fd.read()
        except:
            return "no result"
        
    def http_msg(self, fparams):
        import urllib2,re
        p0 = re.compile(r'.*(https?://[\w\-./%?=&]+[\w\-./%?=&]*).*', re.IGNORECASE|re.DOTALL)
        m1 = p0.match(fparams['msg'])
        if m1:
            try:
                print m1.group(1)
                headers = { 'User-Agent' : "Mozilla/5.0 (Windows; U; Windows NT 5.1; zh-CN; rv:1.9.0.1) Gecko/2008070208 Firefox/3.0.1"}
                req = urllib2.Request(m1.group(1), None, headers)
                d = urllib2.urlopen(req, timeout=3)
            except:
                msg = u"%s 无法打开此链接" % fparams["nick"]
                self.room_state.send_message(msg)
                return
            f=d.read(1024)
            p1=re.compile(r'.*?<title>(.*?)</title>.*?', re.IGNORECASE|re.DOTALL)
            title=p1.match(f)
            if title:
                title = title.group(1).translate(None, "\n\r")
                p2=re.compile('charset=(.*?)[\"]?/?>', re.IGNORECASE)
                code = p2.match(f)
                if code:
                    code = code.group(1).strip()
                    if code.endswith("\"") or code.endswith("'"):
                        code=code[:-1]
                    msg = u"%s 发链接了，标题是 [%s]" % (fparams["nick"], title.decode(code))
                    self.room_state.send_message(msg)
                else:
                    try:
                        msg = u"%s 发链接了，标题是 [%s]" % (fparams["nick"], title.decode("utf8"))
                        self.room_state.send_message(msg)
                    except:
                        try:
                            msg = u"%s 发链接了，标题是 [%s]" % (fparams["nick"], title.decode("gb18030"))
                            self.room_state.send_message(msg)
                        except:
                            msg = u"%s 发链接了，标题是 [%s]" % (fparams["nick"], title)
                            self.room_state.send_message(msg)
            else:
                msg = u"%s 报歉，我无法得到你发的链接标题" % fparams["nick"]
                self.room_state.send_message(msg)
        else:
            msg = u"烂 %s, 居然发个假链接来耍我" % fparams["nick"]
            self.room_state.send_message(msg)

# vi: sts=4 et sw=4
