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


import traceback
from functools import partial

from connectors.TCPLINK.YAPLCObject import YAPLCObject_TCP

_TCPLINKSession = None
errCount = 0

PLCObjDefaults = {
    "StartPLC": False,
    "GetTraceVariables": ("Broken", None),
    "GetPLCstatus": '%s,%d' % ("Broken", 0),
    "RemoteExec": (-1, "RemoteExec script failed!")
}


def _TCPLINK_connector_factory(cls, uri, confnodesroot):
    """
    This returns the connector to YAPLC style PLCobject
    """

    servicetype, comportstr = uri.split("://")
    ip, port = comportstr.split(":")
    if confnodesroot:
        confnodesroot.logger.write(_("Connecting to:" + comportstr + "\n"))

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
                    errmess = traceback.format_exc()
                    if confnodesroot:
                        confnodesroot.logger.write_error(str(ex) + "\n")
                    print(errmess)
                    if confnodesroot:
                        await confnodesroot._SetConnector(None)
            return PLCObjDefaults.get(funcname)

        return catcher_func

    class SocketPLCObjectProxy(object):
        def __init__(self):
            global _SocketSession
            _SocketSession = YAPLCObject_TCP(confnodesroot, ip)

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


TCPLINK_connector_factory = partial(_TCPLINK_connector_factory, None)

if __name__ == '__main__':
    cnt = TCPLINK_connector_factory("TCPLINK://COM1", None)()
    loop.run_until_complete(cnt.GetPLCstatus())
