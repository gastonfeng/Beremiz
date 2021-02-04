#!/usr/bin/env python
# -*- coding: utf-8 -*-

# YAPLC connector, based on LPCProto.py and LPCAppProto.py
# from PLCManager
import ctypes
import datetime
import logging
import socket

YAPLC_STATUS = {0xaa: "Started",
                0x5a: "Empty",
                0x55: "Stopped"}


class YAPLCProtoError(Exception):
    """Exception class"""

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return "Exception in PLC protocol : " + str(self.msg)


class YAPLCProto:

    def __init__(self, ip, port, timeout):
        # serialize access lock
        self.port = port
        self.ip = ip
        self.timeout = timeout
        # open serial port
        self.udp = None
        self.udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # bufsize = self.udp.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF)
        # self.udp.connect((ip, port))
        self.udp.settimeout(timeout)
        # timeout = self.udp.gettimeout()
        # self.udp.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        # StartCoroutine(self.Open(), self)

    def flush(self):
        try:
            self.udp.settimeout(0)
            self.udp.recv(1024)
        except:
            pass

    async def ready(self):
        return True

    def Write(self, bv):
        logging.debug(bv)
        if bv == b'l':
            logging.debug(bv)

        return self.udp.sendto(bv, (self.ip, self.port))

    def Read(self, nbytes):
        return self.udp.recv(nbytes)

    def settimeout(self, val):
        self.udp.settimeout(val)

    async def HandleTransaction(self, transaction):
        transaction.SetPort(self)
        # self.flush()
        # send command, wait ack (timeout)
        await            transaction.SendCommand()
        if transaction.Data:
            await transaction.SendData(transaction.Data)
        self.Write(bytes(transaction.txbuf))
        transaction.rxbuf = self.Read(1024)
        current_plc_status = await transaction.GetCommandAck()
        res = await transaction.GetData()
        return YAPLC_STATUS.get(current_plc_status, "Broken"), res

    def close(self):
        self.udp.close()

    def __del__(self):
        self.close()


class YAPLCTransaction:

    def __init__(self, command):
        self.Command = command
        self.udp = None
        self.txbuf = []
        self.rxbuf = []
        self.Data = None

    def SetPort(self, udp):
        self.udp = udp

    async def SendCommand(self):
        # send command thread
        # self.udp.send(bytes([self.Command, ]))
        self.txbuf = [self.Command, ]
        return True

    async def GetCommandAck(self):
        # self.udp.settimeout(2)
        # res = self.udp.recv(2)
        if not self.rxbuf: return None
        res = self.rxbuf[0:2]
        if res is None:
            return None
        if len(res) == 2:
            comm_status, current_plc_status = res
        else:
            raise YAPLCProtoError("YAPLC transaction error - controller did not ack order!")
        # LPC returns command itself as an ack for command
        if comm_status == self.Command:
            return current_plc_status
        return None

    async def SendData(self, Data):
        # res = self.udp.send(Data)
        self.txbuf += Data
        return len(Data)

    async def GetData(self):
        # lengthstr = self.udp.recv(4)
        if len(self.rxbuf) < 3:
            return None
        lengthstr = self.rxbuf[2:6]
        if lengthstr is None:
            raise YAPLCProtoError("YAPLC transaction error - can't read data length!")
        else:
            if len(lengthstr) != 4:
                raise YAPLCProtoError("YAPLC transaction error - data length is invalid: " + str(len(lengthstr)) + " !")

        # transform a byte string into length
        length = ctypes.cast(
            ctypes.c_char_p(lengthstr),
            ctypes.POINTER(ctypes.c_uint32)
        ).contents.value
        if length > 0:
            # data = b''
            # t1 = time.time()
            # while len(data) < length and time.time() - t1 < 1:
            # data += self.udp.recv(length - len(data))
            data = self.rxbuf[6:length + 6]
            if data is None:
                raise YAPLCProtoError("YAPLC transaction error - can't read data!")
            else:
                if len(lengthstr) == 0:
                    raise YAPLCProtoError("YAPLC transaction error - data is invalid!")
            return data
        else:
            return None

    async def ExchangeData(self):
        pass


class IDLETransaction(YAPLCTransaction):
    def __init__(self):
        YAPLCTransaction.__init__(self, 0x6a)
    # ExchangeData = YAPLCTransaction.GetData


class STARTTransaction(YAPLCTransaction):
    def __init__(self):
        YAPLCTransaction.__init__(self, 0x61)


class STOPTransaction(YAPLCTransaction):
    def __init__(self):
        YAPLCTransaction.__init__(self, 0x62)


class BOOTTransaction(YAPLCTransaction):
    def __init__(self):
        YAPLCTransaction.__init__(self, 0x63)


class SET_TRACE_RESETransaction(YAPLCTransaction):
    def __init__(self):
        YAPLCTransaction.__init__(self, 0x95)


class SET_TRACE_VARIABLETransaction(YAPLCTransaction):
    def __init__(self, data):
        YAPLCTransaction.__init__(self, 0x64)
        length = len(data)
        # transform length into a byte string
        # we presuppose endianess of LPC same as PC
        lengthstr = ctypes.string_at(ctypes.pointer(ctypes.c_uint32(length)), 4)
        self.Data = lengthstr + data

    async def ExchangeData(self):
        await self.SendData(self.Data)


class SET_FORCE_VARIABLETransaction(YAPLCTransaction):
    def __init__(self, data):
        YAPLCTransaction.__init__(self, 0x72)
        length = len(data)
        # transform length into a byte string
        # we presuppose endianess of LPC same as PC
        lengthstr = ctypes.string_at(ctypes.pointer(ctypes.c_uint32(length)), 4)
        self.Data = lengthstr + data

    async def ExchangeData(self):
        await self.SendData(self.Data)


class GET_TRACE_VARIABLETransaction(YAPLCTransaction):
    def __init__(self):
        YAPLCTransaction.__init__(self, 0x65)

    ExchangeData = YAPLCTransaction.GetData


class GET_PLCIDTransaction(YAPLCTransaction):
    def __init__(self):
        YAPLCTransaction.__init__(self, 0x66)

    ExchangeData = YAPLCTransaction.GetData


class GET_LOGCOUNTSTransaction(YAPLCTransaction):
    def __init__(self):
        YAPLCTransaction.__init__(self, 0x67)

    ExchangeData = YAPLCTransaction.GetData


class GET_LOGMSGTransaction(YAPLCTransaction):
    def __init__(self, level, msgid):
        YAPLCTransaction.__init__(self, 0x68)
        msgidstr = ctypes.string_at(ctypes.pointer(ctypes.c_int(msgid)), 4)
        self.Data = bytes([level, ]) + msgidstr

    async def ExchangeData(self):
        # pass
        await self.SendData(self.Data)
        return await self.GetData()


class RESET_LOGCOUNTSTransaction(YAPLCTransaction):
    def __init__(self):
        YAPLCTransaction.__init__(self, 0x69)


class TFTP_PLCBINTransaction(YAPLCTransaction):
    def __init__(self):
        YAPLCTransaction.__init__(self, 0x6e)


class XMODEM_PLCBINTransaction(YAPLCTransaction):
    def __init__(self):
        YAPLCTransaction.__init__(self, 0x6f)


class SETRTCTransaction(YAPLCTransaction):
    def __init__(self):
        YAPLCTransaction.__init__(self, 0x6b)
        dt = datetime.datetime.now()

        year = dt.year % 100
        year = ctypes.string_at(ctypes.pointer(ctypes.c_uint8(year)), 1)
        mon = ctypes.string_at(ctypes.pointer(ctypes.c_uint8(dt.month)), 1)
        day = ctypes.string_at(ctypes.pointer(ctypes.c_uint8(dt.day)), 1)
        hour = ctypes.string_at(ctypes.pointer(ctypes.c_uint8(dt.hour)), 1)
        minute = ctypes.string_at(ctypes.pointer(ctypes.c_uint8(dt.minute)), 1)
        second = ctypes.string_at(ctypes.pointer(ctypes.c_uint8(dt.second)), 1)
        self.Data = year + mon + day + hour + minute + second

    async def ExchangeData(self):
        await self.SendData(self.Data)


class SETIPTransaction(YAPLCTransaction):
    def __init__(self, data):
        YAPLCTransaction.__init__(self, 0x6d)
        length = len(data)
        assert length == 12
        self.Data = data

    async def ExchangeData(self):
        await self.SendData(self.Data)


class GET_PLCRTEVERTransaction(YAPLCTransaction):
    def __init__(self):
        YAPLCTransaction.__init__(self, 0x70)

    ExchangeData = YAPLCTransaction.GetData


class GET_Thread_INFO(YAPLCTransaction):
    def __init__(self):
        YAPLCTransaction.__init__(self, 0x71)

    ExchangeData = YAPLCTransaction.GetData


class GET_MEM(YAPLCTransaction):
    def __init__(self, addr, length):
        YAPLCTransaction.__init__(self, 0x73)
        addrstr = ctypes.string_at(ctypes.pointer(ctypes.c_uint32(addr)), 4)
        lenstr = ctypes.string_at(ctypes.pointer(ctypes.c_uint16(length)), 2)
        self.Data = addrstr + lenstr

    async def ExchangeData(self):
        await self.SendData(self.Data)
        return await self.GetData()
