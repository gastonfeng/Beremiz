#!/usr/bin/env python
# -*- coding: utf-8 -*-
import base64
import copy
import os.path
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
import socket
import traceback
from time import sleep

import Pyro4
import Pyro4.core
import Pyro4.util
from Pyro4.errors import PyroError

# from connectors.PYRO.PSK_Adapter import setupPSKAdapter

service_type = '_PYRO._tcp.local.'


# for connectors that do not support DNS-SD, this attribute can be omitted
# Pyro.config.PYRO_BROKEN_MSGWAITALL = use_ssl
# reload(Pyro4.protocol)
# if use_ssl:
#     setupPSKAdapter()


def PYRO_connector_factory(uri, confnodesroot):
    """
    This returns the connector to Pyro style PLCobject
    """
    confnodesroot.logger.write(_("PYRO connecting to URI : %s\n") % uri)

    servicetype, location = uri.split("://")
    if servicetype == "PYROS":
        schemename = "PYROLOCSSL"
        # Protect against name->IP substitution in Pyro3
        Pyro4.config.PYRO_DNS_URI = True
        # load PSK from project
        Pyro4.config.PYROSSL_CERTDIR = os.path.abspath(str(confnodesroot.ProjectPath) + '/certs')
        if not os.path.exists(Pyro4.config.PYROSSL_CERTDIR):
            confnodesroot.logger.write_error(
                'Error : the directory %s is missing for SSL certificates (certs_dir).'
                'Please fix it in your project.\n' % Pyro4.config.PYROSSL_CERTDIR)
            return None
        else:
            confnodesroot.logger.write(_("PYRO using certificates in '%s' \n")
                                       % (Pyro4.config.PYROSSL_CERTDIR))
        Pyro4.config.PYROSSL_CERT = "client.crt"
        Pyro4.config.PYROSSL_KEY = "client.key"

        def _gettimeout(self):
            return self.timeout

        def _settimeout(self, timeout):
            self.timeout = timeout

        from M2Crypto.SSL import Connection
        Connection.timeout = None
        Connection.gettimeout = _gettimeout
        Connection.settimeout = _settimeout
        # strip ID from URL, so that pyro can understand it.
        # match host, expected 127.0.0.1, got server
        Connection.clientPostConnectionCheck = None
    else:
        schemename = "PYROLOC"

    if location.find(service_type) != -1:
        try:
            from zeroconf import Zeroconf
            r = Zeroconf()
            i = r.get_service_info(service_type, location)
            if i is None:
                raise Exception("'%s' not found" % location)
            ip = str(socket.inet_ntoa(i.address))
            port = str(i.port)
            newlocation = ip + ':' + port
            confnodesroot.logger.write(_("'{a1}' is located at {a2}\n").format(a1=location, a2=newlocation))
            location = newlocation
            r.close()
        except Exception:
            confnodesroot.logger.write_error(_("MDNS resolution failure for '%s'\n") % location)
            print(traceback.format_exc())
            return None
    # Try to get the proxy object
    try:
        RemotePLCObjectProxy = Pyro4.Proxy("PYRONAME:PLCObject")
    except Exception as e:
        confnodesroot.logger.write_error(
            _("Connection to {loc} failed with exception {ex}\n").format(
                loc=location, ex=str(e)))
        return None

    # RemotePLCObjectProxy.adapter.setTimeout(60)

    def PyroCatcher(func, default=None):
        """
        A function that catch a Pyro exceptions, write error to logger
        and return default value when it happen
        """

        def catcher_func(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Pyro4.errors.ConnectionClosedError as e:
                confnodesroot._SetConnector(None)
                confnodesroot.logger.write_error(_("Connection lost!\n"))
            except Pyro4.errors.ProtocolError as e:
                confnodesroot.logger.write_error(_("Pyro exception: %s\n") % e)
            except Exception as e:
                print(traceback.format_exc())
                errmess = str(e)
                confnodesroot.logger.write_error(errmess + "\n")
                print(errmess)
                print(traceback.print_exc())
                confnodesroot._SetConnector(None)
            return default

        return catcher_func

    # Check connection is effective.
    # lambda is for getattr of GetPLCstatus to happen inside catcher
    # if async_to_sync(PyroCatcher(RemotePLCObjectProxy.GetPLCstatus))() is None:
    # if IDPSK is None:
    # confnodesroot.logger.write_error(_("Cannot get PLC status - connection failed.\n"))
    # return None

    #     ID, secret = IDPSK
    #     PSK.UpdateID(confnodesroot.ProjectPath, ID, secret, uri)

    class PyroProxyProxy(object):
        """
        A proxy proxy class to handle Beremiz Pyro interface specific behavior.
        And to put Pyro exception catcher in between caller and Pyro proxy
        """

        def __init__(self):
            self.RemotePLCObjectProxyCopy = None

        def GetPyroProxy(self):
            """
            This func returns the real Pyro Proxy.
            Use this if you musn't keep reference to it.
            """
            return RemotePLCObjectProxy

        async def _PyroStartPLC(self, *args, **kwargs):
            """
            confnodesroot._connector.GetPyroProxy() is used
            rather than RemotePLCObjectProxy because
            object is recreated meanwhile,
            so we must not keep ref to it here
            """
            current_status, _log_count = confnodesroot._connector.GetPyroProxy().GetPLCstatus()
            if current_status == "Dirty":
                confnodesroot.logger.write(_("Force runtime reload\n"))
                confnodesroot._connector.GetPyroProxy().ForceReload()
                confnodesroot._Disconnect()
                sleep(0.5)
                confnodesroot._Connect()
            self.RemotePLCObjectProxyCopy = copy.copy(confnodesroot._connector.GetPyroProxy())
            return confnodesroot._connector.GetPyroProxy().StartPLC()

        StartPLC = PyroCatcher(_PyroStartPLC, False)

        async def _PyroGetTraceVariables(self):
            """
            for safe use in from debug thread, must use the copy
            """
            if self.RemotePLCObjectProxyCopy is None:
                self.RemotePLCObjectProxyCopy = copy.copy(confnodesroot._connector.GetPyroProxy())
            status, traces = self.RemotePLCObjectProxyCopy.GetTraceVariables()
            res2 = (status, [(x[0], base64.decodebytes(x[1]['data'].encode())) for x in traces])
            return res2

        GetTraceVariables = PyroCatcher(_PyroGetTraceVariables, ("Broken", None))

        async def _PyroGetPLCstatus(self):
            return RemotePLCObjectProxy.GetPLCstatus()

        GetPLCstatus = PyroCatcher(_PyroGetPLCstatus, ("Broken", None))

        async def _PyroRemoteExec(self, script, **kwargs):
            return RemotePLCObjectProxy.RemoteExec(script, **kwargs)

        RemoteExec = PyroCatcher(_PyroRemoteExec, (-1, "RemoteExec script failed!"))

        def __getattr__(self, attrName):
            member = self.__dict__.get(attrName, None)
            if member is None:
                async def my_local_func(*args, **kwargs):
                    res = RemotePLCObjectProxy.__getattr__(attrName)(*args, **kwargs)
                    return res

                member = PyroCatcher(my_local_func, None)
                self.__dict__[attrName] = member
            return member

    return PyroProxyProxy()
