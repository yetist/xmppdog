#! /usr/bin/env python
# -*- encoding:utf-8 -*-
# FileName: admin.py

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
from pyxmpp.all import JID,Iq,Presence,Message,StreamError
from pyxmpp.jabber import delay
from xmppdog.plugin import PluginBase
from pyxmpp.interface import implements
from pyxmpp.interfaces import *

class Plugin(PluginBase):
    def __init__(self, app, name):
        PluginBase.__init__(self,app,name)

    def unload(self):
        return True

    def session_started(self,stream):
        self.xmppdog.stream.set_message_handler("chat",self.message_chat)
        self.xmppdog.stream.set_message_handler("normal",self.message_normal)

    def message_normal(self,stanza):
        fr=stanza.get_from()
        thread=stanza.get_thread()
        subject=stanza.get_subject()
        body=stanza.get_body()
        if not subject and not body:
            return
        if body is None:
            body=u""
        d=delay.get_delay(stanza)
        if d:
            timestamp=d.get_datetime_local()
        else:
            timestamp=None
        print "here", body

    def message_chat(self, stanza):
        """
        Handle incomming chat message.
        """ 
        print "msg from admin"
        subject=stanza.get_subject()
        body=stanza.get_body()
        t=stanza.get_type()
        print u'Message from %s received.' % (unicode(stanza.get_from(),)),
        if subject:
            print u'Subject: "%s".' % (subject,),
        if body:
            print u'Body: "%s".' % (body,),
        if t:
            print u'Type: "%s".' % (t,)
        else:
            print u'Type: "normal".' % (t,)
        if stanza.get_type()=="headline":
            # 'headline' messages should never be replied to
            return True
        if subject:
            subject=u"Re: "+subject
        if body:
            if (stanza.get_from().bare().as_utf8() == self.xmppdog.admin):
                command = body.split()
                if (command[0] == ">admin"):
                    return self.cmd_admin(stanza, command)
        print "msg end admin"
        return True

    def cmd_admin(self, stanza, command):
        target = JID(stanza.get_from())
        if   len(command) == 1:
            msg = self.cmd_help()
            self.xmppdog.stream.send(Message(to_jid=target, body=msg))
        elif len(command) == 2:
            if (command[1] == "help"):
                msg = self.cmd_help()
                self.xmppdog.stream.send(Message(to_jid=target, body=msg))
        elif   len(command) == 3:
            if (command[1] == "status"):
                # 此处设置状态工作不正常。
                #p = Presence(command[2])
                #return [p]
                pass
        return True

    def cmd_help(self):
        """
        Return help message.
        """
        lst=[]
        cmd="/admin"
        sub_cmd=(
        "help            - this help message", 
        "status [status] - set status", 
        )
        for i in sub_cmd:
            lst.append(" ".join([cmd, i]))
        return unicode("\n".join(lst), 'iso-8859-2')

# vi: sts=4 et sw=4
