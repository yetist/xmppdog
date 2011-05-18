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
from muc.room import Room

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
                for cm in ("qomodev@conference.jabber.org", "qomodev@conference.jaim.at"):
                    room_jid=pyxmpp.JID(unicode(cm))
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
        if (command[0] == "--room"):
            return self.cmd_room(stanza, command)
        elif (command[0] == "--fetch"):
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
        cmd="--room"
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

# vi: sts=4 et sw=4
