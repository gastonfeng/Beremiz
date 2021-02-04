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
# along with this program; if not, _write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.


import asyncio
import ctypes
import os
import traceback
from functools import partial

import msgpack
import sliplib as sliplib

from connectors.SERIAL import YAPLCObject_SER
from runtime.PLCObject import LogLevelsCount
from stm32bl.stm32bl_net import stm32bl_net

_ESPLINKSession = None
errCount = 0


class ESPLINKSession(sliplib.Driver):

    def __init__(self, _URL):
        sliplib.Driver.__init__(self)
        self.ESPLINK = stm32bl_net(_URL)
        self.lock = asyncio.Lock()

    async def ready(self):
        while True:
            if self.reader and self.writer:
                return
            await asyncio.sleep(0.1)

    def close(self):
        self.ESPLINK.close()
        self.ESPLINK = None

    async def restartPLC(self):
        await self.lock.acquire()
        cmd = self.send(msgpack.packb({"cmd": "reboot"}))
        await self.ESPLINK._write(cmd)

        sub_buf = await self.ESPLINK._read(1024)
        self.lock.release()
        if not sub_buf:
            raise Exception(_('no response'))
        sub_buf = self.receive(sub_buf)[0]
        return sub_buf == b'OK'

    async def MatchMD5(self, MD5):
        await self.lock.acquire()
        cmd = self.send(msgpack.packb({"cmd": "MatchMD5"}))
        await self.ESPLINK._write(cmd)

        sub_buf = await self.ESPLINK._read(1024)
        self.lock.release()
        if not sub_buf:
            raise Exception(_('no response'))
        sub_buf = self.receive(sub_buf)[0]
        if sub_buf == MD5:
            return True
        return False

    async def GetPLCstatus(self):
        await self.lock.acquire()
        cmd = self.send(bytes([0x67, ]))
        await self.ESPLINK._write(cmd)

        sub_buf = await self.ESPLINK._read(32)
        self.lock.release()
        if not sub_buf:
            raise Exception(_('no response'))
        if sub_buf is not None and len(sub_buf) == LogLevelsCount * 4:
            cstrcounts = ctypes.create_string_buffer(sub_buf)
            ccounts = ctypes.cast(cstrcounts, ctypes.POINTER(ctypes.c_uint32))
            counts = [int(ccounts[idx]) for idx in range(LogLevelsCount)]
        else:
            counts = [0] * LogLevelsCount
        return self.PLCStatus, counts

    async def SetTraceVariablesList(self, val):
        return None

    async def GetTraceVariables(self):
        await self.lock.acquire()
        cmd = self.send(msgpack.packb({"cmd": "GetTraceVariables"}))
        await self.ESPLINK._write(cmd)

        sub_buf = await self.ESPLINK._read(1024)
        self.lock.release()
        if not sub_buf:
            raise Exception(_('no response'))
        sub_buf = self.receive(sub_buf)
        if sub_buf and isinstance(sub_buf, list):
            sub_buf = sub_buf[0]
            sub_buf = msgpack.unpackb(sub_buf)
        return sub_buf

    async def StopPLC(self):
        await self.lock.acquire()
        cmd = self.send(msgpack.packb({"cmd": "StopPLC"}))
        await self.ESPLINK._write(cmd)

        sub_buf = await self.ESPLINK._read(1024)
        self.lock.release()
        if not sub_buf:
            raise Exception(_('no response'))
        sub_buf = self.receive(sub_buf)[0]
        return sub_buf == b'OK'

    async def StartPLC(self):
        await self.lock.acquire()
        cmd = self.send(msgpack.packb({"cmd": "StartPLC"}))
        await self.ESPLINK._write(cmd)

        sub_buf = await self.ESPLINK._read(1024)
        self.lock.release()
        if not sub_buf:
            raise Exception(_('no response'))
        sub_buf = self.receive(sub_buf)[0]
        return sub_buf == b'OK'

    async def PostFile(self, src, destname):
        return None

    async def PurgeBlobs(self):
        return None

    async def SeedBlob(self, val):
        return None

    async def NewPLC(self, MD5, object_blob, extrafiles):
        return True


PLCObjDefaults = {
    "StartPLC": False,
    "GetTraceVariables": ("Broken", None),
    "GetPLCstatus": '%s,%d' % ("Broken", 0),
    "RemoteExec": (-1, "RemoteExec script failed!")
}


def _ESPLINK_connector_factory(cls, uri, confnodesroot):
    """
    This returns the connector to YAPLC style PLCobject
    """

    servicetype, comportstr = uri.split("://")

    confnodesroot.logger._write(_("Connecting to:" + comportstr + "\n"))

    def RegisterSocketClient():
        pass

    # AddToDoBeforeQuit = confnodesroot.AppFrame.AddToDoBeforeQuit

    def SocketSessionProcMapper(funcname):
        wampfuncname = funcname  # text('.'.join((ID, funcname)))

        async def catcher_func(*args, **kwargs):
            if _SocketSession is not None:
                try:
                    return await getattr(_SocketSession, wampfuncname)(*args, **kwargs)
                except Exception as ex:
                    errmess = traceback.format_exc()
                    confnodesroot.logger.write_error(errmess + "\n")
                    print(errmess)
                    await confnodesroot._SetConnector(None)
            return PLCObjDefaults.get(funcname)

        return catcher_func

    if os.name in ("nt", "ce"):
        lib_ext = ".dll"
    else:
        lib_ext = ".so"

    YaPyESPLINKLib = os.path.join(os.path.dirname(os.path.realpath(__file__)), "libYaPyESPLINK" + lib_ext)
    if (os.name == 'posix' and not os.path.isfile(YaPyESPLINKLib)):
        YaPyESPLINKLib = "libYaPyESPLINK" + lib_ext

    class SocketPLCObjectProxy(object):
        def __init__(self):
            global _SocketSession
            _SocketSession = YAPLCObject_SER(YaPyESPLINKLib, confnodesroot, comportstr)

        def __getattr__(self, attrName):
            member = self.__dict__.get(attrName, None)
            if member is None:
                member = SocketSessionProcMapper(attrName)
                self.__dict__[attrName] = member
            return member

        def __del__(self):
            '''调用者释放后执行'''
            _SocketSession.close()

    return SocketPLCObjectProxy()


ESPLINK_connector_factory = partial(_ESPLINK_connector_factory, ESPLINKSession)

if __name__ == '__main__':
    cnt = ESPLINK_connector_factory("ESPLINK://COM1", None)()
    loop.run_until_complete(cnt.GetPLCstatus())
