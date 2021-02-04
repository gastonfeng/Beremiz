#!/usr/bin/env python
# -*- coding: utf-8 -*-
# YAPLC connector, based on LPCObject.py and LPCAppObjet.py
# from PLCManager
from threading import Lock

from connectors.TCPLINK.YAPLCProto import YAPLCProto
from connectors.UDPLINK import YAPLCObject_UDP
from wxasync.src.wxasync import StartCoroutine


class YAPLCObject_TCP(YAPLCObject_UDP):
    def __init__(self, confnodesroot, comportstr):

        self.TransactionLock = Lock()
        self.PLCStatus = "Disconnected"
        self.confnodesroot = confnodesroot
        self.PLCprint = confnodesroot.logger.write
        self._Idxs = []
        self.ip = comportstr
        self.TransactionLock.acquire()
        try:
            self.Connection = YAPLCProto(comportstr, 8080, 5)
        except Exception as e:
            print(str(e) + "\n")
            self.Connection = None
            self.PLCStatus = None  # ProjectController is responsible to set "Disconnected" status
            StartCoroutine(self.confnodesroot._SetConnector(None), self.confnodesroot.AppFrame)
        self.TransactionLock.release()
        self.errCount = 0
        self.lasttime = 0

    def close(self):
        if self.Connection:
            self.Connection.close()

