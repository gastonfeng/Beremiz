#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz, a Integrated Development Environment for
# programming IEC 61131-3 automates supporting plcopen standard and CanFestival.
#
# Copyright (c) 2016 Mario de Sousa (msousa@fe.up.pt)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# This code is made available on the understanding that it will not be
# used in safety-critical situations without a full and competent review.


import os

from ConfigTreeNode import ConfigTreeNode
from modbus.mb_utils import *
from plcopen.types_enums import LOCATION_CONFNODE, LOCATION_VAR_MEMORY, LOCATION_VAR_OUTPUT, LOCATION_VAR_INPUT

base_folder = os.path.split(os.path.dirname(os.path.realpath(__file__)))[0]
base_folder = os.path.join(base_folder, "..")
ModbusPath = os.path.join(base_folder, "Modbus")
IEC_C = {"UINT": "uint16_t", "REAL": "float", "INT": "int16_t", "BOOL": "uint8_t", "SINT": "int8_t", "USINT": "uint8_t",
         "DINT": "int32_t", "UDINT": "uint32_t", "LREAL": "double", "LINT": "int64_t", "ULINT": "uint64_t",
         "WORD": "uint16_t", "BYTE": "uint8_t", "LWORD": "uint64_t"}


#
#
#
# C L I E N T    R E Q U E S T            #
#
#
#
def params(location):
    current_location = list(location)
    if len(current_location) == 2:
        current_location += [0, 0]
    elif len(current_location) == 3:
        current_location += [0]
    else:
        raise Exception(_("Error: location size must 2 or 3. current=%s") % location)
    return [
        {"name": '通信参数',
         "type": LOCATION_CONFNODE,
         "location": ".".join([str(i) for i in current_location]) + ".x",
         "children": [
             {"name": "ID(USINT)", "var_name": "MB_%s_ID" % '_'.join(map(str, location)), "type": LOCATION_VAR_OUTPUT,
              "size": 1,
              "IEC_type": "USINT",
              "io_name": "id",
              "location": "%s%s" % ('B', ".".join(map(str, current_location + [1]))),
              "description": "ID Address,USINT",
              "children": []},
             {"name": "BaudRate(UDINT)", "var_name": "MB_%s_BAUD" % '_'.join(map(str, location)),
              "type": LOCATION_VAR_OUTPUT, "size": 4,
              "IEC_type": "UDINT",
              "io_name": "baudrate",
              "location": "%s%s" % ('D', ".".join(map(str, current_location + [2]))),
              "description": "通信波特率,UDINT",
              "children": []},
             {"name": "data_bits(USINT)", "var_name": "MB_%s_DATASZ" % '_'.join(map(str, location)),
              "type": LOCATION_VAR_OUTPUT, "size": 1,
              "IEC_type": "USINT",
              "io_name": "data_bits",
              "location": "%s%s" % ('B', ".".join(map(str, current_location + [3]))),
              "description": "数据位,USINT,8-9",
              "children": []},
             {"name": "stop_bits(USINT)", "var_name": "MB_%s_STOPSZ" % '_'.join(map(str, location)),
              "type": LOCATION_VAR_OUTPUT, "size": 1,
              "IEC_type": "USINT",
              "io_name": "stop_bits",
              "location": "%s%s" % ('B', ".".join(map(str, current_location + [4]))),
              "description": "停止位,USINT,[1-2]",
              "children": []},
             {"name": "Parity(USINT)", "var_name": "MB_%s_PARITY" % '_'.join(map(str, location)),
              "type": LOCATION_VAR_OUTPUT, "size": 1,
              "IEC_type": "USINT",
              "io_name": "parity",
              "location": "%s%s" % ('B', ".".join(map(str, current_location + [5]))),
              "description": "校验位,USINT,",
              "children": []},
             {"name": "Period(UDINT)", "var_name": "MB_%s_INTERVAL" % '_'.join(map(str, location)),
              "type": LOCATION_VAR_OUTPUT, "size": 4,
              "IEC_type": "UDINT",
              "io_name": "period",
              "location": "%s%s" % ('D', ".".join(map(str, current_location + [6]))),
              "description": "查询周期,UDINT,单位ms",
              "children": []},
             {"name": "Status(INT)", "var_name": "MB_%s_STATUS" % '_'.join(map(str, location)),
              "type": LOCATION_VAR_INPUT, "size": 2,
              "IEC_type": "INT",
              "io_name": "status",
              "location": "%s%s" % ('W', ".".join(map(str, current_location + [7]))),
              "description": "通信状态(INT)",
              "children": []},
             {"name": "Count(UDINT)", "var_name": "MB_%s_COUNT" % '_'.join(map(str, location)),
              "type": LOCATION_VAR_INPUT, "size": 4,
              "IEC_type": "UDINT",
              "io_name": "okcount",
              "location": "%s%s" % ('D', ".".join(map(str, current_location + [8]))),
              "description": "通信计数,UDINT",
              "children": []},
             {"name": "ErrCount(UDINT)", "var_name": "MB_%s_ERRCNT" % '_'.join(map(str, location)),
              "type": LOCATION_VAR_INPUT, "size": 4,
              "IEC_type": "UDINT",
              "io_name": "errcount",
              "location": "%s%s" % ('D', ".".join(map(str, current_location + [9]))),
              "description": "错误计数,UDINT",
              "children": []},
             {"name": "Enable(BOOL)", "var_name": "MB_%s_EN" % '_'.join(map(str, location)), "type": LOCATION_VAR_INPUT,
              "size": 1,
              "IEC_type": "BOOL",
              "io_name": "enable",
              "location": "%s%s" % ('X', ".".join(map(str, current_location + [10]))),
              "description": "使能,BOOL",
              "children": []},
         ]}]


def tcp_params(location):
    current_location = list(location)
    if len(current_location) == 2:
        current_location += [0, 0]
    elif len(current_location) == 3:
        current_location += [0]
    else:
        raise Exception(_("Error: location size must 2 or 3. current=%s") % location)
    return [
        {"name": '通信参数',
         "type": LOCATION_CONFNODE,
         "location": ".".join([str(i) for i in current_location]) + ".x",
         "children": [
             {"name": "ID(USINT)", "var_name": "MB_%s_ID" % '_'.join(map(str, location)), "type": LOCATION_VAR_OUTPUT,
              "size": 1,
              "IEC_type": "USINT",
              "io_name": "id",
              "location": "%s%s" % ('B', ".".join(map(str, current_location + [1]))),
              "description": "ID Address,USINT",
              "children": []},
             {"name": "Period(UDINT)", "var_name": "MB_%s_INTERVAL" % '_'.join(map(str, location)),
              "type": LOCATION_VAR_OUTPUT, "size": 4,
              "IEC_type": "UDINT",
              "io_name": "period",
              "location": "%s%s" % ('D', ".".join(map(str, current_location + [2]))),
              "description": "查询周期,UDINT,单位ms",
              "children": []},
             {"name": "Status(INT)", "var_name": "MB_%s_STATUS" % '_'.join(map(str, location)),
              "type": LOCATION_VAR_INPUT, "size": 2,
              "IEC_type": "INT",
              "io_name": "status",
              "location": "%s%s" % ('W', ".".join(map(str, current_location + [3]))),
              "description": "通信状态(INT)",
              "children": []},
             {"name": "Count(UDINT)", "var_name": "MB_%s_COUNT" % '_'.join(map(str, location)),
              "type": LOCATION_VAR_INPUT, "size": 4,
              "IEC_type": "UDINT",
              "io_name": "okcount",
              "location": "%s%s" % ('D', ".".join(map(str, current_location + [4]))),
              "description": "通信计数,UDINT",
              "children": []},
             {"name": "ErrCount(UDINT)", "var_name": "MB_%s_ERRCNT" % '_'.join(map(str, location)),
              "type": LOCATION_VAR_INPUT, "size": 4,
              "IEC_type": "UDINT",
              "io_name": "errcount",
              "location": "%s%s" % ('D', ".".join(map(str, current_location + [5]))),
              "description": "错误计数,UDINT",
              "children": []},
             {"name": "Enable(BOOL)", "var_name": "MB_%s_EN" % '_'.join(map(str, location)), "type": LOCATION_VAR_INPUT,
              "size": 1,
              "IEC_type": "BOOL",
              "io_name": "enable",
              "location": "%s%s" % ('X', ".".join(map(str, current_location + [6]))),
              "description": "使能,BOOL",
              "children": []},
         ]}]


class _RequestPlug(object):
    XSD = """<?xml version="1.0" encoding="utf-8" ?>
    <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
      <xsd:element name="ModbusRequest">
        <xsd:complexType>
          <xsd:attribute name="Function" type="xsd:string" use="optional" default="01 - Read Coils"/>
          <xsd:attribute name="Baud_Rate"   type="xsd:string"  use="optional" default="9600"/>
          <xsd:attribute name="Parity"      type="xsd:string"  use="optional" default="even"/>
          <xsd:attribute name="Data_Bits"   type="xsd:string"  use="optional" default="8"/>
          <xsd:attribute name="Stop_Bits"   type="xsd:string"  use="optional" default="1"/>
          <xsd:attribute name="SlaveID" use="optional" default="1">
            <xsd:simpleType>
                <xsd:restriction base="xsd:integer">
                    <xsd:minInclusive value="0"/>
                    <xsd:maxInclusive value="255"/>
                </xsd:restriction>
            </xsd:simpleType>
          </xsd:attribute>
          <xsd:attribute name="Nr_of_Channels" use="optional" default="1">
            <xsd:simpleType>
                <xsd:restriction base="xsd:integer">
                    <xsd:minInclusive value="1"/>
                    <xsd:maxInclusive value="2000"/>
                </xsd:restriction>
            </xsd:simpleType>
          </xsd:attribute>
          <xsd:attribute name="Start_Address" use="optional" default="0">
            <xsd:simpleType>
                <xsd:restriction base="xsd:integer">
                    <xsd:minInclusive value="0"/>
                    <xsd:maxInclusive value="65535"/>
                </xsd:restriction>
            </xsd:simpleType>
          </xsd:attribute>
          <xsd:attribute name="Timeout_in_ms" use="optional" default="100">
            <xsd:simpleType>
                <xsd:restriction base="xsd:integer">
                    <xsd:minInclusive value="1"/>
                    <xsd:maxInclusive value="100000"/>
                </xsd:restriction>
            </xsd:simpleType>
          </xsd:attribute>
        <xsd:attribute name="Delay_in_ms" use="optional" default="100">
            <xsd:simpleType>
                <xsd:restriction base="xsd:integer">
                    <xsd:minInclusive value="1"/>
                    <xsd:maxInclusive value="2147483647"/>
                </xsd:restriction>
            </xsd:simpleType>
          </xsd:attribute>
      <xsd:attribute name="endian"   type="xsd:string" use="optional" default="default-1234"/>

        </xsd:complexType>
      </xsd:element>
    </xsd:schema>
    """

    def GetParamsAttributes(self, path=None):
        infos = ConfigTreeNode.GetParamsAttributes(self, path=path)
        for element in infos:
            if element["name"] == "ModbusRequest":
                for child in element["children"]:
                    if child["name"] == "Function":
                        lis = list(modbus_function_dict.keys())
                        lis.sort()
                        child["type"] = lis
                    if child["name"] == "Baud_Rate":
                        child["type"] = modbus_serial_baudrate_list
                    if child["name"] == "Data_Bits":
                        child["type"] = modbus_serial_databits_list
                    if child["name"] == "Stop_Bits":
                        child["type"] = modbus_serial_stopbits_list
                    if child["name"] == "Parity":
                        child["type"] = list(modbus_serial_parity_dict.keys())
                    if child["name"] == "endian":
                        child["type"] = ["default-1234", 'lit-4321', 'lar-2143', 'lit-3412']
        return infos

    def GetVariableLocationTree(self):
        current_location = self.GetCurrentLocation()
        name = self.BaseParams.getName()
        address = self.GetParamsAttributes()[0]["children"][7]["value"]
        count = self.GetParamsAttributes()[0]["children"][6]["value"]
        function = self.GetParamsAttributes()[0]["children"][0]["value"]
        # 'BOOL' or 'WORD'
        datatype = modbus_function_dict[function][3]
        # 1 or 16
        datasize = modbus_function_dict[function][4]
        # 'Q' for coils and holding registers, 'I' for input discretes and input registers
        # datazone = modbus_function_dict[function][5]
        # 'X' for bits, 'W' for words
        datatacc = modbus_function_dict[function][6]
        # 'Coil', 'Holding Register', 'Input Discrete' or 'Input Register'
        dataname = modbus_function_dict[function][7]
        entries = []
        for offset in range(address, address + count):
            entries.append({
                "name": dataname + " " + str(offset),
                "type": LOCATION_VAR_MEMORY,
                "size": datasize,
                "IEC_type": datatype,
                "var_name": "MB_" + "".join([w[0] for w in dataname.split()]) + "_" + str(offset),
                "location": datatacc + ".".join([str(i) for i in current_location]) + "." + str(offset),
                "description": "description",
                "children": []})
        return {"name": name,
                "type": LOCATION_CONFNODE,
                "location": ".".join([str(i) for i in current_location]) + ".x",
                "children": entries + params(current_location)}

    def CTNGenerate_C(self, buildpath, locations):
        """
        Generate C code
        @param current_location: Tupple containing plugin IEC location : %I0.0.4.5 => (0,0,4,5)
        @param locations: List of complete variables locations \
            [{"IEC_TYPE" : the IEC type (i.e. "INT", "STRING", ...)
            "NAME" : name of the variable (generally "__IW0_1_2" style)
            "DIR" : direction "Q","I" or "M"
            "SIZE" : size "X", "B", "W", "D", "L"
            "LOC" : tuple of interger for IEC location (0,1,2,...)
            }, ...]
        @return: [(C_file_name, CFLAGS),...] , LDFLAGS_TO_APPEND
        """
        # return LibCFilesAndCFLAGS, LibLDFLAGS, Libs, LibExtraFiles
        return [], "", False, ['modbus']


#
#
#
# S E R V E R    M E M O R Y    A R E A       #
#
#
#

# dictionary implementing:
# key - string with the description we want in the request plugin GUI
# list - (modbus function number, request type, max count value)
modbus_memtype_dict = {
    "01 - Coils": ['1', 'rw_bits', 0, "BOOL", 1, "Q", "X", "Coil"],
    "02 - Input Discretes": ['2', 'ro_bits', 0, "BOOL", 1, "I", "X", "Input Discrete"],
    "03 - Holding Registers": ['3', 'rw_words', 0, "WORD", 16, "Q", "W", "Holding Register"],
    "04 - Input Registers": ['4', 'ro_words', 0, "WORD", 16, "I", "W", "Input Register"],
}


class _MemoryAreaPlug(object):
    XSD = """<?xml version="1.0" encoding="utf-8" ?>
    <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
      <xsd:element name="MemoryArea">
        <xsd:complexType>
          <xsd:attribute name="MemoryAreaType" type="xsd:string" use="optional" default="01 - Coils"/>
          <xsd:attribute name="Nr_of_Channels" use="optional" default="1">
            <xsd:simpleType>
                <xsd:restriction base="xsd:integer">
                    <xsd:minInclusive value="1"/>
                    <xsd:maxInclusive value="65536"/>
                </xsd:restriction>
            </xsd:simpleType>
          </xsd:attribute>
          <xsd:attribute name="Start_Address" use="optional" default="0">
            <xsd:simpleType>
                <xsd:restriction base="xsd:integer">
                    <xsd:minInclusive value="0"/>
                    <xsd:maxInclusive value="65535"/>
                </xsd:restriction>
            </xsd:simpleType>
          </xsd:attribute>
        </xsd:complexType>
      </xsd:element>
    </xsd:schema>
    """

    def GetParamsAttributes(self, path=None):
        infos = ConfigTreeNode.GetParamsAttributes(self, path=path)
        for element in infos:
            if element["name"] == "MemoryArea":
                for child in element["children"]:
                    if child["name"] == "MemoryAreaType":
                        lis = list(modbus_memtype_dict.keys())
                        lis.sort()
                        child["type"] = lis
        return infos

    def GetVariableLocationTree(self):
        current_location = self.GetCurrentLocation()
        name = self.BaseParams.getName()
        address = self.GetParamsAttributes()[0]["children"][2]["value"]
        count = self.GetParamsAttributes()[0]["children"][1]["value"]
        function = self.GetParamsAttributes()[0]["children"][0]["value"]
        # 'BOOL' or 'WORD'
        datatype = modbus_memtype_dict[function][3]
        # 1 or 16
        datasize = modbus_memtype_dict[function][4]
        # 'Q' for coils and holding registers, 'I' for input discretes and input registers
        # datazone = modbus_memtype_dict[function][5]
        # 'X' for bits, 'W' for words
        datatacc = modbus_memtype_dict[function][6]
        # 'Coil', 'Holding Register', 'Input Discrete' or 'Input Register'
        dataname = modbus_memtype_dict[function][7]
        entries = []
        for offset in range(address, address + count):
            entries.append({
                "name": dataname + " " + str(offset),
                "type": LOCATION_VAR_MEMORY,
                "size": datasize,
                "IEC_type": datatype,
                "var_name": "MB_" + "".join([w[0] for w in dataname.split()]) + "_" + str(offset),
                "location": datatacc + ".".join([str(i) for i in current_location]) + "." + str(offset),
                "description": "description",
                "children": []})
        return {"name": name,
                "type": LOCATION_CONFNODE,
                "location": ".".join([str(i) for i in current_location]) + ".x",
                "children": entries}

    def CTNGenerate_C(self, buildpath, locations):
        """
        Generate C code
        @param current_location: Tupple containing plugin IEC location : %I0.0.4.5 => (0,0,4,5)
        @param locations: List of complete variables locations \
            [{"IEC_TYPE" : the IEC type (i.e. "INT", "STRING", ...)
            "NAME" : name of the variable (generally "__IW0_1_2" style)
            "DIR" : direction "Q","I" or "M"
            "SIZE" : size "X", "B", "W", "D", "L"
            "LOC" : tuple of interger for IEC location (0,1,2,...)
            }, ...]
        @return: [(C_file_name, CFLAGS),...] , LDFLAGS_TO_APPEND
        """
        return [], "", False, ['modbus']


#
#
#
# T C P    C L I E N T                 #
#
#
#

class _ModbusTCPclientPlug(object):
    XSD = """<?xml version="1.0" encoding="utf-8" ?>
    <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
      <xsd:element name="ModbusTCPclient">
        <xsd:complexType>
          <xsd:attribute name="Remote_IP_Address" type="xsd:string" use="optional" default="localhost"/>
          <xsd:attribute name="Remote_Port_Number" type="xsd:string" use="optional" default="502"/>
          <xsd:attribute name="Invocation_Rate_in_ms" use="optional" default="100">
            <xsd:simpleType>
                <xsd:restriction base="xsd:unsignedLong">
                    <xsd:minInclusive value="1"/>
                    <xsd:maxInclusive value="2147483647"/>
                </xsd:restriction>
            </xsd:simpleType>
          </xsd:attribute>
        </xsd:complexType>
      </xsd:element>
    </xsd:schema>
    """
    # NOTE: Max value of 2147483647 (i32_max) for Invocation_Rate_in_ms
    # corresponds to aprox 25 days.
    CTNChildrenTypes = [("ModbusRequest", _RequestPlug, "Request")]
    # TODO: Replace with CTNType !!!
    PlugType = "ModbusTCPclient"

    # Return the number of (modbus library) nodes this specific TCP client will need
    #   return type: (tcp nodes, rtu nodes, ascii nodes)
    def GetNodeCount(self):
        return (1, 0, 0)

    def GetVariableLocationTree(self):
        current_location = self.GetCurrentLocation()
        name = self.BaseParams.getName()
        children = []
        for child in self.IECSortedChildren():
            children.append(child.GetVariableLocationTree())

        return {
            "name": name,
            "type": LOCATION_CONFNODE,
            "location": ".".join([str(i) for i in current_location]) + ".x",
            "children": children + tcp_params(current_location)}

    def CTNGenerate_C(self, buildpath, locations):
        """
        Generate C code
        @param current_location: Tupple containing plugin IEC location : %I0.0.4.5 => (0,0,4,5)
        @param locations: List of complete variables locations \
            [{"IEC_TYPE" : the IEC type (i.e. "INT", "STRING", ...)
            "NAME" : name of the variable (generally "__IW0_1_2" style)
            "DIR" : direction "Q","I" or "M"
            "SIZE" : size "X", "B", "W", "D", "L"
            "LOC" : tuple of interger for IEC location (0,1,2,...)
            }, ...]
        @return: [(C_file_name, CFLAGS),...] , LDFLAGS_TO_APPEND
        """
        return [], "-DMODBUS_TCP", False, ['modbus']


#
#
#
# T C P    S E R V E R                 #
#
#
#

class _ModbusTCPserverPlug(object):
    # NOTE: the Port number is a 'string' and not an 'integer'!
    # This is because the underlying modbus library accepts strings
    # (e.g.: well known port names!)
    XSD = """<?xml version="1.0" encoding="utf-8" ?>
    <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
      <xsd:element name="ModbusServerNode">
        <xsd:complexType>
          <xsd:attribute name="Local_IP_Address" type="xsd:string" use="optional"  default="#ANY#"/>
          <xsd:attribute name="Local_Port_Number" type="xsd:string" use="optional" default="502"/>
          <xsd:attribute name="SlaveID" use="optional" default="0">
            <xsd:simpleType>
                <xsd:restriction base="xsd:integer">
                    <xsd:minInclusive value="0"/>
                    <xsd:maxInclusive value="255"/>
                </xsd:restriction>
            </xsd:simpleType>
          </xsd:attribute>
          <xsd:attribute name="endian"   type="xsd:string" use="optional" default="default-1234"/>
        </xsd:complexType>
      </xsd:element>
    </xsd:schema>
    """
    CTNChildrenTypes = [("MemoryArea", _MemoryAreaPlug, "Memory Area")]
    # TODO: Replace with CTNType !!!
    PlugType = "ModbusTCPserver"

    # Return the number of (modbus library) nodes this specific TCP server will need
    #   return type: (tcp nodes, rtu nodes, ascii nodes)
    def GetNodeCount(self):
        return (1, 0, 0)

    def GetParamsAttributes(self, path=None):
        infos = ConfigTreeNode.GetParamsAttributes(self, path=path)
        for element in infos:
            if element["name"] == "ModbusRTUslave":
                for child in element["children"]:
                    if child["name"] == "Baud_Rate":
                        child["type"] = modbus_serial_baudrate_list
                    if child["name"] == "Data_Bits":
                        child["type"] = modbus_serial_databits_list
                    if child["name"] == "Stop_Bits":
                        child["type"] = modbus_serial_stopbits_list
                    if child["name"] == "Parity":
                        child["type"] = list(modbus_serial_parity_dict.keys())
                    if child["name"] == "endian":
                        child["type"] = ["default-1234", 'lit-4321', 'lar-2143', 'lit-3412']
        return infos

    # Return a list with a single tuple conatining the (location, port number)
    #     location: location of this node in the configuration tree
    #     port number: IP port used by this Modbus/IP server
    def GetIPServerPortNumbers(self):
        port = self.GetParamsAttributes()[0]["children"][1]["value"]
        return [(self.GetCurrentLocation(), port)]

    def GetVariableLocationTree(self):
        current_location = self.GetCurrentLocation()
        name = self.BaseParams.getName()
        children = []
        for child in self.IECSortedChildren():
            children.append(child.GetVariableLocationTree())

        return {
            "name": name,
            "type": LOCATION_CONFNODE,
            "location": ".".join([str(i) for i in current_location]) + ".x",
            "children": children + tcp_params(current_location)}

    def CTNGenerate_C(self, buildpath, locations):
        """
        Generate C code
        @param current_location: Tupple containing plugin IEC location : %I0.0.4.5 => (0,0,4,5)
        @param locations: List of complete variables locations \
            [{"IEC_TYPE" : the IEC type (i.e. "INT", "STRING", ...)
            "NAME" : name of the variable (generally "__IW0_1_2" style)
            "DIR" : direction "Q","I" or "M"
            "SIZE" : size "X", "B", "W", "D", "L"
            "LOC" : tuple of interger for IEC location (0,1,2,...)
            }, ...]
        @return: [(C_file_name, CFLAGS),...] , LDFLAGS_TO_APPEND
        """
        return [], "-DMODBUS_TCP", False, ['modbus']


#
#
#
# R T U    C L I E N T                 #
#
#
#

class _ModbusRTUclientPlug(object):
    XSD = """<?xml version="1.0" encoding="utf-8" ?>
    <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
      <xsd:element name="ModbusRTUclient">
        <xsd:complexType>
          <xsd:attribute name="Serial_Port" type="xsd:string"  use="optional" default="/dev/ttyS0"/>
          <xsd:attribute name="Baud_Rate"   type="xsd:string"  use="optional" default="9600"/>
          <xsd:attribute name="Parity"      type="xsd:string"  use="optional" default="even"/>
          <xsd:attribute name="Data_Bits"   type="xsd:string"  use="optional" default="8"/>
          <xsd:attribute name="Stop_Bits"   type="xsd:string"  use="optional" default="1"/>
          <xsd:attribute name="Delay_in_ms" use="optional" default="100">
            <xsd:simpleType>
                <xsd:restriction base="xsd:integer">
                    <xsd:minInclusive value="1"/>
                    <xsd:maxInclusive value="2147483647"/>
                </xsd:restriction>
            </xsd:simpleType>
          </xsd:attribute>
        </xsd:complexType>
      </xsd:element>
    </xsd:schema>
    """
    # NOTE: Max value of 2147483647 (i32_max) for Invocation_Rate_in_ms
    # corresponds to aprox 25 days.
    CTNChildrenTypes = [("ModbusRequest", _RequestPlug, "Request")]
    # TODO: Replace with CTNType !!!
    PlugType = "ModbusRTUclient"

    def GetVariableLocationTree(self):
        current_location = self.GetCurrentLocation()
        name = self.BaseParams.getName()
        children = []
        for child in self.IECSortedChildren():
            children.append(child.GetVariableLocationTree())

        return {
            "name": name,
            "type": LOCATION_CONFNODE,
            "location": ".".join([str(i) for i in current_location]) + ".x",
            "children": children}

    def GetParamsAttributes(self, path=None):
        infos = ConfigTreeNode.GetParamsAttributes(self, path=path)
        for element in infos:
            if element["name"] == "ModbusRTUclient":
                for child in element["children"]:
                    if child["name"] == "Baud_Rate":
                        child["type"] = modbus_serial_baudrate_list
                    if child["name"] == "Data_Bits":
                        child["type"] = modbus_serial_databits_list
                    if child["name"] == "Stop_Bits":
                        child["type"] = modbus_serial_stopbits_list
                    if child["name"] == "Parity":
                        child["type"] = list(modbus_serial_parity_dict.keys())
        return infos

    # Return the number of (modbus library) nodes this specific RTU client will need
    #   return type: (tcp nodes, rtu nodes, ascii nodes)
    def GetNodeCount(self):
        return (0, 1, 0)

    def CTNGenerate_C(self, buildpath, locations):
        """
        Generate C code
        @param current_location: Tupple containing plugin IEC location : %I0.0.4.5 => (0,0,4,5)
        @param locations: List of complete variables locations \
            [{"IEC_TYPE" : the IEC type (i.e. "INT", "STRING", ...)
            "NAME" : name of the variable (generally "__IW0_1_2" style)
            "DIR" : direction "Q","I" or "M"
            "SIZE" : size "X", "B", "W", "D", "L"
            "LOC" : tuple of interger for IEC location (0,1,2,...)
            }, ...]
        @return: [(C_file_name, CFLAGS),...] , LDFLAGS_TO_APPEND
        """
        return [], "-DMODBUS_RTU", False, ['modbus']


#
#
#
# R T U    S L A V E                   #
#
#
#


class _ModbusRTUslavePlug(object):
    XSD = """<?xml version="1.0" encoding="utf-8" ?>
    <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
      <xsd:element name="ModbusRTUslave">
        <xsd:complexType>
          <xsd:attribute name="Serial_Port" type="xsd:string"  use="optional" default="/dev/ttyS0"/>
          <xsd:attribute name="Baud_Rate"   type="xsd:string"  use="optional" default="9600"/>
          <xsd:attribute name="Parity"      type="xsd:string"  use="optional" default="even"/>
          <xsd:attribute name="Data_Bits"   type="xsd:string"  use="optional" default="8"/>
          <xsd:attribute name="Stop_Bits"   type="xsd:string"  use="optional" default="1"/>
          <xsd:attribute name="SlaveID" use="optional" default="1">
            <xsd:simpleType>
                <xsd:restriction base="xsd:integer">
                    <xsd:minInclusive value="1"/>
                    <xsd:maxInclusive value="255"/>
                </xsd:restriction>
            </xsd:simpleType>
          </xsd:attribute>
        <xsd:attribute name="endian"   type="xsd:string" use="optional" default="default-1234"/>
        </xsd:complexType>
      </xsd:element>
    </xsd:schema>
    """
    CTNChildrenTypes = [("MemoryArea", _MemoryAreaPlug, "Memory Area")]
    # TODO: Replace with CTNType !!!
    PlugType = "ModbusRTUslave"

    def GetVariableLocationTree(self):
        current_location = self.GetCurrentLocation()
        name = self.BaseParams.getName()
        children = []
        for child in self.IECSortedChildren():
            children.append(child.GetVariableLocationTree())

        return {
            "name": name,
            "type": LOCATION_CONFNODE,
            "location": ".".join([str(i) for i in current_location]) + ".x",
            "children": children + params(current_location)}

    def GetParamsAttributes(self, path=None):
        infos = ConfigTreeNode.GetParamsAttributes(self, path=path)
        for element in infos:
            if element["name"] == "ModbusRTUslave":
                for child in element["children"]:
                    if child["name"] == "Baud_Rate":
                        child["type"] = modbus_serial_baudrate_list
                    if child["name"] == "Data_Bits":
                        child["type"] = modbus_serial_databits_list
                    if child["name"] == "Stop_Bits":
                        child["type"] = modbus_serial_stopbits_list
                    if child["name"] == "Parity":
                        child["type"] = list(modbus_serial_parity_dict.keys())
                    if child["name"] == "endian":
                        child["type"] = ["default-1234", 'lit-4321', 'lar-2143', 'lit-3412']
        return infos

    # Return the number of (modbus library) nodes this specific RTU slave will need
    #   return type: (tcp nodes, rtu nodes, ascii nodes)
    def GetNodeCount(self):
        return (0, 1, 0)

    def CTNGenerate_C(self, buildpath, locations):
        """
        Generate C code
        @param current_location: Tupple containing plugin IEC location : %I0.0.4.5 => (0,0,4,5)
        @param locations: List of complete variables locations \
            [{"IEC_TYPE" : the IEC type (i.e. "INT", "STRING", ...)
            "NAME" : name of the variable (generally "__IW0_1_2" style)
            "DIR" : direction "Q","I" or "M"
            "SIZE" : size "X", "B", "W", "D", "L"
            "LOC" : tuple of interger for IEC location (0,1,2,...)
            }, ...]
        @return: [(C_file_name, CFLAGS),...] , LDFLAGS_TO_APPEND
        """
        return [], "-DMODBUS_RTU", False, ['modbus']


def _lt_to_str(loctuple):
    return '.'.join(map(str, loctuple))


#
#
#
# R O O T    C L A S S                #
#
#
#
class RootClass(object):
    XSD = """<?xml version="1.0" encoding="utf-8" ?>
    <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
      <xsd:element name="ModbusRoot">
        <xsd:complexType>
          <xsd:attribute name="MaxRemoteTCPclients" use="optional" default="10">
            <xsd:simpleType>
                <xsd:restriction base="xsd:integer">
                    <xsd:minInclusive value="0"/>
                    <xsd:maxInclusive value="65535"/>
                </xsd:restriction>
            </xsd:simpleType>
          </xsd:attribute>
        </xsd:complexType>
      </xsd:element>
    </xsd:schema>
    """
    CTNChildrenTypes = [("ModbusTCPclient", _ModbusTCPclientPlug, "Modbus TCP Client"),
                        ("ModbusTCPserver", _ModbusTCPserverPlug, "Modbus TCP Server"),
                        ("ModbusRTUclient", _ModbusRTUclientPlug, "Modbus RTU Client"),
                        ("ModbusRTUslave", _ModbusRTUslavePlug, "Modbus RTU Slave")]
    mems = []

    # Return the number of (modbus library) nodes this specific instance of the modbus plugin will need
    #   return type: (tcp nodes, rtu nodes, ascii nodes)
    def GetNodeCount(self):
        max_remote_tcpclient = self.GetParamsAttributes()[
            0]["children"][0]["value"]
        total_node_count = [max_remote_tcpclient, 0, 0]
        for child in self.IECSortedChildren():
            # ask each child how many nodes it needs, and add them all up.
            total_node_count = list(tuple(x1 + x2 for x1, x2 in list(zip(total_node_count, child.GetNodeCount()))))
        return total_node_count

    # Return a list with tuples of the (location, port numbers) used by all
    # the Modbus/IP servers
    def GetIPServerPortNumbers(self):
        IPServer_port_numbers = []
        for child in self.IECSortedChildren():
            if child.CTNType == "ModbusTCPserver":
                IPServer_port_numbers.extend(child.GetIPServerPortNumbers())
        return IPServer_port_numbers

    def checkRanger(self, name, type, start_address, length):
        for i in self.mems:
            if (type == i['type']) and ((start_address >= i['start'] and start_address <= i['start'] + i[
                'length'] - 1) or (start_address + length - 1 >= i['start'] and start_address + length - 1 <= i[
                'start'] + \
                                   i['length'] - 1)):
                raise Exception(_("Modbus MemoryArea Conflict: {name} & {iname} ! build cancel!\n").format(name=name,
                                                                                                           iname=i[
                                                                                                               'name']))
        self.mems.append({'name': name, 'type': type, 'start': start_address, 'length': length})

    def CTNGenerate_C(self, buildpath, locations):
        # print "#############"
        # print self.__class__
        # print type(self)
        # print "self.CTNType >>>"
        # print self.CTNType
        # print "type(self.CTNType) >>>"
        # print type(self.CTNType)
        # print "#############"
        self.mems.clear()
        loc_dict = {"locstr": "_".join(map(str, self.GetCurrentLocation()))}

        # Determine the number of (modbus library) nodes ALL instances of the modbus plugin will need
        #   total_node_count: (tcp nodes, rtu nodes, ascii nodes)
        # Also get a list with tuples of (location, IP port numbers) used by all the Modbus/IP server nodes
        #   This list is later used to search for duplicates in port numbers!
        #   IPServer_port_numbers = [(location ,IPserver_port_number), ...]
        #       location: tuple similar to (0, 3, 1) representing the location in the configuration tree "0.3.1.x"
        # IPserver_port_number: a number (i.e. port number used by the
        # Modbus/IP server)
        total_node_count = [0, 0, 0]
        IPServer_port_numbers = []
        for CTNInstance in self.GetCTRoot().IterChildren():
            if CTNInstance.CTNType == "modbus":
                # ask each modbus plugin instance how many nodes it needs, and
                # add them all up.
                total_node_count = list(tuple(x1 + x2 for x1, x2 in list(zip(
                    total_node_count, CTNInstance.GetNodeCount()))))
                IPServer_port_numbers.extend(
                    CTNInstance.GetIPServerPortNumbers())

        # Search for use of duplicate port numbers by Modbus/IP servers
        # print IPServer_port_numbers
        # ..but first define a lambda function to convert a tuple with the config tree location to a nice looking string
        #   for e.g., convert the tuple (0, 3, 4) to "0.3.4"

        for i in range(0, len(IPServer_port_numbers) - 1):
            for j in range(i + 1, len(IPServer_port_numbers)):
                if IPServer_port_numbers[i][1] == IPServer_port_numbers[j][1]:
                    self.GetCTRoot().logger.write_warning(
                        _("Error: Modbus/IP Servers %{a1}.x and %{a2}.x use the same port number {a3}.\n").
                            format(
                            a1=_lt_to_str(IPServer_port_numbers[i][0]),
                            a2=_lt_to_str(IPServer_port_numbers[j][0]),
                            a3=IPServer_port_numbers[j][1]))
                    raise Exception
                    # TODO: return an error code instead of raising an
                    # exception

        # Determine the current location in Beremiz's project configuration
        # tree
        current_location = self.GetCurrentLocation()

        # define a unique name for the generated C and h files
        prefix = "_".join(map(str, current_location))
        Gen_MB_c_path = os.path.join(buildpath, "MB_%s.cpp" % prefix)
        Gen_MB_h_path = os.path.join(buildpath, "MB_%s.h" % prefix)
        c_filename = os.path.join(os.path.split(__file__)[0], "mb_runtime.c")
        h_filename = os.path.join(os.path.split(__file__)[0], "mb_runtime.h")

        tcpclient_reqs_count = 0
        rtuclient_reqs_count = 0
        ascclient_reqs_count = 0
        tcpclient_node_count = 0
        rtuclient_node_count = 0
        ascclient_node_count = 0
        tcpserver_node_count = 0
        rtuserver_node_count = 0
        server_node_count = 0
        ascserver_node_count = 0
        nodeid = 0
        client_nodeid = 0
        client_requestid = 0
        server_id = 0
        buffer = ''
        server_mem_robits_t = ''
        server_mem_rwbits_t = ''
        server_mem_rowords_t = ''
        server_mem_words_t = ''
        server_node_list = []
        client_node_list = []
        client_request_list = []
        client_request_buffer = []
        server_memarea_list = []
        loc_vars = []
        init = []
        publish = []
        retrieve = []
        loc_vars_list = []  # list of variables already declared in C code!
        _publish = []
        _retrieve = []
        _globl = ['int inwrite=0;']
        _remove = []
        for child in self.IECSortedChildren():
            # print "<<<<<<<<<<<<<"
            # print "child (self.IECSortedChildren())----->"
            # print child.__class__
            # print ">>>>>>>>>>>>>"
            #
            if child.PlugType == "ModbusTCPserver":
                tcpserver_node_count += 1
                server_node_count += 1
                ip, port, slaveid, endian = GetCTVals(child, range(4))
                IEC_Channel = child.BaseParams.getIEC_Channel()

                new_node = GetTCPServerNodePrinted(self, child)
                if new_node is None:
                    return [], "", False, []
                server_node_list.append(new_node)
                #
                inx = 1
                params = {1: {'type': 'uint8_t', 'name': 'server_nodes[%d].slave_id' % (server_node_count - 1)},
                          2: {'type': 'uint32_t', 'name': 'server_nodes[%d].period' % (server_node_count - 1)},
                          3: {'type': 'int16_t',
                              'name': 'server_nodes[%d].prev_error' % (server_node_count - 1)},
                          4: {'type': 'uint32_t', 'name': 'server_nodes[%d].okcount' % (server_node_count - 1)},
                          5: {'type': 'uint32_t', 'name': 'server_nodes[%d].errcount' % (server_node_count - 1)},
                          6: {'type': 'uint8_t', 'name': 'server_nodes[%d].enable' % (server_node_count - 1)},
                          }
                for subchild in child.IECSortedChildren():
                    new_memarea = GetTCPServerMemAreaPrinted(
                        self, subchild, nodeid)
                    if new_memarea is None:
                        return [], "", False, []
                    server_memarea_list.append(new_memarea)
                    function = subchild.GetParamsAttributes()[
                        0]["children"][0]["value"]
                    # 'ro_bits', 'rw_bits', 'ro_words' or 'rw_words'
                    memarea = modbus_memtype_dict[function][1] + str(inx)
                    m = subchild.MemoryArea
                    Nr_of_Channels = int(m.get('Nr_of_Channels', 1))
                    buffer += '\tuint16_t %s[%d];\n' % (memarea, Nr_of_Channels)
                    start_address = int(GetCTVal(subchild, 2))
                    name = subchild.BaseParams.getName()
                    self.checkRanger(name, function[1], start_address, Nr_of_Channels)
                    if modbus_memtype_dict[function][1] == 'ro_bits':
                        server_mem_robits_t += '{%d, %d, %s},\n' % (start_address, Nr_of_Channels, memarea)
                    elif modbus_memtype_dict[function][1] == 'rw_bits':
                        server_mem_rwbits_t += '{%d, %d, %s},\n' % (start_address, Nr_of_Channels, memarea)
                    elif modbus_memtype_dict[function][1] == 'ro_words':
                        server_mem_rowords_t += '{%d, %d, %s},\n' % (start_address, Nr_of_Channels, memarea)
                    elif modbus_memtype_dict[function][1] == 'rw_words':
                        server_mem_words_t += '{%d, %d, %s},\n' % (start_address, Nr_of_Channels, memarea)
                    inx += 1
                    for iecvar in subchild.GetLocations():
                        # print repr(iecvar)
                        absloute_address = iecvar["LOC"][3]
                        relative_addr = absloute_address - start_address
                        # test if relative address in request specified range
                        if relative_addr in range(int(GetCTVal(subchild, 1))) and len(iecvar['LOC']) == 4:
                            if str(iecvar["NAME"]) not in loc_vars_list:
                                method = {'lit-4321': "s4321", 'lar-2143': "s2143", 'lit-3412': "s3412",
                                          "default-1234": "s1234"}
                                if endian == "default-1234" or iecvar['SIZE'] in ['X', 'B']:
                                    loc_vars.append(
                                        str(iecvar["IEC_TYPE"]) + " *" + str(iecvar["NAME"]) + " =(%s *) &%s[%d];" % (
                                            str(iecvar["IEC_TYPE"]), memarea, relative_addr))
                                    loc_vars_list.append(str(iecvar["NAME"]))
                                    modbus_memtype_dict[function][2] = modbus_memtype_dict[function][2] + 1
                                else:
                                    if iecvar["DIR"] in ["I", "M"]:
                                        _retrieve.append(
                                            "%s_%s((const char *)&%s[%d],(char *)%s);" % (
                                                method[endian], iecvar['SIZE'], memarea, relative_addr, iecvar["NAME"]))
                                        init.append("%s_%s((const char *)%s,(char *)&%s[%d]);" % (
                                            method[endian], iecvar['SIZE'], iecvar["NAME"], memarea, relative_addr))

                                    if iecvar["DIR"] in ["Q", "M"]:
                                        _publish.append("%s_%s((const char *)%s,(char *)&%s[%d]);" % (
                                            method[endian], iecvar['SIZE'], iecvar["NAME"], memarea, relative_addr))
                                    loc_vars_list.append(str(iecvar["NAME"]))
                                    modbus_memtype_dict[function][2] = modbus_memtype_dict[function][2] + 1
                            else:
                                self.GetCTRoot().logger.write_warning(
                                    _("Waring: Variable Dup {loc} ,{name} \n").format(loc=iecvar["LOC"],
                                                                                      name=str(iecvar["NAME"])))
                        # else:
                        #     self.GetCTRoot().logger.write_error(
                        #         _("Error: Variable Illigl %s ,%s \n") % (iecvar["LOC"], str(iecvar["NAME"])))
                for iecvar in self.GetLocations():
                    absloute_address = iecvar["LOC"][3]
                    relative_addr = absloute_address - start_address
                    # test if relative address in request specified range
                    if iecvar['LOC'][1] == IEC_Channel and len(iecvar['LOC']) == 5 and params.get(iecvar['LOC'][4]):
                        # loc_vars.append("extern %s *%s;" % (IEC_C[iecvar['IEC_TYPE']], str(iecvar["NAME"])))
                        # loc_vars.append(
                        #     "%s *" % params[iecvar['LOC'][4]]['type'] + str(iecvar["NAME"]) + " = &%s;" % (
                        #         params[iecvar['LOC'][4]]['name']))
                        loc_vars_list.append(str(iecvar["NAME"]))
                        if iecvar["DIR"] in ["I", "M"]:
                            retrieve.append("*%s = %s;" % (iecvar["NAME"], params[iecvar['LOC'][4]]['name']))
                            init.append("%s = *%s;" % (params[iecvar['LOC'][4]]['name'], iecvar["NAME"]))

                        if iecvar["DIR"] in ["Q", "M"]:
                            publish.append("%s = *%s;" % (params[iecvar['LOC'][4]]['name'], iecvar["NAME"]))
                _globl += ['inwrite|=server_nodes[%d].inwrite;' % (server_node_count - 1)]
                _remove += ['server_nodes[%d].inwrite=0;' % (server_node_count - 1)]
                server_id += 1
            #
            if child.PlugType == "ModbusRTUslave":
                rtuserver_node_count += 1
                server_node_count += 1
                IEC_Channel = child.BaseParams.getIEC_Channel()
                device, baud, parity, databits, stop_bits, slaveid, endian = GetCTVals(child, range(7))
                new_node = GetRTUSlaveNodePrinted(self, child, device, baud, parity, databits, stop_bits, slaveid)
                if new_node is None:
                    return [], "", False, []
                server_node_list.append(new_node)
                #
                inx = 1
                params = {1: {'type': 'uint8_t', 'name': 'server_nodes[%d].slave_id' % (server_node_count - 1)},
                          2: {'type': 'uint32_t',
                              'name': 'server_nodes[%d].node_address.addr.rtu.baud' % (server_node_count - 1)},
                          3: {'type': 'uint8_t',
                              'name': 'server_nodes[%d].node_address.addr.rtu.data_bits' % (
                                      server_node_count - 1)},
                          4: {'type': 'uint8_t',
                              'name': 'server_nodes[%d].node_address.addr.rtu.stop_bits' % (
                                      server_node_count - 1)},
                          5: {'type': 'uint8_t',
                              'name': 'server_nodes[%d].node_address.addr.rtu.parity' % (server_node_count - 1)},
                          6: {'type': 'uint32_t', 'name': 'server_nodes[%d].period' % (server_node_count - 1)},
                          7: {'type': 'int16_t',
                              'name': 'server_nodes[%d].prev_error' % (server_node_count - 1)},
                          8: {'type': 'uint32_t', 'name': 'server_nodes[%d].okcount' % (server_node_count - 1)},
                          9: {'type': 'uint32_t', 'name': 'server_nodes[%d].errcount' % (server_node_count - 1)},
                          10: {'type': 'uint8_t', 'name': 'server_nodes[%d].enable' % (server_node_count - 1)},
                          }
                for subchild in child.IECSortedChildren():
                    new_memarea = GetTCPServerMemAreaPrinted(
                        self, subchild, nodeid)
                    if new_memarea is None:
                        return [], "", False, []
                    server_memarea_list.append(new_memarea)
                    function = subchild.GetParamsAttributes()[0]["children"][0]["value"]
                    # 'ro_bits', 'rw_bits', 'ro_words' or 'rw_words'
                    memarea = modbus_memtype_dict[function][1] + str(IEC_Channel) + str(inx)
                    m = subchild.MemoryArea
                    Nr_of_Channels = int(m.get('Nr_of_Channels', 1))
                    buffer += '\tuint16_t %s[%d];\n' % (memarea, Nr_of_Channels)
                    start_address = int(GetCTVal(subchild, 2))
                    name = subchild.BaseParams.getName()
                    self.checkRanger(name, function[1], start_address, Nr_of_Channels)
                    if modbus_memtype_dict[function][1] == 'ro_bits':
                        server_mem_robits_t += '{%d, %d, %s},\n' % (start_address, Nr_of_Channels, memarea)
                    elif modbus_memtype_dict[function][1] == 'rw_bits':
                        server_mem_rwbits_t += '{%d, %d, %s},\n' % (start_address, Nr_of_Channels, memarea)
                    elif modbus_memtype_dict[function][1] == 'ro_words':
                        server_mem_rowords_t += '{%d, %d, %s},\n' % (start_address, Nr_of_Channels, memarea)
                    elif modbus_memtype_dict[function][1] == 'rw_words':
                        server_mem_words_t += '{%d, %d, %s},\n' % (start_address, Nr_of_Channels, memarea)
                    inx += 1
                    for iecvar in subchild.GetLocations():
                        # print repr(iecvar)
                        absloute_address = iecvar["LOC"][3]
                        relative_addr = absloute_address - start_address
                        # test if relative address in request specified range
                        if relative_addr in range(int(GetCTVal(subchild, 1))) and len(iecvar['LOC']) == 4:
                            if str(iecvar["NAME"]) not in loc_vars_list:
                                method = {'lit-4321': "s4321", 'lar-2143': "s2143", 'lit-3412': "s3412",
                                          "default-1234": "s1234"}
                                if iecvar["DIR"] in ["I", "M"]:
                                    _retrieve.append(
                                        "%s_%s((const char *)&%s[%d],(char *)%s);" % (
                                            method[endian], iecvar['SIZE'], memarea, relative_addr, iecvar["NAME"]))
                                    init.append("%s_%s((const char *)%s,(char *)&%s[%d]);" % (
                                        method[endian], iecvar['SIZE'], iecvar["NAME"], memarea, relative_addr))

                                if iecvar["DIR"] in ["Q", "M"]:
                                    _publish.append("%s_%s((const char *)%s,(char *)&%s[%d]);" % (
                                        method[endian], iecvar['SIZE'], iecvar["NAME"], memarea, relative_addr))
                                loc_vars_list.append(str(iecvar["NAME"]))
                                modbus_memtype_dict[function][2] = modbus_memtype_dict[function][2] + 1
                            else:
                                self.GetCTRoot().logger.write_warning(
                                    _("Waring: Variable Dup {loc} ,{name} \n").format(loc=iecvar["LOC"],
                                                                                      name=str(iecvar["NAME"])))
                        # else:
                        #     self.GetCTRoot().logger.write_error(
                        #         _("Error: Variable Illigl %s ,%s \n") % (iecvar["LOC"], str(iecvar["NAME"])))
                for iecvar in self.GetLocations():
                    absloute_address = iecvar["LOC"][3]
                    relative_addr = absloute_address - start_address
                    # test if relative address in request specified range
                    if iecvar['LOC'][1] == IEC_Channel and len(iecvar['LOC']) == 5 and params.get(iecvar['LOC'][4]):
                        # loc_vars.append("extern %s *%s;" % (IEC_C[iecvar['IEC_TYPE']], str(iecvar["NAME"])))
                        # loc_vars.append(
                        #     "%s *" % params[iecvar['LOC'][4]]['type'] + str(iecvar["NAME"]) + " = &%s;" % (
                        #         params[iecvar['LOC'][4]]['name']))
                        loc_vars_list.append(str(iecvar["NAME"]))
                        if iecvar["DIR"] in ["I", "M"]:
                            retrieve.append("*%s = %s;" % (iecvar["NAME"], params[iecvar['LOC'][4]]['name']))
                            init.append("%s = *%s;" % (params[iecvar['LOC'][4]]['name'], iecvar["NAME"]))

                        if iecvar["DIR"] in ["Q", "M"]:
                            publish.append("%s = *%s;" % (params[iecvar['LOC'][4]]['name'], iecvar["NAME"]))
                _globl += ['inwrite|=server_nodes[%d].inwrite;' % (server_node_count - 1)]
                _remove += ['server_nodes[%d].inwrite=0;' % (server_node_count - 1)]
                server_id += 1
            #
            if child.PlugType == "ModbusTCPclient":
                tcpclient_reqs_count += len(child.IECSortedChildren())
                new_node = GetTCPClientNodePrinted(self, child)
                if new_node is None:
                    return [], "", False
                client_node_list.append(new_node)
                for subchild in child.IECSortedChildren():
                    new_req, buf = GetClientRequestPrinted(
                        self, subchild, client_nodeid)
                    endian = GetCTVal(child, 9)
                    if new_req is None:
                        return [], "", False, []
                    client_request_list.append(new_req)
                    client_request_buffer.append(buf)
                    for iecvar in subchild.GetLocations():
                        # absloute address - start address
                        relative_addr = iecvar["LOC"][3] - int(GetCTVal(subchild, 3))
                        # test if relative address in request specified range
                        if relative_addr in range(int(GetCTVal(subchild, 6))):
                            if str(iecvar["NAME"]) not in loc_vars_list:
                                # loc_vars.append("extern %s *%s;" % (IEC_C[iecvar['IEC_TYPE']], str(iecvar["NAME"])))
                                loc_vars.append(
                                    "uint16_t *" + str(iecvar["NAME"]) + " = &client_requests[%d].plcv_buffer[%d];" % (
                                        client_requestid, relative_addr))
                                loc_vars_list.append(str(iecvar["NAME"]))
                    client_requestid += 1
                tcpclient_node_count += 1
                client_nodeid += 1
            #
            if child.PlugType == "ModbusRTUclient":
                IEC_Channel = child.BaseParams.getIEC_Channel()
                rtuclient_reqs_count += len(child.IECSortedChildren())
                new_node = GetRTUClientNodePrinted(self, child)
                if new_node is None:
                    return [], "", False, []
                client_node_list.append(new_node)
                for subchild in child.IECSortedChildren():
                    new_req, buf = GetClientRequestPrinted(self, subchild, client_nodeid)
                    if new_req is None:
                        return [], "", False, []
                    client_request_list.append(new_req)
                    client_request_buffer.append(buf)
                    endian = GetCTVal(subchild, 10)
                    start_address = int(GetCTVal(subchild, 7))
                    params = {
                        1: {'type': 'uint8_t', 'name': 'client_requests[%d].slave_id' % client_requestid},
                        2: {'type': 'uint32_t',
                            'name': 'client_requests[%d].node_address.addr.rtu.baud' % client_requestid},
                        3: {'type': 'uint8_t',
                            'name': 'client_requests[%d].node_address.addr.rtu.data_bits' % client_requestid},
                        4: {'type': 'uint8_t',
                            'name': 'client_requests[%d].node_address.addr.rtu.stop_bits' % client_requestid},
                        5: {'type': 'uint8_t',
                            'name': 'client_requests[%d].node_address.addr.rtu.parity' % client_requestid},
                        6: {'type': 'uint32_t', 'name': 'client_requests[%d].period' % client_requestid},
                        7: {'type': 'int16_t', 'name': 'client_requests[%d].prev_error' % client_requestid},
                        8: {'type': 'uint32_t', 'name': 'client_requests[%d].okcount' % client_requestid},
                        9: {'type': 'uint32_t', 'name': 'client_requests[%d].errcount' % client_requestid},
                        10: {'type': 'uint8_t', 'name': 'client_requests[%d].enable' % client_requestid},
                    }
                    for iecvar in subchild.GetLocations():
                        # print repr(iecvar)
                        absloute_address = iecvar["LOC"][3]
                        relative_addr = absloute_address - start_address
                        # test if relative address in request specified range
                        if relative_addr in range(int(GetCTVal(subchild, 1))) and len(iecvar['LOC']) == 4:
                            if str(iecvar["NAME"]) not in loc_vars_list:
                                method = {'lit-4321': "s4321", 'lar-2143': "s2143", 'lit-3412': "s3412",
                                          "default-1234": "s1234"}
                                if iecvar["DIR"] in ["I", "M"]:
                                    retrieve.append(
                                        "%s_%s((const char *)&%s[%d],(char *)%s);" % (
                                            method[endian], iecvar['SIZE'], 'plcv_buffer%d_%d_%d' % (
                                                iecvar["LOC"][0], iecvar["LOC"][1], iecvar["LOC"][2]), relative_addr,
                                            iecvar["NAME"]))
                                    init.append("%s_%s((const char *)%s,(char *)&%s[%d]);" % (
                                        method[endian], iecvar['SIZE'], iecvar["NAME"],
                                        'plcv_buffer%d_%d_%d' % (iecvar["LOC"][0], iecvar["LOC"][1], iecvar["LOC"][2]),
                                        relative_addr))

                                if iecvar["DIR"] in ["Q", "M"]:
                                    publish.append("%s_%s((const char *)%s,(char *)&%s[%d]);" % (
                                        method[endian], iecvar['SIZE'], iecvar["NAME"],
                                        'plcv_buffer%d_%d_%d' % (iecvar["LOC"][0], iecvar["LOC"][1], iecvar["LOC"][2]),
                                        relative_addr))
                                loc_vars_list.append(str(iecvar["NAME"]))
                            else:
                                self.GetCTRoot().logger.write_warning(
                                    _("Waring: Variable Dup {loc} ,{name} \n").format(loc=iecvar["LOC"],
                                                                                      name=str(iecvar["NAME"])))
                        if iecvar['LOC'][1] == IEC_Channel and len(iecvar['LOC']) == 5 and params.get(iecvar['LOC'][4]):
                            # loc_vars.append("extern %s *%s;" % (IEC_C[iecvar['IEC_TYPE']], str(iecvar["NAME"])))
                            # loc_vars.append(
                            #     "%s *" % params[iecvar['LOC'][4]]['type'] + str(iecvar["NAME"]) + " = &%s;" % (
                            #         params[iecvar['LOC'][4]]['name']))
                            loc_vars_list.append(str(iecvar["NAME"]))
                            if iecvar["DIR"] in ["I", "M"]:
                                retrieve.append("*%s = %s;" % (iecvar["NAME"], params[iecvar['LOC'][4]]['name']))
                                init.append("%s = *%s;" % (params[iecvar['LOC'][4]]['name'], iecvar["NAME"]))

                            if iecvar["DIR"] in ["Q", "M"]:
                                publish.append("%s = *%s;" % (params[iecvar['LOC'][4]]['name'], iecvar["NAME"]))
                    client_requestid += 1
                rtuclient_node_count += 1
                client_nodeid += 1
            nodeid += 1
        if _publish:
            publish += _globl
            publish.append('if(!inwrite){\n')
            publish += _publish
            publish.append('}\n')
        if _retrieve:
            retrieve += _globl
            retrieve.append('if(inwrite){\n')
            retrieve += _retrieve
            retrieve += _remove
            retrieve.append('}\n')

        loc_dict["loc_vars"] = "\n".join(loc_vars)
        loc_dict["server_nodes_params"] = ",\n\n".join(server_node_list)
        loc_dict["client_nodes_params"] = ",\n\n".join(client_node_list)
        loc_dict["client_request_buffer"] = "\n\n".join(client_request_buffer)
        loc_dict["client_req_params"] = ",\n\n".join(client_request_list)
        loc_dict["tcpclient_reqs_count"] = str(tcpclient_reqs_count)
        loc_dict["tcpclient_node_count"] = str(tcpclient_node_count)
        loc_dict["tcpserver_node_count"] = str(tcpserver_node_count)
        loc_dict["rtuclient_reqs_count"] = str(rtuclient_reqs_count)
        loc_dict["rtuclient_node_count"] = str(rtuclient_node_count)
        loc_dict["rtuserver_node_count"] = str(rtuserver_node_count)
        loc_dict["ascclient_reqs_count"] = str(ascclient_reqs_count)
        loc_dict["ascclient_node_count"] = str(ascclient_node_count)
        loc_dict["ascserver_node_count"] = str(ascserver_node_count)
        loc_dict["total_tcpnode_count"] = str(total_node_count[0])
        loc_dict["total_rtunode_count"] = str(total_node_count[1])
        loc_dict["total_ascnode_count"] = str(total_node_count[2])
        loc_dict["max_remote_tcpclient"] = int(self.GetParamsAttributes()[0]["children"][0]["value"])
        loc_dict["buffer"] = buffer
        loc_dict["server_mem_robits_t"] = server_mem_robits_t
        loc_dict["server_mem_rwbits_t"] = server_mem_rwbits_t
        loc_dict["server_mem_rowords_t"] = server_mem_rowords_t
        loc_dict["server_mem_words_t"] = server_mem_words_t
        loc_dict["init"] = "\n".join(init)
        loc_dict["publish"] = "\n".join(publish)
        loc_dict["retrieve"] = "\n".join(retrieve)

        # get template file content into a string, format it with dict
        # and write it to proper .h file
        mb_main = open(h_filename).read() % loc_dict
        f = open(Gen_MB_h_path, 'w', encoding='utf-8')
        f.write(mb_main)
        f.close()
        # same thing as above, but now to .c file
        mb_main = open(c_filename).read() % loc_dict
        f = open(Gen_MB_c_path, 'w', encoding='utf-8')
        f.write(mb_main)
        f.close()

        LDFLAGS = []
        # LDFLAGS.append(" \"-L" + ModbusPath + "\"")
        # LDFLAGS.append(" \"" + os.path.join(ModbusPath, "libmb.a") + "\"")
        # LDFLAGS.append(" \"-Wl,-rpath," + ModbusPath + "\"")
        # LDFLAGS.append("\"" + os.path.join(ModbusPath, "mb_slave_and_master.o") + "\"")
        # LDFLAGS.append("\"" + os.path.join(ModbusPath, "mb_slave.o") + "\"")
        # LDFLAGS.append("\"" + os.path.join(ModbusPath, "mb_master.o") + "\"")
        # LDFLAGS.append("\"" + os.path.join(ModbusPath, "mb_tcp.o")    + "\"")
        # LDFLAGS.append("\"" + os.path.join(ModbusPath, "mb_rtu.o")    + "\"")
        # LDFLAGS.append("\"" + os.path.join(ModbusPath, "mb_ascii.o")    + "\"")
        # LDFLAGS.append("\"" + os.path.join(ModbusPath, "sin_util.o")  + "\"")
        # Target is ARM with linux and not win on x86 so winsock2 (ws2_32) library is useless !!!
        # if os.name == 'nt':   # other possible values: 'posix' 'os2' 'ce' 'java' 'riscos'
        # LDFLAGS.append(" -lws2_32 ")  # on windows we need to load winsock
        # library!

        return [(Gen_MB_c_path, ' -I"' + ModbusPath + '"')], LDFLAGS, True, ['modbus']
