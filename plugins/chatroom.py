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
import types

import pyxmpp
from pyxmpp.jabber import delay
from xmppdog.plugin import PluginBase
from pyxmpp.jabber import muc,delay
from pyxmpp.message import Message
from muc.room import Room

commands = {}
acommands = {}
commandchrs = "--"

class ADMIN_COMMAND(Exception):pass
class MSG_COMMAND(Exception):pass

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

    def get_room_by_mid(self, mid):
        room_jid=pyxmpp.JID(unicode(jid))
        if room_jid.resource or not room_jid.node:
            self.xmppdog.error("Bad room JID")
            return (None,None)
        rs=self.xmppdog.room_manager.get_room_state(room_jid)
        if rs and rs.joined:
            room_handler=rs.handler
        else:
            room_handler=Room(room_jid, self.xmppdog.stream.me, self.xmppdog)
            self.xmppdog.room_manager.join(room_jid, room_nick, room_handler)
        return (rs, room_handle)

    def send_to_mid_room(self, mid, msg):

        (rs, handle) = self.get_room_by_mid(mid)
        handler.room_state.send_message(msg)
        handler.room_state.leave()
        self.xmppdog.room_manager.forget(rs)

    def send_to_room(self, msg, room=None, sender=None):
        if sender is not None:
            msg = "%s -> %s" % (sender, msg)

        for rm_state in self.xmppdog.room_manager.rooms.values():
            rm_jid = rm_state.get_room_jid()
            if room is None:
                rm_state.send_message(msg)
            elif rm_jid.startswith(room):
                rm_state.send_message(msg)

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
        body=stanza.get_body()
        if body:
            ##如果消息来之bugs.linux-ren.org,那么将其转发到qomodev聊天室中
            if self.get_jid(stanza) == "bugs.linux-ren.org@jabber.org":
                for mid in ("qomodev@conference.jabber.org", "qomodev@conference.jaim.at"):
                    self.send_to_mid_room(mid, body)
        return True

    def message_chat(self,stanza):
        if stanza.get_type()=="headline":
            # 'headline' messages should never be replied to
            return True

        # process message from chatroom by someone
        if self.is_room_msg(stanza):
            body=stanza.get_body()
            if body.startswith(commandchrs):
                self.cmd(stanza)
        else:
            return True

    def cmd(self, stanza):

        body = stanza.get_body()

        if " " in body:
            cmd, msg=body.split(" ",1)
        else:
            cmd, msg=body.strip(),""
        cmd = cmd[len(commandchrs):].lower()
        func = None
        try:
            if commands.has_key(cmd):
                func = commands[cmd]
                func(self, stanza, msg)
            elif acommands.has_key(cmd):
                func = acommands[cmd]
                func(self, stanza, msg)
            else:
                self.send_to_one(stanza, 'Unknown command "%s".' % cmd)
        except ADMIN_COMMAND:
            self.send_to_one(stanza, 'This is admin command, you have no permision to use.')
        except MSG_COMMAND:
            self.send_to_one(stanza, func.__doc__)

#########################################################

def cmd_msg(myself, stanza, msg):
    "[room_jid] <message> -  向聊天室(room_jid)发送消息"

    if " " in msg:
        mid, m = msg.split(" ",1)
    else:
        m, mid = msg.strip(),None

    jid = stanza.get_from_jid()
    nick = jid.as_unicode().split("/")[-1]
    msg = "%s -> %s" % (nick, m)

    for rm_state in myself.xmppdog.room_manager.rooms.values():
        rm_jid = rm_state.get_room_jid().as_unicode()
        if mid is None:
            rm_state.send_message(msg)
        elif rm_jid.startswith(mid):
            rm_state.send_message(msg)

def cmd_nick(myself, stanza, msg):
    "[room_jid] <nickname> - 修改xmppdog在聊天室(room_jid)中的昵称"

    if " " in msg:
        mid, nick=msg.split(" ",1)
    else:
        nick, mid=msg.strip(),None

    for rm_state in myself.xmppdog.room_manager.rooms.values():
        rm_jid = rm_state.get_room_jid().as_unicode()
        if mid is None:
            rm_state.change_nick(nick)
        elif rm_jid.startswith(mid):
            rm_state.change_nick(nick)

def cmd_block(myself, stanza, msg):
    "[room_jid] <nick name> - 在聊天室中禁止对<nick>的消息响应"

    if " " in msg:
        mid, nick=msg.split(" ",1)
    else:
        nick, mid=msg.strip(),None

    for rm_state in myself.xmppdog.room_manager.rooms.values():
        rm_jid = rm_state.get_room_jid().as_unicode()
        if mid is None:
            if nick not in rm_state.handler.blockme:
                rm_state.handler.blockme.append(nick)
                msg=u"/me 忽略了 %s 的消息" % nick
                rm_state.handler.room_state.send_message(msg)
            else:
                myself.send_to_one(stanza, u"%s 已经被忽略了" % nick)
        elif rm_jid.startswith(mid):
            if nick not in rm_state.handler.blockme:
                rm_state.handler.blockme.append(nick)
                msg=u"/me 忽略了 %s 的消息" % nick
                rm_state.handler.room_state.send_message(msg)
            else:
                myself.send_to_one(stanza, u"%s 已经被忽略了" % nick)

def cmd_unblock(myself, stanza, msg):
    "[room_jid] <nick name> - 在聊天室中恢复对<nick>的消息响应"

    if " " in msg:
        mid, nick=msg.split(" ",1)
    else:
        nick, mid=msg.strip(),None

    for rm_state in myself.xmppdog.room_manager.rooms.values():
        rm_jid = rm_state.get_room_jid().as_unicode()
        if mid is None:
            if nick in rm_state.handler.blockme:
                rm_state.handler.blockme.remove(nick)
                msg=u"/me 开始关注 %s 的消息" % nick
                rm_state.handler.room_state.send_message(msg)
            else:
                myself.send_to_one(stanza, u"%s 没有被忽略" % nick)
        elif rm_jid.startswith(mid):
            if nick in rm_state.handler.blockme:
                rm_state.handler.blockme.remove(nick)
                msg=u"/me 开始关注 %s 的消息" % nick
                rm_state.handler.room_state.send_message(msg)
            else:
                myself.send_to_one(stanza, u"%s 没有被忽略" % nick)

def cmd_fetch(myself, stanza, msg):
    "[room_jid] <nick name> - 设置<nick>订阅聊天室(room_jid)消息"

    if " " in msg:
        mid, nick=msg.split(" ",1)
    else:
        nick, mid=msg.strip(),None

    for rm_state in myself.xmppdog.room_manager.rooms.values():
        rm_jid = rm_state.get_room_jid().as_unicode()
        if mid is None:
            if nick not in rm_state.handler.fetchlist:
                rm_state.handler.fetchlist.append(nick)
                msg=u"/me %s 订阅了本聊天室的消息" % nick
                rm_state.handler.room_state.send_message(msg)
            else:
                myself.send_to_one(stanza, u"%s 已经订阅过聊天室消息" % nick)
        elif rm_jid.startswith(mid):
            if nick not in rm_state.handler.fetchlist:
                rm_state.handler.fetchlist.append(nick)
                msg=u"/me %s 订阅了本聊天室的消息" % nick
                rm_state.handler.room_state.send_message(msg)
            else:
                myself.send_to_one(stanza, u"%s 已经订阅过聊天室消息" % nick)

def cmd_unfetch(myself, stanza, msg):
    "[room_jid] <nick name> - 取消<nick>订阅聊天室(room_jid)消息"

    if " " in msg:
        mid, nick=msg.split(" ",1)
    else:
        nick, mid=msg.strip(),None

    for rm_state in myself.xmppdog.room_manager.rooms.values():
        rm_jid = rm_state.get_room_jid().as_unicode()
        if mid is None:
            if nick in rm_state.handler.fetchlist:
                rm_state.handler.fetchlist.remove(nick)
                msg=u"/me %s 取消了订阅本聊天室的消息" % nick
                rm_state.handler.room_state.send_message(msg)
            else:
                myself.send_to_one(stanza, u"%s 没有订阅过聊天室消息" % nick)
        elif rm_jid.startswith(mid):
            if nick in rm_state.handler.fetchlist:
                rm_state.handler.fetchlist.remove(nick)
                msg=u"/me %s 取消了订阅本聊天室的消息" % nick
                rm_state.handler.room_state.send_message(msg)
            else:
                myself.send_to_one(stanza, u"%s 没有订阅过聊天室消息" % nick)

def cmd_help(myself, stanza, msg):
    "显示帮助信息"

    msg = 'Commands: \n%s' % commandchrs + commandchrs.join(["%-20s%s\n" % (x, unicode(y.__doc__, "utf8") or "") for x, y in commands.items()])
    if myself.is_admin(stanza):
        msg =  msg + 'Admin Commands: \n%s' % commandchrs + commandchrs.join(["%-20s%s\n" % (x, unicode(y.__doc__, "utf8") or "") for x, y in acommands.items()])
    myself.send_to_one(stanza, msg)

#########################################################

for i, func in globals().items():
    if isinstance(func, types.FunctionType):
        if i.startswith('cmd_'):
            commands[i.lower()[4:]] = func
        elif i.startswith('acmd_'):
            acommands[i.lower()[5:]] = func

# vi: sts=4 et sw=4
