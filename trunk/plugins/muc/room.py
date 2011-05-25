#! /usr/bin/env python
# -*- encoding:utf-8 -*-
# FileName: room.py

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
from pyxmpp.jabber import muc,delay
from cmds import commands, acommands, commandchrs
from pyxmpp.message import Message
import pyxmpp
import random,time

class ADMIN_COMMAND(Exception):pass
class MSG_COMMAND(Exception):pass

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

    def send2room(self, msg):
        self.room_state.send_message(msg)

    def send2nick(self, nick, msg):
        user = self.room_state.get_user(nick, True)
        m=Message(to_jid=user.room_jid, stanza_type="chat", body=msg)
        self.xmppdog.stream.send(m)

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
                print i, target
                msg = fparams["nick"] + ": " + body
                #self.send2nick(fparams['nick'], msg)
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
            user = self.room_state.get_user(fparams['nick'], True)
            print user.real_jid.resource
            #if user.real_jid.resource.find("bot") >= 0:
            #    return
            self.msg_callme(fparams)
        elif fparams["msg"].find("http://") >= 0 or fparams["msg"].find("https://") >= 0:
            if fparams["nick"] not in self.blockme:
                self.msg_http(fparams)
        elif fparams["msg"].startswith(commandchrs):
            self.cmd(fparams)

    def cmd(self, fparams):

        if " " in fparams['msg']:
            cmd, msg=fparams['msg'].split(" ",1)
        else:
            cmd, msg=fparams['msg'].strip(),""
        cmd = cmd[len(commandchrs):].lower()
        func = None
        try:
            if commands.has_key(cmd):
                func = commands[cmd]
                func(self, fparams)
            elif acommands.has_key(cmd):
                func = acommands[cmd]
                func(self, fparams)
            else:
                self.send2room('Unknown command "%s".' % cmd)
        except ADMIN_COMMAND:
            self.send2room('This is admin command, you have no permision to use.')
        except MSG_COMMAND:
            self.send2room(func.__doc__)

##################### 群聊锁定消息／命令处理 ####################################

    def msg_callme(self, fparams):
        if fparams["nick"] in self.blockme:
            return
        if self.xmppdog.talks.has_key('random'):
            talks = self.xmppdog.talks['random']
            random.seed(time.time())
            msg=u"%s: %s" % (fparams["nick"], talks[random.randint(0,len(talks)-1)][:-1].decode("utf-8"))
            self.room_state.send_message(msg)

    def msg_http(self, fparams):
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

##################### 群聊锁定消息／命令处理 ####################################

if __name__=="__main__":
    pass
