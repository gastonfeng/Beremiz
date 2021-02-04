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


# from __future__ import absolute_import
# from __future__ import print_function
import asyncio
import traceback
from functools import partial
from threading import Event

import aiohttp
from urllib3.util import request

_HttpSession = None
_HttpConnection = None
_HttpSessionEvent = Event()
_URL = None

lock = asyncio.Lock()


class HttpSession():
    def __init__(self):
        global _HttpSession
        _HttpSession = self

    async def ready(self):
        return
    async def restartPLC(self):
        await lock.acquire()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('%s/reboot' % (_URL)) as response:
                    res = await response.text()
        except Exception as e:
            res = None
        lock.release()
        return res

    async def MatchMD5(self,MD5):
        await lock.acquire()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('%s/MatchMD5' % (_URL)) as response:
                    res = await response.text()
                    if res==MD5:
                        res=True
        except Exception as e:
            res = None
        lock.release()
        return res

    async def GetPLCstatus(self):
        await lock.acquire()
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get('%s/GetPLCstatus' % (_URL))as response:
                    res = await response.text()
            except Exception as e:
                res = None
        lock.release()
        return res

    async def SetTraceVariablesList(self, val):
        await lock.acquire()
        try:
            # v = str(val)
            async with aiohttp.ClientSession() as session:
                async with session.post('%s/SetTraceVariablesList' % (_URL), data=val)as response:
                    res = await response.text()
        except Exception as e:
            res = None
        lock.release()
        return res

    async def GetTraceVariables(self):
        await lock.acquire()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post('%s/GetTraceVariables' % (_URL))as response:
                    res = await response.read()
        except Exception as e:
            res = None
        lock.release()
        return res

    async def StopPLC(self):
        await lock.acquire()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('%s/StopPLC' % (_URL))as response:
                    res = await response.text()
        except Exception as e:
            res = None
        lock.release()
        return res

    async def StartPLC(self):
        await lock.acquire()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('%s/StartPLC' % (_URL))as response:
                    res = await response.text()
        except Exception as e:
            res = None
        lock.release()
        return res

    async def PostFile(self, src, destname):
        await lock.acquire()
        try:
            async with aiohttp.ClientSession() as session:
                files = {destname: open(src, "rb")}
                async with session.post('%s/upload' % (_URL), data=files)as response:
                    res = await response.text()
        except Exception as e:
            print(e)
            res = None
        lock.release()
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


def _HTTP_connector_factory(cls, uri, confnodesroot):
    """
    HTTP://127.0.0.1:12345/path#realm#ID
    HTTPS://127.0.0.1:12345/path#realm#ID
    """
    global _URL
    scheme, location = uri.split("://")
    scheme = "HTTP"
    urlpath = location
    urlprefix = {"HTTP": "http",
                 "HTTPS": "https"}[scheme]
    url = urlprefix + "://" + urlpath
    _URL = url

    def RegisterHttpClient():

        conn = request
        confnodesroot.logger.write(_("HTTP connecting to URL : %s\n") % url)
        return conn

    AddToDoBeforeQuit = confnodesroot.AppFrame.AddToDoBeforeQuit

    def ThreadProc():
        global _HttpConnection
        _HttpConnection = RegisterHttpClient()

    def HttpSessionProcMapper(funcname):
        wampfuncname = funcname  # text('.'.join((ID, funcname)))

        async def catcher_func(*args, **kwargs):
            if _HttpSession is not None:
                try:
                    return await getattr(_HttpSession, wampfuncname)(*args, **kwargs)
                except Exception:
                    errmess = traceback.format_exc()
                    confnodesroot.logger.write_error(errmess + "\n")
                    print(errmess)
                    # confnodesroot._SetConnector(None)
            return PLCObjDefaults.get(funcname)

        return catcher_func

    class HttpPLCObjectProxy(object):
        def __init__(self):
            _HttpSession = HttpSession()

        def __getattr__(self, attrName):
            member = self.__dict__.get(attrName, None)
            if member is None:
                member = HttpSessionProcMapper(attrName)
                self.__dict__[attrName] = member
            return member

    # TODO : GetPLCID()
    # TODO : PSK.UpdateID()

    return HttpPLCObjectProxy


HTTP_connector_factory = partial(_HTTP_connector_factory, HttpSession)
