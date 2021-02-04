#!/usr/bin/env python
# -*- coding: utf-8 -*-

# YAPLC connector, based on LPCProto.py and LPCAppProto.py
# from PLCManager
import ctypes
import socket

from connectors.UDPLINK.YAPLCProto import YAPLC_STATUS


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
        self.tcp = None
        self.tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #        bufsize = self.tcp.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF)
        self.tcp.connect((ip, port))
        self.tcp.settimeout(timeout)
        timeout = self.tcp.gettimeout()
        self.tcp.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        # StartCoroutine(self.Open(), self)

    def flush(self):
        try:
            self.tcp.settimeout(0)
            self.tcp.recv(1024)
        except:
            pass

    async def ready(self):
        return True

    def Write(self, bv):
        return self.tcp.send(bv)

    def Read(self, nbytes):
        return self.tcp.recv(nbytes)

    def settimeout(self, val):
        self.tcp.settimeout(val)

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
        self.tcp.close()

    def __del__(self):
        self.close()


class YAPLCTransaction:

    def __init__(self, command):
        self.Command = command
        self.tcp = None

    def SetPort(self, tcp):
        self.tcp = tcp

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
