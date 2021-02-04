#!/usr/bin/env python
# -*- coding: utf-8 -*-
# YAPLC connector, based on LPCObject.py and LPCAppObjet.py
# from PLCManager
import ctypes
import os
import time
import traceback
from threading import Lock

import tftpy

from connectors.UDPLINK.YAPLCProto import YAPLCProto, YAPLCProtoError, STARTTransaction, STOPTransaction, \
    BOOTTransaction, SETRTCTransaction, GET_LOGCOUNTSTransaction, GET_PLCIDTransaction, GET_PLCRTEVERTransaction, \
    GET_Thread_INFO, SETIPTransaction, SET_TRACE_RESETransaction, SET_TRACE_VARIABLETransaction, \
    SET_FORCE_VARIABLETransaction, GET_TRACE_VARIABLETransaction, RESET_LOGCOUNTSTransaction, GET_LOGMSGTransaction, \
    TFTP_PLCBINTransaction
from runtime.loglevels import LogLevelsCount
from runtime.typemapping import TypeTranslator
from util.ProcessLogger import ProcessLogger
from wxasync.src.wxasync import StartCoroutine


class YAPLCObject_UDP(object):
    def __init__(self, confnodesroot, comportstr):

        self.TransactionLock = Lock()
        self.PLCStatus = "Disconnected"
        self.confnodesroot = confnodesroot
        self.PLCprint = confnodesroot.logger.write
        self._Idxs = []
        self.ip = comportstr
        self.TransactionLock.acquire()
        try:
            self.Connection = YAPLCProto(comportstr, 8888, 1)
        except Exception as e:
            print(str(e) + "\n")
            self.Connection = None
            self.PLCStatus = None  # ProjectController is responsible to set "Disconnected" status
            StartCoroutine(self.confnodesroot._SetConnector(None), self.confnodesroot.AppFrame)
        self.TransactionLock.release()
        self.errCount = 0
        self.lasttime = 0

    def connect(self, libfile, comportstr, baud, timeout):
        self.Connection = YAPLCProto(libfile, comportstr, baud, timeout)

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
                print(traceback.print_exc())
            except Exception as e:
                failure = str(e)
                print(traceback.print_exc())
                # self.Connection.flush()
                self.errCount += 1
            if self.errCount >= 10:
                await self.confnodesroot._SetConnector(None)
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
            print(failure + "\n")
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
        if strbuf is not None and len(strbuf) >= 4:
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
                print(ex)
                print(traceback.format_exc())
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

    async def PostFile(self, src, destname):
        self.inx = 0
        self.pktsize = os.path.getsize(src) / 1024

        def hook(packet):
            self.inx += 1
            self.confnodesroot.ShowPLCProgress(status=(_('Downloading')), progress=self.inx * 100 / self.pktsize)

        self.TransactionLock.acquire()
        cnt = 0
        await self.HandleSerialTransaction(SETRTCTransaction())
        await self.HandleSerialTransaction(TFTP_PLCBINTransaction())
        while True:
            try:
                self.inx = 0
                t = tftpy.TftpClient(self.ip, options={'blksize': 512})
                res = True
                t.upload(destname, src, packethook=hook, timeout=2)
                break
            except Exception as ex:
                if self.confnodesroot:
                    self.confnodesroot.logger.write_error(str(ex))
                    self.confnodesroot.logger.write_error("正在重试 %d / 10..." % (cnt + 1))
                    # self.confnodesroot.logger.write_error(traceback.format_exc())
                res = None
            cnt += 1
            if cnt == 10: break
        self.TransactionLock.release()
        if self.confnodesroot:
            self.confnodesroot.HidePLCProgress()
        return res

    async def transferDir(self, src, destname):
        ##@todo:debug
        files = os.listdir(src)
        for file in files:
            await self.PostFile(file, destname)
