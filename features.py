#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz
#
# Copyright (C) 2007: Laurent BESSARD
# Copyright (C) 2007-2018: Edouard TISSERANT
#
# See COPYING file for copyrights details.
from util.TranslationCatalogs import NoTranslate

_ = NoTranslate
libraries = [
    ('Native', 'NativeLib.NativeLibrary', True),
    ('Python', 'py_ext.PythonLibrary', False),
    ('SVGUI', 'svgui.SVGUILibrary', False)]

catalog = [
    ('canfestival', _('CANopen support'), _('Map located variables over CANopen'), 'canfestival.canfestival.RootClass'),
    ('bacnet', _('Bacnet support'), _('Map located variables over Bacnet'), 'bacnet.bacnet.RootClass'),
    ('modbus', _('Modbus support'), _('Map located variables over Modbus'), 'modbus.modbus.RootClass'),
    ('c_ext', _('C extension'), _('Add C code accessing located variables synchronously'), 'c_ext.CFile'),
    ('py_ext', _('Python file'), _('Add Python code executed asynchronously'), 'py_ext.PythonFile'),
    ('wxglade_hmi', _('WxGlade GUI'), _('Add a simple WxGlade based GUI.'), 'wxglade_hmi.WxGladeHMI'),
    ('svgui', _('SVGUI'), _('Experimental web based HMI'), 'svgui.SVGUI')]

file_editors = []
