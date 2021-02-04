#!/usr/bin/env python
# -*- coding: utf-8 -*-

# See COPYING file for copyrights details.

# from __future__ import absolute_import

from itertools import repeat, islice, chain

import wx
from serial.tools import list_ports

from connectors.SchemeEditor import SchemeEditor

Schemes = ["SERIAL", ]

model = []


class SERIAL_dialog(SchemeEditor):
    def __init__(self, *args, **kwargs):
        self.model = model
        self.EnableIDSelector = False
        SchemeEditor.__init__(self, *args, **kwargs)
        self.choices = [d.device for d in list_ports.comports()]
        self.UriTypeChoice = wx.Choice(parent=self, choices=self.choices)
        self.UriTypeChoice.SetSelection(0)
        # self.Bind(wx.EVT_CHOICE, self.OnTypeChoice, self.UriTypeChoice)
        self.fieldsizer.Add(self.UriTypeChoice)

    # pylint: disable=unused-variable
    def SetLoc(self, loc):
        hostportpath, realm, ID = list(islice(chain(loc.split("#"), repeat("")), 3))
        hostport, path = list(islice(chain(hostportpath.split("/"), repeat("")), 2))
        host, port = list(islice(chain(hostport.split(":"), repeat("")), 2))
        self.SetFields(locals())

    def GetLoc(self):
        fields = self.UriTypeChoice.GetStringSelection()
        return fields

    def close(self):
        pass
