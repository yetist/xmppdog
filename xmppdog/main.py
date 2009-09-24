#! /usr/bin/env python
# -*- encoding:utf-8 -*-
# FileName: main.py

"This file is part of xmppdog"
 
__author__   = "yetist"
__copyright__= "Copyright (C) 2009 yetist <wuxiaotian@redflag-linux.com>"
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

import ConfigParser
import sys, os
import string
import time
import traceback

import pyxmpp
from pyxmpp.all import JID,Iq,Presence,Message,StreamError
from pyxmpp.jabber.client import JabberClient
from pyxmpp.jabber import delay

class Application(JabberClient):
    """ Application class """
    def __init__(self, base_dir, config_file):
        """ Initialize the application. """
        self.configFile = config_file
        self.show_debug = None
        self.show_info = None
        self.admin = None
        self.jid = None
        self.password = None
        self.cfg = ConfigParser.ConfigParser()
        self.read_cfg()
        self.base_dir = base_dir
        home = os.environ.get("HOME", "")
        self.home_dir = os.path.join(home, ".xmppdog")
        self.plugin_dirs = [os.path.join(base_dir, "plugins"),
                            os.path.join(self.home_dir, "plugins")]
        self.plugins = {}
        self.plugin_modules = {}
        self.room_manager=None

#        # if bare JID is provided add a resource -- it is required
#        if not jid.resource:
#            jid=JID(jid.node, jid.domain, "xmppdog")
#
#        # setup client with provided connection information
#        # and identity data
#        JabberClient.__init__(self, jid, password,
#                disco_name="XMPP Bot: xmppdog", disco_type="bot")
#
#        # add the separate components
#        self.interface_providers = [
#            VersionHandler(self),
#            EchoHandler(self),
#            ]

    def read_cfg(self):
        """ Read application config file. """
        self.cfg.read(self.configFile)
        self.show_debug = (self.cfg.get('base','show_debug') == "1")
        self.show_info = (self.cfg.get('base','show_info') == "1")
        self.admin = self.cfg.get('base', 'admin')
        self.jid = JID(self.cfg.get('login', 'user'),
                       self.cfg.get('login', 'host'),
                       self.cfg.get('login', 'resource')
                      )
        self.password = unicode(self.cfg.get('login', 'pass'), 'iso-8859-2')
        self.auth_methods = string.split(self.cfg.get('login', 'auth_methods'))
        
    def run(self):
        """ 
        Connect and run the application main loop. 
        """
        try:
            self.load_plugins() 
            self.debug("creating stream...")
            JabberClient.__init__(self,
                                   jid = self.jid,
                                   password = self.password,
                                   auth_methods = self.auth_methods
                                  )
            self.debug("connecting...")
            self.connect()
            self.debug("processing...")
            
            try:
                self.loop(1)
            finally:
                if self.stream:
                    self.disconnect()
        except KeyboardInterrupt:
            self.info("Quit request")
            self.exit()
        except StreamError:
            raise
    
    def _load_plugin(self, name):
        """ 
        Load the plugin. 
        """
        try:
            mod = self.plugin_modules.get(name)
            if mod:
                mod = reload(mod)
            else:
                mod = __import__(name)
            plugin = mod.Plugin(self, name)
            plugin.module = mod
            plugin.sys_path = sys.path
            self.plugins[name] = plugin
            self.plugin_modules[name] = mod
        except StandardError:
            self.print_exception()
            self.info("Plugin load failed")

    def load_plugin(self, name):
        """ 
        Find a plugin in filesystem and load it. 
        """
        sys_path = sys.path
        try:
            for path in self.plugin_dirs:
                sys.path = [path] + sys_path
                plugin_file = os.path.join(path, name + ".py")
                if not os.path.exists(plugin_file):
                    continue
                if self.plugins.has_key(name):
                    self.error("Plugin %s already loaded!" % (name,))
                    return
                self.info("Loading plugin %s..." % (name,))
                self._load_plugin(name)
                return
            self.error("Couldn't find plugin %s" % (name,))
        except StandardError:
            sys.path = sys_path

    def load_plugins(self):
        """ 
        Find all plugins in plugin paths and load them. 
        """
        sys_path = sys.path
        try:
            for path in self.plugin_dirs:
                sys.path = [path] + sys_path
                try:
                    directory = os.listdir(path)
                except (OSError,IOError),error:
                    self.debug("Couldn't get plugin list: %s" % (error,))
                    self.info("Skipping plugin directory %s" % (path,))
                    continue
                self.info("Loading plugins from %s:" % (path,))
                for plugin_file in directory:
                    if (plugin_file[0] == "." or 
                        not plugin_file.endswith(".py") 
                        or plugin_file == "__init__.py"):
                        continue
                    name = os.path.join(plugin_file[:-3])
                    if not self.plugins.has_key(name):
                        self.info("  %s" % (name,))
                        self._load_plugin(name)
        except StandardError:
            sys.path = sys_path

    def unload_plugin(self, name):
        """ 
        Unload the plugin. 
        """
        try:
            plugin = self.plugins[name]
        except KeyError:
            self.error("Plugin %s is not loaded" % (name,))
            return False
        self.info("Unloading plugin %s..." % (name,))
        try:
            ret = plugin.unload()
        except StandardError:
            ret = None
        if not ret:
            self.error("Plugin %s cannot be unloaded" % (name,))
            return False
        del self.plugins[name]
        return True
    
    def unload_plugins(self):
        """ 
        Unload all loaded plugins. 
        """
        loaded_plugins = {}
        for plugin in self.plugins:
            loaded_plugins[plugin] = plugin
        for plugin in loaded_plugins:
            self.unload_plugin(plugin)
    
    def reload_plugin(self, name):
        """ 
        Reload the plugin. 
        """
        self.unload_plugin(name)
        self.load_plugin(name)
        self.get_plugin(name).session_started(self.stream)
        
    def get_plugin(self, name):
        """ 
        Return reference to plugin. 
        """
        return self.plugins[name]

    def stream_state_changed(self,state,arg):
        """This one is called when the state of stream connecting the component
        to a server changes. This will usually be used to let the user
        know what is going on."""
        print "*** State changed: %s %r ***" % (state,arg)

    def print_roster_item(self,item):
        print "call print_roster_item"
        if item.name:
            name=item.name
        else:
            name=u""
        print (u'%s "%s" subscription=%s groups=%s'
                % (unicode(item.jid), name, item.subscription,
                    u",".join(item.groups)) )

    def roster_updated(self,item=None):
        print "call roster_updated"
        if not item:
            print u"My roster:"
            for item in self.roster.get_items():
                self.print_roster_item(item)
            return
        print u"Roster item updated:"
        self.print_roster_item(item)

    def idle(self):
        stream=self.get_stream()
        if stream:
            stream.idle()

#    def session_started(self):
#        self.request_roster()
#        p=Presence()
#        self.stream.send(p)
#        self.room_manager=muc.MucRoomManager(self.stream)
#        self.room_manager.set_handlers()
#        for room_id in conf.room.keys():
#            room_jid=pyxmpp.JID(unicode(room_id))
#            if room_jid.resource or not room_jid.node:
#                self.error("Bad room JID")
#                return
#            rs=self.room_manager.get_room_state(room_jid)
#            if rs and rs.joined:
#                room_handler=rs.handler
#            else:
#                room_handler=Room(conf, room_jid, self.stream.me)
#                self.room_manager.join(room_jid, conf.room[room_id], room_handler)

    def cmd_sudo(self, stanza, command):
        print "command is :", command
        target = JID(stanza.get_from())
        if   len(command) == 1:
            msg = self.cmd_help()
            self.stream.send(Message(to_jid=target, body=msg))
        elif len(command) == 2:
            if (command[1] == "down"):
                self.exit()
            elif (command[1] == "help"):
                msg = self.cmd_help()
                self.stream.send(Message(to_jid=target, body=msg))
        elif len(command) == 3:
            if (command[1] == "reload" and command[2] == "config"):
                self.read_cfg()
                self.stream.send(Message(to_jid=target, 
                    body=u'config reloaded'))
                for plugin in self.plugins.values():
                    try:
                        plugin.read_cfg()
                    except StandardError:
                        self.print_exception()
                        self.info("Plugin call failed")
            elif (command[1] == "list" and command[2] == "plugins"):
                msg = 'current plugins are:\n' + "\n".join(self.plugins.keys())
                self.stream.send(Message(to_jid=target, body=msg))
        elif len(command) == 4:
            plugin = command[3]
            if (command[1] == "load" and command[2] == "plugin"):
                self.load_plugin(plugin)
                self.get_plugin(plugin).session_started(self.stream)
                msg = 'plugin ' + plugin + ' successfully loaded' 
                self.stream.send(Message(to_jid=target, body=msg))
            elif (command[1] == "reload" and command[2] == "plugin"):
                self.reload_plugin(plugin)
                msg = 'plugin ' + plugin + ' successfully reloaded' 
                self.stream.send(Message(to_jid=target, body=msg))
            elif (command[1] == "unload" and command[2] == "plugin"):
                self.unload_plugin(plugin)
                msg = 'plugin ' + plugin + ' successfully unloaded' 
                self.stream.send(Message(to_jid=target, body=msg))
    
    def message_chat(self, stanza):
        """
        Handle incomming chat message.
        """ 
        if (stanza.get_from().bare().as_utf8() == self.admin):
            process = True
            message_delay = delay.get_delay(stanza)
            if (message_delay 
                and
                message_delay.reason == "Offline Storage"
               ):
                self.info("Ingnoring offline message from " + \
                    message_delay.fr.as_string() + ": " + stanza.get_body()
                   )
                process = False
            body=stanza.get_body()
            if process and body:
                command = body.split()
                if (command[0] == "/sudo"):
                    self.cmd_sudo(stanza, command)
               # elif (command[0] == "/help"):
               #     msg = self.cmd_help()
               #     self.stream.send(Message(to_jid=target, body=msg))
                else:
                    self.plugins_message_chat(stanza)
        return 1

    def plugins_message_chat(self, stanza):
        """
        Call plugin handler for incomming chat message.
        """ 
        for plugin in self.plugins.values():
            try:
                plugin.message_chat(stanza)
            except StandardError:
                self.print_exception()
                self.info("Plugin call failed")

    def plugins_message_normal(self, stanza):
        """
        Call plugin handler for incomming normal message.
        """ 
        self.debug(u'Normal message from %r ' % (stanza.get_from()))
        for plugin in self.plugins.values():
            try:
                plugin.message_normal(stanza)
            except StandardError:
                self.print_exception()
                self.info("Plugin call failed")

    def session_started(self):
        """
        Stream-related plugin setup (stanza handler registration, etc).
        Send bot presence, set message handler for chat message
        and call session_started for all loaded plugins.
        """ 
        presence = Presence();
        presence.set_priority(20);
        self.stream.send(presence)
        self.stream.set_message_handler("chat", self.message_chat)
        self.stream.set_message_handler("normal", self.plugins_message_normal)
        
        for plugin in self.plugins.values():
            try:
                plugin.session_started(self.stream)
            except StandardError:
                self.print_exception()
                self.info("Plugin call failed")

    def print_exception(self):
        """
        Print exception.
        """ 
        traceback.print_exc(file = sys.stderr)
        
    def stream_state_changed(self, state, arg):
        """
        Print info about state changes.
        """ 
        if state == "resolving":
            self.info("Resolving %r..." % (arg,))
        if state == "resolving srv":
            self.info("Resolving SRV for %r on %r..." % (arg[1], arg[0]))
        elif state == "connecting":
            self.info("Connecting to %s:%i..." % (arg[0], arg[1]))
        elif state == "connected":
            self.info("Connected to %s:%i." % (arg[0], arg[1]))
        elif state == "authenticating":
            self.info("Authenticating as %s..." % (arg,))
        elif state == "binding":
            self.info("Binding to resource %s..." % (arg,))
        elif state == "authorized":
            self.info("Authorized as %s." % (arg,))
        elif state == "tls connecting":
            self.info("Doing TLS handhake with %s." % (arg,))
    
    def cmd_help(self):
        """
        Return help message.
        """
        lst=[]
        cmd="/sudo"
        sub_cmd=("help", "down", 
        "reload config", 
        "list plugins", 
        "unload plugin plugin_name",
        "reload plugin plugin_name",
        "load plugin plugin_name")
        for i in sub_cmd:
            lst.append(" ".join([cmd, i]))
        return unicode("\n".join(lst), 'iso-8859-2')
#        for plugin in self.plugins.values():
#            try:
#                lst.append(plugin.cmd_help())
#            except StandardError:
#                self.print_exception()
#                self.info("Plugin call failed")
#        msg = unicode("\n".join(lst))
#        self.stream.send(Message(to_jid=target, body=msg))
    
    def error(self, error_text):
        """
        Print error.
        """ 
        print "ERROR: " + error_text.encode("utf-8", "replace")
        
    def info(self, info_text):
        """
        Print info.
        """ 
        if self.show_info:
            print "INFO: " + info_text.encode("utf-8", "replace")
    
    def debug(self, debug_text):
        """
        Print debug information.
        """ 
        if self.show_debug:
            print "DEBUG: " + debug_text.encode("utf-8", "replace")
    
    def exit(self):
        """
        Disconnect and exit.
        """ 
        self.unload_plugins()
        if self.stream:
            self.info(u"Disconnecting...")
            self.lock.acquire()
            self.stream.disconnect()
            self.stream.close()
            self.stream = None
            self.lock.release()
            time.sleep(1)

def main(base_dir):
    """
    Run the application.
    """ 
    #libxml2.debugMemory(1)
    
    app = Application(base_dir, 'xmppdog.cfg')
    
    app.run()
    
    #libxml2.cleanupParser()
    #if libxml2.debugMemory(1) == 0:
    #    print "OK"
    #else:
    #    print "Memory leak %d bytes" % (libxml2.debugMemory(1))
    #    libxml2.dumpMemory()

# vi: sts=4 et sw=4
