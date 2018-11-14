#!/usr/bin/env python
# -*- coding: utf-8 -*-

# See COPYING file for copyrights details.

from __future__ import absolute_import

from itertools import repeat, izip_longest
from functools import partial
import wx

from controls.IDManager import IDManager

class SchemeEditor(wx.Panel):
    def __init__(self, scheme, parent, *args, **kwargs):
        self.txtctrls = {} 
        wx.Panel.__init__(self, parent, *args, **kwargs)

        self.fieldsizer = wx.FlexGridSizer(cols=2, hgap=10, vgap=10)

        if self.EnableIDSelector:
            self.model = self.model + [("ID", _("ID:"))]

        for tag, label in self.model:
            txtctrl = wx.TextCtrl(parent=self, size=wx.Size(200, -1))
            self.txtctrls[tag] = txtctrl
            for win, flag in [
                (wx.StaticText(self, label=label), wx.ALIGN_CENTER_VERTICAL),
                (txtctrl, wx.GROW)]:
                self.fieldsizer.AddWindow(win, flag=flag)

        self.fieldsizer.AddSpacer(20)

        if self.EnableIDSelector:
            self.mainsizer = wx.FlexGridSizer(cols=2, hgap=10, vgap=10)
            self.mainsizer.AddSizer(self.fieldsizer)
            self.idselector = IDManager(
                self, parent.ctr,
                partial(wx.CallAfter, parent.SetURI))
            self.mainsizer.AddWindow(self.idselector)
            self.SetSizer(self.mainsizer)
        else:
            self.SetSizer(self.fieldsizer)

    def SetFields(self, fields):
        for tag, label in self.model:
            self.txtctrls[tag].SetValue(fields[tag])

    def GetFields(self):
        return {tag: self.txtctrls[tag].GetValue() for tag,label in self.model}

