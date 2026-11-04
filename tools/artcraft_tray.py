#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright 2026 Monochrome Icons contributors
"""Optional Xfce ArtCraft tray adapter; original pixels are read only at runtime.

Preserve the original alpha mask, show white ink, and forward the original SNI
and dbusmenu interfaces. No vendor artwork is distributed or patched. Requires
Python GObject/GIO. Run as the desktop user, never as root.
"""
import argparse
import fcntl
import os
from pathlib import Path
import signal
import subprocess
import sys

from gi.repository import Gio, GLib

ITEM='org.kde.StatusNotifierItem'
MENU='com.canonical.dbusmenu'
WATCHER='org.kde.StatusNotifierWatcher'
PROPS='org.freedesktop.DBus.Properties'
IDENT='artcraft-launcher-monochrome'


def white_pixels(pixmaps):
    """SNI bytes are network-order ARGB; keep geometry and coverage exactly."""
    result=[]
    for width,height,pixels in pixmaps:
        if width<=0 or height<=0 or len(pixels)!=width*height*4 or width*height>1048576:
            raise ValueError('Invalid source tray bitmap')
        data=bytearray(pixels)
        for offset in range(0,len(data),4):
            value=255 if data[offset] else 0
            data[offset+1:offset+4]=bytes([value,value,value])
        result.append((width,height,bytes(data)))
    return result


class Tray:
    def __init__(self,plugin):
        self.plugin=plugin
        self.bus=Gio.bus_get_sync(Gio.BusType.SESSION,None)
        self.name=f'org.kde.StatusNotifierItem-{os.getpid()}-1'
        self.source=None;self.registrations=[];self.subscriptions=[]
        self.cache={};self.interfaces={};self.masked=False;self.was_hidden=False
        self.loop=GLib.MainLoop()
        self.owner=Gio.bus_own_name_on_connection(self.bus,self.name,Gio.BusNameOwnerFlags.NONE,
                                                self.acquired,self.lost)

    def call(self,name,path,interface,method,args=None):
        return self.bus.call_sync(name,path,interface,method,args,None,Gio.DBusCallFlags.NONE,2000,None)

    def hidden(self):
        command=['xfconf-query','-c','xfce4-panel','-p',self.plugin+'/hidden-items']
        p=subprocess.run(command,capture_output=True,text=True)
        if p.returncode:return None
        return [x for x in p.stdout.splitlines() if x and not x.startswith('Value is an array')]

    def write_hidden(self,values):
        command=['xfconf-query','-c','xfce4-panel','-p',self.plugin+'/hidden-items']
        if values is None:
            subprocess.run(command+['-r'],capture_output=True,check=False);return
        args=command+['-a']
        if self.hidden() is None:
            args+=['-n']
            for value in values:args+=['-t','string','-s',value]
        else:
            for value in values:args+=['-s',value]
        subprocess.run(args,capture_output=True,check=True)

    def mask(self):
        if self.masked:return
        values=self.hidden()
        self.hidden_existed=values is not None
        self.was_hidden='artcraft-launcher' in (values or [])
        if self.was_hidden:
            raise RuntimeError('Original ArtCraft item was already hidden; preserve user preference')
        self.write_hidden((values or [])+['artcraft-launcher'])
        self.masked=True

    def unmask(self):
        if not self.masked:return
        values=[x for x in (self.hidden() or []) if x!='artcraft-launcher']
        self.write_hidden(values if values or self.hidden_existed else None)
        self.masked=False

    def acquired(self,*args):
        GLib.idle_add(self.once)
        self.watcher_subscription=self.bus.signal_subscribe(
            WATCHER,WATCHER,None,'/StatusNotifierWatcher',None,
            Gio.DBusSignalFlags.NONE,lambda *args:GLib.idle_add(self.once))
        # Signals handle normal changes; a slow retry covers watcher restarts.
        GLib.timeout_add_seconds(30,self.tick)

    def once(self):
        self.tick()
        return False

    def lost(self,*args):
        self.loop.quit()

    def refresh(self):
        for interface,path in [(ITEM,self.source[1]),(MENU,self.menu_path)]:
            props=self.call(self.source[0],path,PROPS,'GetAll',GLib.Variant('(s)',(interface,))).unpack()[0]
            self.cache[interface]=props
        props=self.cache[ITEM]
        props['Id']=IDENT
        for key in ['IconPixmap','AttentionIconPixmap','OverlayIconPixmap']:
            if key in props:props[key]=white_pixels(props[key])
        for key in ['IconName','AttentionIconName','OverlayIconName','IconThemePath']:
            props[key]=''
        tooltip=props.get('ToolTip')
        if tooltip:
            name,pixels,title,description=tooltip
            props['ToolTip']=('',white_pixels(pixels),title,description)

    def get_property(self,connection,sender,path,interface,name):
        info=self.interfaces[interface]
        prop=next(p for p in info.properties if p.name==name)
        value=self.cache[interface][name]
        if interface==ITEM and name=='Status' and self.source is None:value='Passive'
        return GLib.Variant(prop.signature,value)

    def method(self,connection,sender,path,interface,name,parameters,invocation):
        if self.source is None:
            invocation.return_dbus_error('org.freedesktop.DBus.Error.Disconnected','ArtCraft is not running');return
        target_path=self.source[1] if interface==ITEM else self.menu_path
        def completed(bus,result):
            try:invocation.return_value(bus.call_finish(result))
            except GLib.Error as error:invocation.return_gerror(error)
        self.bus.call(self.source[0],target_path,interface,name,parameters,None,
                      Gio.DBusCallFlags.NONE,10000,None,completed)

    def signal(self,connection,sender,path,interface,name,parameters):
        try:
            self.refresh()
            self.bus.emit_signal(None,'/StatusNotifierItem' if interface==ITEM else self.menu_path,
                                 interface,name,parameters)
        except GLib.Error:pass

    def disconnect(self):
        for subscription in self.subscriptions:self.bus.signal_unsubscribe(subscription)
        for registration in self.registrations:self.bus.unregister_object(registration)
        self.subscriptions=[];self.registrations=[];self.interfaces={}

    def connect(self,source):
        if not self.masked and 'artcraft-launcher' in (self.hidden() or []):
            raise RuntimeError('Original ArtCraft item was already hidden; preserve user preference')
        self.disconnect();self.source=source
        self.menu_path=self.call(*source,PROPS,'Get',GLib.Variant('(ss)',(ITEM,'Menu'))).unpack()[0]
        self.refresh()
        for interface,path,own_path in [(ITEM,source[1],'/StatusNotifierItem'),(MENU,self.menu_path,self.menu_path)]:
            xml=self.call(source[0],path,'org.freedesktop.DBus.Introspectable','Introspect').unpack()[0]
            info=Gio.DBusNodeInfo.new_for_xml(xml).lookup_interface(interface)
            self.interfaces[interface]=info
            self.registrations.append(self.bus.register_object(own_path,info,self.method,self.get_property,None))
            self.subscriptions.append(self.bus.signal_subscribe(source[0],interface,None,path,None,
                                                                Gio.DBusSignalFlags.NONE,self.signal))
        self.call(WATCHER,'/StatusNotifierWatcher',WATCHER,'RegisterStatusNotifierItem',GLib.Variant('(s)',(self.name,)))
        self.mask()
        for name,parameters in [('NewStatus',GLib.Variant('(s)',(self.cache[ITEM]['Status'],))),
                                ('NewIcon',None),('NewToolTip',None)]:
            self.bus.emit_signal(None,'/StatusNotifierItem',ITEM,name,parameters)
        print('Registered monochrome original ArtCraft tray; menus and clicks forwarded',flush=True)

    def tick(self):
        try:
            items=self.call(WATCHER,'/StatusNotifierWatcher',PROPS,'Get',
                            GLib.Variant('(ss)',(WATCHER,'RegisteredStatusNotifierItems'))).unpack()[0]
            found=None
            for item in items:
                name,sep,path=item.partition('/')
                path='/'+path if sep else '/StatusNotifierItem'
                if name==self.name:continue
                try:
                    ident=self.call(name,path,PROPS,'Get',GLib.Variant('(ss)',(ITEM,'Id'))).unpack()[0]
                    if ident=='artcraft-launcher':found=(name,path);break
                except GLib.Error:continue
            if found and found!=self.source:self.connect(found)
            elif found and not any(item.partition('/')[0]==self.name for item in items):
                self.call(WATCHER,'/StatusNotifierWatcher',WATCHER,'RegisterStatusNotifierItem',
                          GLib.Variant('(s)',(self.name,)))
                self.mask()
            elif not found and self.source:
                self.source=None
                self.bus.emit_signal(None,'/StatusNotifierItem',ITEM,'NewStatus',GLib.Variant('(s)',('Passive',)))
                self.unmask()
        except (GLib.Error,RuntimeError,ValueError,KeyError,subprocess.CalledProcessError) as error:
            print('Tray adapter:',error,file=sys.stderr,flush=True)
            self.unmask()
        return True

    def run(self):
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT,signal.SIGTERM,lambda:self.loop.quit())
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT,signal.SIGINT,lambda:self.loop.quit())
        try:self.loop.run()
        finally:
            self.unmask();self.disconnect();Gio.bus_unown_name(self.owner)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plugin',required=True,help='Verified Xfce systray path, e.g. /plugins/plugin-6')
    args=parser.parse_args()
    if not __import__('re').fullmatch(r'/plugins/plugin-\d+',args.plugin):parser.error('Invalid Xfce plugin path')
    if subprocess.check_output(['xfconf-query','-c','xfce4-panel','-p',args.plugin],text=True).strip()!='systray':
        parser.error('Selected plugin is not the notification area')
    lock=Path(os.environ.get('XDG_RUNTIME_DIR','/run/user/'+str(os.getuid())))/'artcraft-monochrome-tray.lock'
    with lock.open('a+') as stream:
        try:fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise SystemExit('Tray adapter already running')
        stream.seek(0);stream.truncate();stream.write(str(os.getpid()));stream.flush()
        Tray(args.plugin).run()
