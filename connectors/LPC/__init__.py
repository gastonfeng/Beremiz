#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#Copyright (C) 2007: Edouard TISSERANT and Laurent BESSARD
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

def LPC_connector_factory(uri, confnodesroot):
    """
    This returns the connector to LPC style PLCobject
    """
    servicetype, location = uri.split("://")
    mode,comportstr = location.split('/')
    if mode=="APPLICATION":
        from LPCAppObject import LPCAppObject 
        return LPCAppObject(confnodesroot,comportstr)
    elif mode=="BOOTLOADER":
        from LPCBootObject import LPCBootObject 
        return LPCBootObject(confnodesroot,comportstr)


