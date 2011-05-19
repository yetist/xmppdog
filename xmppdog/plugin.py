#! /usr/bin/env python
# -*- encoding:utf-8 -*-
# FileName: plugin.py

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

import logging
import pyxmpp

class PluginBase:
    def __init__(self, app, name):
        """
        Initialize the plugin.
        """
        print "call PluginBase"
        self.settings={}
        self.available_settings={}
        self.xmppdog = app
        self.name=name
        self.module=None
        self.sys_path=None
        self.logger=logging.getLogger("xmppdog.plugin."+name)
        self.debug=self.logger.debug
        self.info=self.logger.info
        self.warning=self.logger.warning
        self.error=self.logger.error
        print "leav PluginBase"

    def cmd_help(self):
        return " "

    def read_cfg(self):
        pass

    def unload(self):
        """
        Unregister every handler installed etc. and return True if the plugin
        may safely be unloaded.
        """
        return False

    def session_started(self,stream):
        """
        Stream-related plugin setup (stanza handler registration, etc).
        """
        pass

    def session_ended(self,stream):
        """
        Called when a session is closed (the stream has been disconnected).
        """
        pass

    def is_admin(self, stanza):
        jid = self.get_jid(stanza)
        return jid in self.xmppdog.admin

    def get_jid(self, stanza):
        fr=stanza.get_from()
        jid = fr.bare().as_unicode()
        return jid

    def send_to_jid(self, jid, msg):
        target = pyxmpp.JID(jid)
        #m = pyxmpp.message.Message(to_jid=target,  stanza_type="chat", body=msg)
        m = pyxmpp.message.Message(to_jid=target, body=msg)
        return self.xmppdog.stream.send(m)

    def send_to_one(self, stanza, msg):
        target = pyxmpp.JID(stanza.get_from())
        m = pyxmpp.message.Message(to_jid=target, body=msg)
        self.xmppdog.stream.send(m)

    def is_room_msg(self, stanza):
        jid = self.get_jid(stanza)
        if jid.find("conference") > 1:
            return True
        else:
            return False

# vi: sts=4 et sw=4
