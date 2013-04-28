#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#Copyright (C) 2011: Edouard TISSERANT and Laurent BESSARD
#
#See COPYING file for copyrights details.
#
#This library is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public
#License as published by the Free Software Foundation; either
#version 2.1 of the License, or (at your option) any later version.
#
#This library is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#General Public License for more details.
#
#You should have received a copy of the GNU General Public
#License along with this library; if not, write to the Free Software
#Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from ctypes import *
from datetime import timedelta as td

class IEC_STRING(Structure):
    """
    Must be changed according to changes in iec_types.h
    """
    _fields_ = [("len", c_uint8),
                ("body", c_char * 126)] 

class IEC_TIME(Structure):
    """
    Must be changed according to changes in iec_types.h
    """
    _fields_ = [("s", c_long), #tv_sec
                ("ns", c_long)] #tv_nsec

def _t(t, u=lambda x:x.value, p=lambda t,x:t(x)): return  (t, u, p)
def _ttime(): return (IEC_TIME, 
                      lambda x:td(0, x.s, x.ns/1000), 
                      lambda t,x:t(x.days * 24 * 3600 + x.seconds, x.microseconds*1000))

SameEndianessTypeTranslator = {
    "BOOL" :       _t(c_uint8,  lambda x:x.value!=0),
    "STEP" :       _t(c_uint8),
    "TRANSITION" : _t(c_uint8),
    "ACTION" :     _t(c_uint8),
    "SINT" :       _t(c_int8),
    "USINT" :      _t(c_uint8),
    "BYTE" :       _t(c_uint8),
    "STRING" :     (IEC_STRING, 
                      lambda x:x.body[:x.len], 
                      lambda t,x:t(len(x),x)),
    "INT" :        _t(c_int16),
    "UINT" :       _t(c_uint16),
    "WORD" :       _t(c_uint16),
    "DINT" :       _t(c_int32),
    "UDINT" :      _t(c_uint32),
    "DWORD" :      _t(c_uint32),
    "LINT" :       _t(c_int64),
    "ULINT" :      _t(c_uint64),
    "LWORD" :      _t(c_uint64),
    "REAL" :       _t(c_float),
    "LREAL" :      _t(c_double),
    "TIME" :       _ttime(),
    "TOD" :        _ttime(),
    "DATE" :       _ttime(),
    "DT" :         _ttime(),
    } 

SwapedEndianessTypeTranslator = {
    #TODO
    } 

TypeTranslator=SameEndianessTypeTranslator

# Construct debugger natively supported types
DebugTypesSize =  dict([(key,sizeof(t)) for key,(t,p,u) in SameEndianessTypeTranslator.iteritems() if t is not None])

def UnpackDebugBuffer(buff, size, indexes):
    res = []
    offset = 0
    for idx, iectype, forced in indexes:
        cursor = c_void_p(buff.value + offset)
        c_type,unpack_func, pack_func = \
            TypeTranslator.get(iectype,
                                    (None,None,None))
        if c_type is not None and offset < size:
            res.append(unpack_func(
                        cast(cursor,
                         POINTER(c_type)).contents))
            offset += sizeof(c_type) if iectype != "STRING" else len(res[-1])+1
        else:
            #if c_type is None:
            #    PLCprint("Debug error - " + iectype +
            #             " not supported !")
            #if offset >= size:
            #    PLCprint("Debug error - buffer too small ! %d != %d"%(offset, size))
            break
    if offset and offset == size:
        return res
    return None



LogLevels = ["CRITICAL","WARNING","INFO","DEBUG"]
LogLevelsCount = len(LogLevels)
LogLevelsDict = dict(zip(LogLevels,range(LogLevelsCount)))
LogLevelsDefault = LogLevelsDict["DEBUG"]

