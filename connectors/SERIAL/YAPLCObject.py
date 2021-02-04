#!/usr/bin/env python
# -*- coding: utf-8 -*-
import ctypes
# YAPLC connector, based on LPCObject.py and LPCAppObjet.py
# from PLCManager
import logging
import os
import shutil
import tempfile
import time
import traceback
from threading import Lock

from asgiref.sync import async_to_sync

from connectors.SERIAL.YAPLCProto import BOOTTransaction, YAPLCProto, STARTTransaction, STOPTransaction, \
    GET_LOGCOUNTSTransaction, \
    GET_PLCIDTransaction, SET_TRACE_VARIABLETransaction, GET_TRACE_VARIABLETransaction, RESET_LOGCOUNTSTransaction, \
    GET_LOGMSGTransaction, YAPLCProtoError, SETRTCTransaction, SET_TRACE_RESETransaction, \
    SETIPTransaction, GET_PLCRTEVERTransaction, XMODEM_PLCBINTransaction, SET_FORCE_VARIABLETransaction, GET_Thread_INFO
from modem.modem.protocol.ymodem import YMODEM
from runtime.PLCObject import LogLevelsCount
from runtime.typemapping import TypeTranslator
from util.ProcessLogger import ProcessLogger


class YAPLCObject_SER(object):
    def __init__(self, libfile, confnodesroot, comportstr):
        self.rts = 0
        self.dtr = 0
        if hasattr(confnodesroot, 'rts'):
            self.rts = getattr(confnodesroot, 'rts')
        if hasattr(confnodesroot, 'dtr'):
            self.dtr = getattr(confnodesroot, 'dtr')
        self.TransactionLock = Lock()
        self.PLCStatus = "Disconnected"
        self.libfile = libfile
        self.confnodesroot = confnodesroot
        self.PLCprint = confnodesroot.logger.write
        self._Idxs = []

        self.TransactionLock.acquire()
        try:
            self.connect(libfile, comportstr, 115200, 2)
        except Exception as e:
            logging.error(str(e) + "\n")
            self.Connection = None
            self.PLCStatus = None  # ProjectController is responsible to set "Disconnected" status
            async_to_sync(self.confnodesroot._SetConnector)(None)
            self.confnodesroot.logger.write_warning('连接已断开')

        self.TransactionLock.release()
        self.errCount = 0
        self.lasttime = 0

    def connect(self, libfile, comportstr, baud, timeout):
        self.Connection = YAPLCProto(libfile, comportstr, baud, timeout)
        self.Connection.SerialPort.GPIO(1, 1 if self.rts == 0 else 0)
        time.sleep(0.1)
        self.Connection.SerialPort.GPIO(2, self.dtr)
        time.sleep(0.5)

    async def ready(self):
        if self.Connection:
            return await self.Connection.ready()
        return False

    async def _HandleSerialTransaction(self, transaction, must_do_lock):
        res = None
        failure = None
        # Must acquire the lock
        # if must_do_lock:
        #     self.TransactionLock.acquire()
        while time.time() - self.lasttime < 0.1:
            time.sleep(0.001)
        # print(time.time())
        # print(transaction)
        if self.Connection is not None:
            # Do the job
            try:
                self.PLCStatus, res = await                self.Connection.HandleTransaction(transaction)
                self.errCount = 0
            except YAPLCProtoError as e:
                failure = str(e)
                self.Connection.flush()
                self.PLCStatus = None  # ProjectController is responsible to set "Disconnected" status
                self.errCount += 1
                logging.error(traceback.print_exc())
            except Exception as e:
                failure = str(e)
                logging.error(traceback.print_exc())
                self.Connection.flush()
                self.errCount += 1
            if self.errCount >= 10:
                await self.confnodesroot._SetConnector(None)
                self.confnodesroot.logger.write_warning('连接已断开')
            self.lasttime = time.time()
        # Must release the lock
        # if must_do_lock:
        #     self.TransactionLock.release()
        return res, failure

    async def HandleSerialTransaction(self, transaction):
        res = None
        failure = None
        res, failure = await self._HandleSerialTransaction(transaction, True)
        if failure is not None:
            logging.error(failure + "\n")
            # self.confnodesroot.logger.write_warning(failure + "\n")
        return res

    async def StartPLC(self):
        self.TransactionLock.acquire()
        await self.HandleSerialTransaction(STARTTransaction())
        self.TransactionLock.release()

    async def StopPLC(self):
        self.TransactionLock.acquire()
        await self.HandleSerialTransaction(STOPTransaction())
        self.TransactionLock.release()
        return True

    async def restartPLC(self):
        self.TransactionLock.acquire()
        await self._HandleSerialTransaction(BOOTTransaction(), False)
        self.TransactionLock.release()

    async def NewPLC(self, md5sum, data, extrafiles):
        if self.MatchMD5(md5sum) == False:
            res = None
            failure = None

            await self.HandleSerialTransaction(SETRTCTransaction())

            self.confnodesroot.logger.write_warning(
                _("Will now upload firmware to PLC.\nThis may take some time, don't close the program.\n"))
            self.TransactionLock.acquire()
            # Will now boot target
            res, failure = await self._HandleSerialTransaction(BOOTTransaction(), False)
            time.sleep(3)
            # Close connection
            self.Connection.Close()
            # bootloader command
            # data contains full command line except serial port string which is passed to % operator
            # cmd = data % self.Connection.port
            cmd = [token % {"serial_port": self.Connection.port} for token in data]
            # wrapper to run command in separate window
            cmdhead = []
            cmdtail = []
            if os.name in ("nt", "ce"):
                # cmdwrap = "start \"Loading PLC, please wait...\" /wait %s \r"
                cmdhead.append("cmd")
                cmdhead.append("/c")
                cmdhead.append("start")
                cmdhead.append("Loading PLC, please wait...")
                cmdhead.append("/wait")
            else:
                # cmdwrap = "xterm -e %s \r"
                cmdhead.append("xterm")
                cmdhead.append("-e")
                # Load a program
                # try:
                # os.system( cmdwrap % command )
            # except Exception,e:
            #    failure = str(e)
            command = cmdhead + cmd + cmdtail;
            status, result, err_result = ProcessLogger(self.confnodesroot.logger, command).spin()
            """
                    TODO: Process output?
            """
            # Reopen connection
            self.Connection.Open()
            self.TransactionLock.release()

            if failure is not None:
                self.confnodesroot.logger.write_warning(failure + "\n")
                return False
            else:
                await self.StopPLC()
                return self.PLCStatus == "Stopped"
        else:
            await self.StopPLC()
            return self.PLCStatus == "Stopped"

    async def GetPLCstatus(self):
        counts = [0, 0, 0, 0]
        for n in range(5):
            self.TransactionLock.acquire()
            strcounts = await self.HandleSerialTransaction(GET_LOGCOUNTSTransaction())
            self.TransactionLock.release()
            if strcounts is not None and len(strcounts) == LogLevelsCount * 4:
                cstrcounts = ctypes.create_string_buffer(strcounts)
                ccounts = ctypes.cast(cstrcounts, ctypes.POINTER(ctypes.c_uint32))
                counts = [int(ccounts[idx]) for idx in range(LogLevelsCount)]
                break
            else:
                counts = [0] * LogLevelsCount
        return self.PLCStatus, counts

    async def MatchMD5(self, MD5):
        self.MatchSwitch = False
        self.TransactionLock.acquire()
        data = await self.HandleSerialTransaction(GET_PLCIDTransaction())
        self.MatchSwitch = True
        self.TransactionLock.release()
        if data is not None:
            data = data.decode()
            if data[:32] == MD5[:32]:
                return True
            # else:
            #     self.confnodesroot.logger.write_warning('MD5:PLC= %s ,Local = %s\n' % (data, MD5))
        return False

    async def GetRteVer(self):
        self.TransactionLock.acquire()
        data = await self.HandleSerialTransaction(GET_PLCRTEVERTransaction())
        self.TransactionLock.release()
        return data

    async def GetThreadInfo(self):
        self.TransactionLock.acquire()
        data = await self.HandleSerialTransaction(GET_Thread_INFO())
        self.TransactionLock.release()
        return data

    async def SetIP(self, data):
        self.TransactionLock.acquire()
        await self.HandleSerialTransaction(SETIPTransaction(data))
        self.TransactionLock.release()

    async def SetTraceVariablesList(self, idxs):
        """
        Call ctype imported function to append
        these indexes to registred variables in PLC debugger
        """
        buff = b""
        self.TransactionLock.acquire()
        if idxs:
            # keep a copy of requested idx
            await self.HandleSerialTransaction(SET_TRACE_RESETransaction())
            self._Idxs = idxs[:]
            inx = 0
            for idx, iectype in idxs:
                inx += 1
                idxstr = ctypes.string_at(ctypes.pointer(ctypes.c_uint32(idx)), 4)
                buff += idxstr + bytes([0, ])
                if len(buff) > 150:
                    await self.HandleSerialTransaction(SET_TRACE_VARIABLETransaction(buff))
                    buff = b''
                    # todo:->async
                    time.sleep(0.2)
                self.confnodesroot.ShowPLCProgress(status=(_('Setting Monitor Variable %d/%d') % (inx, len(idxs))),
                                                   progress=inx * 100 / len(idxs))
            if buff:
                await self.HandleSerialTransaction(SET_TRACE_VARIABLETransaction(buff))
            self.confnodesroot.HidePLCProgress()
        else:
            buff = b""
            self._Idxs = []
            await self.HandleSerialTransaction(SET_TRACE_VARIABLETransaction(buff))
        self.TransactionLock.release()

    async def SetForceVariablesList(self, idxs):
        """
        Call ctype imported function to append
        these indexes to registred variables in PLC debugger
        """
        buff = b""
        self.TransactionLock.acquire()
        self._Idxs = idxs[:]
        inx = 0
        for idx, iectype, force in idxs:
            inx += 1
            idxstr = ctypes.string_at(ctypes.pointer(ctypes.c_uint32(idx)), 4)
            if force != None:
                c_type, unpack_func, pack_func = TypeTranslator.get(iectype, (None, None, None))
                forced_type_size = ctypes.sizeof(c_type) \
                    if iectype != "STRING" else len(force) + 1
                forced_type_size_str = bytes([forced_type_size, ])
                forcestr = ctypes.string_at(
                    ctypes.pointer(
                        pack_func(c_type, force)),
                    forced_type_size)
                buff += idxstr + forced_type_size_str + forcestr
            else:
                buff += idxstr + bytes([0, ])
        if buff:
            await self.HandleSerialTransaction(SET_FORCE_VARIABLETransaction(buff))
        self.TransactionLock.release()

    async def GetTraceVariables(self):
        """
        Return a list of variables, corresponding to the list of required idx
        """
        self.TransactionLock.acquire()
        strbuf = await self.HandleSerialTransaction(GET_TRACE_VARIABLETransaction())
        self.TransactionLock.release()
        TraceVariables = []
        if strbuf is not None and len(strbuf) >= 4 and self.PLCStatus == "Started":
            size = len(strbuf) - 4
            ctick = ctypes.create_string_buffer(strbuf[:4])
            tick = ctypes.cast(ctick, ctypes.POINTER(ctypes.c_uint32)).contents
            if size > 0:
                cbuff = ctypes.create_string_buffer(strbuf[4:])
                buff = ctypes.cast(cbuff, ctypes.c_void_p)
                TraceBuffer = ctypes.string_at(buff.value, size)
                # Add traces
                TraceVariables.append((tick.value, TraceBuffer))
        return self.PLCStatus, TraceVariables

    async def ResetLogCount(self):
        self.TransactionLock.acquire()
        await self.HandleSerialTransaction(RESET_LOGCOUNTSTransaction())
        self.TransactionLock.release()

    async def GetLogMessage(self, level, msgid):
        self.TransactionLock.acquire()
        strbuf = await self.HandleSerialTransaction(GET_LOGMSGTransaction(level, msgid))
        self.TransactionLock.release()
        if strbuf is not None and len(strbuf) > 12:
            cbuf = ctypes.cast(
                ctypes.c_char_p(strbuf[:12]),
                ctypes.POINTER(ctypes.c_uint32))
            try:
                a = strbuf[12:]
                if a:
                    a = a.decode()
                    b = tuple(int(cbuf[idx]) for idx in range(3))
                    c = [a] + list(b)
                    return c
            except Exception as ex:
                logging.error(ex)
                logging.error(traceback.format_exc())
        return None

    def ForceReload(self):
        raise YAPLCProtoError("Not implemented")

    def RemoteExec(self, script, **kwargs):
        return (-1, "RemoteExec is not supported by YAPLC target!")

    def close(self):
        if self.Connection:
            self.Connection.close()

    async def PurgeBlobs(self):
        return None

    async def SeedBlob(self, val):
        return None

    def getc(self, size, timeout=10, debug=None):
        t1 = time.time()
        data = None
        while time.time() - t1 < timeout:
            data = self.Connection.SerialPort.Read(size)
            if isinstance(data, int):
                data = bytes([data, ])
            if data: break
        # print(data)
        return data

    def putc(self, data, timeout=3, debug=None):
        size = self.Connection.SerialPort.Write(data)
        self.inx += size
        self.confnodesroot.ShowPLCProgress(status=(_('Downloading')), progress=self.inx * 100 / self.pktsize)
        # @todo: 界面未刷新
        return size

    async def PostFile(self, src, destname):
        self.inx = 0
        self.pktsize = os.path.getsize(src)
        self.TransactionLock.acquire()
        try:
            await self.HandleSerialTransaction(SETRTCTransaction())
            await self.HandleSerialTransaction(XMODEM_PLCBINTransaction())
            fd, fn = tempfile.mkstemp()
            shutil.copy(src, fn)
            t = YMODEM(self.getc, self.putc)
            res = t.send(fn, retry=10)
            self.confnodesroot.HidePLCProgress()
        except Exception as e:
            logging.error(traceback.format_exc())
            res = None
        self.TransactionLock.release()
        return res
