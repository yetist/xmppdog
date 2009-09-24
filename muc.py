#!/usr/bin/python -u
# -*- encoding:utf-8 -*-
import pyxmpp
from pyxmpp.jabber import muc,delay
import datetime

class Room(muc.MucRoomHandler):
    def __init__(self, conf, room, me):
        muc.MucRoomHandler.__init__(self)
        self.room=room
        self.me=me
        self.conf=conf
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
        print type(fparams)
        if fparams.has_key("timestamp"):
            return
        #td=datetime.datetime.now() - fparams["timestamp"]
        #if td.seconds > 10:
        if fparams["format"] == "muc.to_me":
            self.cmd_callme(fparams)
        elif fparams["format"] == "muc.other":
            self.cmd_other(fparams)

    def cmd_callme(self, fparams):
        talks=[u"找我什么事？",
                u"别来烦我,好不好？",
                u"我很忙，一会儿聊",
                u"What can I help you?",
                u"你是不是闲得没事干？",
                u"正在看片，现在没功夫聊天",
                u"你刚才说什么？",
                u"主人你好,有什么可以效劳的？",
                u"没明白你什么意思，再说一遍好吗？",
                u"想和我说话了"]
        import random,time
        random.seed(time.time())
        msg=u"%s: %s" % (fparams["nick"], talks[random.randint(0,len(talks)-1)])
        self.room_state.send_message(msg)

    def cmd_other(self, fparams):
        if fparams["msg"].find("http://") >= 0:
            self.http_msg(fparams)
        elif fparams["msg"].startswith("~"):
            print "hello"

    def http_msg(self, fparams):
        import urllib2,re
        p0 = re.compile(r'.*(http://[\w\-./%?=&]+[\w\-./%?=&]*).*', re.IGNORECASE|re.DOTALL)
        m1 = p0.match(fparams['msg'])
        if m1:
            try:
                print m1.group(1)
                headers = { 'User-Agent' : "Mozilla/5.0 (Windows; U; Windows NT 5.1; zh-CN; rv:1.9.0.1) Gecko/2008070208 Firefox/3.0.1"}
                req = urllib2.Request(m1.group(1), None, headers)
                d = urllib2.urlopen(req)
                #d=urllib2.urlopen(m1.group(1))
            except:
                msg = u"%s 无法打开此链接" % fparams["nick"]
                self.room_state.send_message(msg)
                return
            f=d.read(1024)
            p1=re.compile(r'.*?<title>(.*?)</title>.*?', re.IGNORECASE|re.DOTALL)
            title=p1.match(f)
            if title:
                title = title.group(1)
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

class Rooms(muc.MucRoomHandler):
    def __init__(self,room,me):
        muc.MucRoomHandler.__init__(self)
        self.room=room
        self.me=me
        self.fparams={
            "room":self.room,
            "me":self.me,
        }
        print self.me

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
        print body
        if not body:
            return
        if user:
            fparams=self.user_format_params(user)
        else:
            fparams=dict(self.fparams)
        d=delay.get_delay(stanza)
        if d:
            fparams["timestamp"]=d.get_datetime_local()
        if body.startswith(u"/me "):
            fparams["msg"]=body[4:]
            return
        else:
            fparams["msg"]=body
        fr=stanza.get_from()
        if user is None:
            self.buffer.append_themed("muc.info",fparams)
            self.buffer.update()
            return
        elif fr==self.room_state.room_jid:
            format="muc.me"
        elif self.room_state.me.nick.lower() in body.lower():
            format="muc.to_me"
        else:
            format="muc.other"

    def subject_changed(self,user,stanza):
        if user:
            fparams=self.user_format_params(user)
        else:
            fparams=dict(self.fparams)
        if user:
            fparams["msg"]=(u"%s has changed the subject to: %s"
                    % (user.nick,self.room_state.subject))
        else:
            fparams["msg"]=(u"The subject has been changed to: %s"
                    % (self.room_state.subject,))
        d=delay.get_delay(stanza)
        if d:
            fparams["timestamp"]=d.get_datetime_local()
        return

    def user_joined(self, user, stanza):
        fparams = self.user_format_params(user)
        d = delay.get_delay(stanza)
        if d:
            fparams["timestamp"] = d.get_datetime_local()
        print fparams
        return

    def user_left(self,user,stanza):
        fparams=self.user_format_params(user)
        if stanza:
            d=delay.get_delay(stanza)
            if d:
                fparams["timestamp"]=d.get_datetime_local()
        if user.same_as(self.room_state.me):
            self.buffer.append_themed("muc.me_left",fparams)
        else:
            self.buffer.append_themed("muc.left",fparams)
        self.buffer.update()
        return

    def role_changed(self,user,old_role,new_role,stanza):
        fparams=self.user_format_params(user)
        d=delay.get_delay(stanza)
        if d:
            fparams["timestamp"]=d.get_datetime_local()
        if user.same_as(self.room_state.me):
            self.buffer.append_themed("muc.my_role_changed",fparams)
        else:
            self.buffer.append_themed("muc.role_changed",fparams)
        self.buffer.update()
        return

    def affiliation_changed(self,user,old_affiliation,new_affiliation,stanza):
        fparams=self.user_format_params(user)
        d=delay.get_delay(stanza)
        if d:
            fparams["timestamp"]=d.get_datetime_local()
        if user.same_as(self.room_state.me):
            self.buffer.append_themed("muc.my_affiliation_changed",fparams)
        else:
            self.buffer.append_themed("muc.affiliation_changed",fparams)
        self.buffer.update()
        return

    def nick_change(self,user,new_nick,stanza):
        self.buffer.append_themed("debug","Nick change started: %r -> %r" % (user.nick,new_nick))
        return True

    def nick_changed(self,user,old_nick,stanza):
        fparams=self.user_format_params(user)
        fparams["old_nick"]=old_nick
        d=delay.get_delay(stanza)
        if d:
            fparams["timestamp"]=d.get_datetime_local()
        if user.same_as(self.room_state.me):
            self.buffer.append_themed("muc.my_nick_changed",fparams)
        else:
            self.buffer.append_themed("muc.nick_changed",fparams)
        self.buffer.update()
        return

    def presence_changed(self,user,stanza):
        fr=stanza.get_from()
        available=stanza.get_type()!="unavailable"
        print "show: ", stanza.get_show()
        print "status: ", stanza.get_status()

    def room_created(self, stanza):
        self.buffer.append_themed("muc.info","New room created. It must be configured before use.")
        self.buffer.update()
        self.buffer.ask_question("[C]onfigure or [A]ccept defaults", "choice", "a",
                self.initial_configuration_choice, values = ("a", "c"), required = True)

    def initial_configuration_choice(self, response):
        if response == "a":
            self.room_state.request_instant_room()
        else:
            self.room_state.request_configuration_form()

    def configuration_form_received(self, form):
        form_buffer = FormBuffer(self.fparams, "muc.conf_descr")
        form_buffer.set_form(form, self.configuration_callback)
        cjc_globals.screen.display_buffer(form_buffer)

    def configuration_callback(self, form_buffer, form):
        form_buffer.close()
        self.room_state.configure_room(form)

    def room_configured(self):
        self.buffer.append_themed("muc.info","Room configured")
        self.buffer.update()

    def user_input(self,s):
        self.room_state.send_message(s)
        return 1

    def error(self,stanza):
        err=stanza.get_error()
        emsg=err.get_message()
        msg="Error"
        if emsg:
            msg+=": %s" % emsg
        etxt=err.get_text()
        if etxt:
            msg+=" ('%s')" % etxt
        self.buffer.append_themed("error",msg)
        self.buffer.update()

    def cmd_me(self,args):
        if not args:
            return 1
        args=args.all()
        if not args:
            return 1
        self.user_input(u"/me "+args)
        return 1

    def cmd_subject(self,args):
        subj=args.all()
        if not subj:
            if self.room_state.subject:
                self.buffer.append_themed("info",u"The room subject is: %s" % (self.room_state.subject,))
            else:
                self.buffer.append_themed("info",u"The room has no subject")
            self.buffer.update()
            return 1
        self.room_state.set_subject(subj)
        return 1

    def cmd_who(self, args):
        nicks = u','.join(self.room_state.users.keys())
        self.buffer.append(nicks + u"\n")
        self.buffer.update()
        
    def cmd_nick(self,args):
        new_nick=args.all()
        if not args:
            raise CommandError,"No nickname given"
        if not self.room_state.joined:
            self.buffer.append_themed("error","You are not in the room")
            self.buffer.update()
            return 1
        self.room_state.change_nick(new_nick)
        return 1

    def cmd_query(self, args):
        nick = args.shift()
        if not nick:
            raise CommandError,"No nickname given"
        if nick not in self.room_state.users:
            self.buffer.append_themed("error", "No '%s' in this room", nick)
            self.buffer.update()
            return 1
        user = self.room_state.users[nick]
        rest = args.all()
        args = u'"%s"' % (user.room_jid.as_unicode().replace('"', '\\"'), )

    def cmd_leave(self,args):
        self.room_state.leave()

    def cmd_close(self,args):
        args.finish()
        self.room_state.leave()
        self.buffer.close()
        return 1

    def cmd_configure(self,args):
        args.finish()
        self.room_state.request_configuration_form()
        return 1

    def get_completion_words(self):
        return [nick+u":" for nick in self.room_state.users.keys()]
