#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz, a Integrated Development Environment for
# programming IEC 61131-3 automates supporting plcopen standard and CanFestival.
#
# Copyright (C) 2007: Edouard TISSERANT and Laurent BESSARD
#
# See COPYING file for copyrights details.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.


import asyncio
import traceback
from functools import partial
from time import sleep

import msgpack
import tftpy as tftpy

from wxasync.src.wxasync import StartCoroutine

_SocketSession = None
_URL = None


class SocketSession(object):
    def __init__(self, parent):
        self.reader = None
        self.writer = None
        self.lock = asyncio.Lock()
        self.lock.locked()
        StartCoroutine(self.connect(parent), self)

    async def connect(self, parent):
        await self.lock.acquire()
        self.cnter = asyncio.open_connection(_URL, 8080)
        try:
            self.reader, self.writer = await asyncio.wait_for(self.cnter, timeout=1)
        except asyncio.TimeoutError:
            parent.logger.write_error(_("Socket connected to URL : %s\n Failed.") % _URL)
        else:
            parent.logger.write(_("Socket connected to URL : %s\n") % _URL)
        self.lock.release()

    def close(self):
        if self.writer:
            self.writer.close()
            self.cnter.close()

    async def ready(self):
        while True:
            if self.reader and self.writer:
                return
            await asyncio.sleep(0.1)

    async def restartPLC(self):
        await self.lock.acquire()
        cmd = (msgpack.packb({"cmd": "reboot"}))
        self.writer.write(cmd)
        await self.writer.drain()
        sub_buf = await self.reader.read(1024)
        self.lock.release()
        if not sub_buf:
            raise Exception(_('no response'))
        return sub_buf == b'OK'

    async def MatchMD5(self,MD5):
        await self.lock.acquire()
        cmd = (msgpack.packb({"cmd": "MatchMD5"}))
        self.writer.write(cmd)
        await self.writer.drain()

        sub_buf = await self.reader.read(1024)
        self.lock.release()
        if not sub_buf:
            raise Exception(_('no response'))
        sub_buf = sub_buf.decode()
        if sub_buf==MD5:
            return True
        return sub_buf

    async def GetPLCstatus(self):
        await self.lock.acquire()
        cmd = msgpack.packb({"cmd": "GetPLCstatus"})
        self.writer.write(cmd)
        await self.writer.drain()
        sub_buf = await self.reader.read(1024)
        self.lock.release()
        if not sub_buf:
            raise Exception(_('no response'))
        sub_buf = sub_buf.decode()
        return sub_buf

    async def SetTraceVariablesList(self, val):
        return None

    async def GetTraceVariables(self):
        await self.lock.acquire()
        cmd = (msgpack.packb({"cmd": "GetTraceVariables"}))
        self.writer.write(cmd)
        await self.writer.drain()

        sub_buf = await self.reader.read(1024)
        self.lock.release()
        if not sub_buf:
            raise Exception(_('no response'))
        sub_buf = msgpack.unpackb(sub_buf)
        return sub_buf

    async def StopPLC(self):
        await self.lock.acquire()
        cmd = (msgpack.packb({"cmd": "StopPLC"}))
        self.writer.write(cmd)
        await self.writer.drain()

        sub_buf = await self.reader.read(1024)
        self.lock.release()
        if not sub_buf:
            raise Exception(_('no response'))
        return sub_buf == b'OK'

    async def StartPLC(self):
        await self.lock.acquire()
        cmd = (msgpack.packb({"cmd": "StartPLC"}))
        self.writer.write(cmd)
        await self.writer.drain()

        sub_buf = await self.reader.read(1024)
        self.lock.release()
        if not sub_buf:
            raise Exception(_('no response'))
        return sub_buf == b'OK'

    async def PostFile(self, src, destname):
        await self.lock.acquire()
        try:
            t = tftpy.TftpClient(_URL)
            res = True
            t.upload(destname, src)
        except Exception as e:
            print(e)
            res = None
        self.lock.release()
        return res

    async def PurgeBlobs(self):
        return None

    async def SeedBlob(self, val):
        return None

    async def NewPLC(self, MD5, object_blob, extrafiles):
        return True


PLCObjDefaults = {
    "StartPLC": False,
    "GetTraceVariables": ("Broken", None),
    "GetPLCstatus": '%s %d' % ("Broken", 0),
    "RemoteExec": (-1, "RemoteExec script failed!")
}


def _SOCKET_connector_factory(cls, uri, confnodesroot):
    """
    Socket://127.0.0.1:12345/path#realm#ID
    SocketS://127.0.0.1:12345/path#realm#ID
    """
    global _URL
    scheme, location = uri.split("://")
    ip, port = location.split(":")
    scheme = "Socket"
    urlpath = location
    urlprefix = {"Socket": "Socket",
                 "SocketS": "Sockets"}[scheme]
    url = urlprefix + "://" + urlpath
    _URL = ip

    def RegisterSocketClient():
        pass

    if confnodesroot:
        AddToDoBeforeQuit = confnodesroot.AppFrame.AddToDoBeforeQuit

    def SocketSessionProcMapper(funcname):
        wampfuncname = funcname  # text('.'.join((ID, funcname)))

        async def catcher_func(*args, **kwargs):
            if _SocketSession is not None:
                try:
                    return await getattr(_SocketSession, wampfuncname)(*args, **kwargs)
                except Exception as ex:
                    print(traceback.format_exc())
                    confnodesroot.logger.write_error(str(ex) + "\n")
                    await confnodesroot._SetConnector(None)
            return PLCObjDefaults.get(funcname)

        return catcher_func

    class SocketPLCObjectProxy(object):
        def __init__(self):
            global _SocketSession
            _SocketSession = SocketSession(confnodesroot)
            sleep(1)

        def __getattr__(self, attrName):
            member = self.__dict__.get(attrName, None)
            if member is None:
                member = SocketSessionProcMapper(attrName)
                self.__dict__[attrName] = member
            return member

        def __del__(self):
            '''调用者释放后执行'''
            if _SocketSession:
                _SocketSession.close()

    return SocketPLCObjectProxy


SOCKET_connector_factory = partial(_SOCKET_connector_factory, SocketSession)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    cnt = SOCKET_connector_factory("Socket://192.168.31.100:8080", None)()
    loop.run_until_complete(cnt.GetPLCstatus())
