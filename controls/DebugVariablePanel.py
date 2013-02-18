#!/usr/bin/env python
# -*- coding: utf-8 -*-

#This file is part of PLCOpenEditor, a library implementing an IEC 61131-3 editor
#based on the plcopen standard. 
#
#Copyright (C) 2012: Edouard TISSERANT and Laurent BESSARD
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

from types import TupleType, ListType, FloatType
from time import time as gettime
import math
import numpy
import binascii

import wx
import wx.lib.buttons

try:
    import matplotlib
    matplotlib.use('WX')
    import matplotlib.pyplot
    from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
    from matplotlib.backends.backend_wxagg import _convert_agg_to_wx_bitmap
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from mpl_toolkits.mplot3d import Axes3D
    color_cycle = ['r', 'b', 'g', 'm', 'y', 'k']
    cursor_color = '#800080'
    USE_MPL = True
except:
    USE_MPL = False

from graphics import DebugDataConsumer, DebugViewer, REFRESH_PERIOD
from controls import CustomGrid, CustomTable
from dialogs.ForceVariableDialog import ForceVariableDialog
from util.BitmapLibrary import GetBitmap

def AppendMenu(parent, help, id, kind, text):
    parent.Append(help=help, id=id, kind=kind, text=text)

def GetDebugVariablesTableColnames():
    _ = lambda x : x
    return [_("Variable"), _("Value")]

CRC_SIZE = 8
CRC_MASK = 2 ** CRC_SIZE - 1

class VariableTableItem(DebugDataConsumer):
    
    def __init__(self, parent, variable):
        DebugDataConsumer.__init__(self)
        self.Parent = parent
        self.Variable = variable
        self.RefreshVariableType()
        self.Value = ""
        
    def __del__(self):
        self.Parent = None
    
    def SetVariable(self, variable):
        if self.Parent and self.Variable != variable:
            self.Variable = variable
            self.RefreshVariableType()
            self.Parent.RefreshView()
    
    def GetVariable(self, mask=None):
        variable = self.Variable
        if mask is not None:
            parts = variable.split('.')
            mask = mask + ['*'] * max(0, len(parts) - len(mask))
            last = None
            variable = ""
            for m, v in zip(mask, parts):
                if m == '*':
                    if last == '*':
                        variable += '.'
                    variable += v
                elif last is None or last == '*':
                    variable += '..'
                last = m
        return variable
    
    def RefreshVariableType(self):
        self.VariableType = self.Parent.GetDataType(self.Variable)
        if USE_MPL:
            self.ResetData()
    
    def GetVariableType(self):
        return self.VariableType
    
    def GetData(self, start_tick=None, end_tick=None):
        if USE_MPL and self.IsNumVariable():
            if len(self.Data) == 0:
                return self.Data
            
            start_idx = end_idx = None
            if start_tick is not None:
                start_idx = self.GetNearestData(start_tick, -1)
            if end_tick is not None:
                end_idx = self.GetNearestData(end_tick, 1)
            if start_idx is None:
                start_idx = 0
            if end_idx is not None:
                return self.Data[start_idx:end_idx + 1]
            else:
                return self.Data[start_idx:]
            
        return None
    
    def GetRawValue(self, idx):
        if self.VariableType in ["STRING", "WSTRING"] and idx < len(self.RawData):
            return self.RawData[idx][0]
        return ""
    
    def GetRange(self):
        return self.MinValue, self.MaxValue
    
    def ResetData(self):
        if self.IsNumVariable():
            self.Data = numpy.array([]).reshape(0, 3)
            if self.VariableType in ["STRING", "WSTRING"]:
                self.RawData = []
            self.MinValue = None
            self.MaxValue = None
        else:
            self.Data = None
    
    def IsNumVariable(self):
        return (self.Parent.IsNumType(self.VariableType) or 
                self.VariableType in ["STRING", "WSTRING"])
    
    def NewValue(self, tick, value, forced=False):
        if USE_MPL and self.IsNumVariable():
            if self.VariableType in ["STRING", "WSTRING"]:
                num_value = binascii.crc32(value) & CRC_MASK
            else:
                num_value = float(value)
            if self.MinValue is None:
                self.MinValue = num_value
            else:
                self.MinValue = min(self.MinValue, num_value)
            if self.MaxValue is None:
                self.MaxValue = num_value
            else:
                self.MaxValue = max(self.MaxValue, num_value)
            forced_value = float(forced)
            if self.VariableType in ["STRING", "WSTRING"]:
                raw_data = (value, forced_value)
                if len(self.RawData) == 0 or self.RawData[-1] != raw_data:
                    extra_value = len(self.RawData)
                    self.RawData.append(raw_data)
                else:
                    extra_value = len(self.RawData) - 1
            else:
                extra_value = forced_value
            self.Data = numpy.append(self.Data, [[float(tick), num_value, extra_value]], axis=0)
            self.Parent.HasNewData = True
        DebugDataConsumer.NewValue(self, tick, value, forced)
    
    def SetForced(self, forced):
        if self.Forced != forced:
            self.Forced = forced
            self.Parent.HasNewData = True
    
    def SetValue(self, value):
        if (self.VariableType == "STRING" and value.startswith("'") and value.endswith("'") or
            self.VariableType == "WSTRING" and value.startswith('"') and value.endswith('"')):
            value = value[1:-1]
        if self.Value != value:
            self.Value = value
            self.Parent.HasNewData = True
            
    def GetValue(self, tick=None, raw=False):
        if tick is not None and self.IsNumVariable():
            if len(self.Data) > 0:
                idx = numpy.argmin(abs(self.Data[:, 0] - tick))
                if self.VariableType in ["STRING", "WSTRING"]:
                    value, forced = self.RawData[int(self.Data[idx, 2])]
                    if not raw:
                        if self.VariableType == "STRING":
                            value = "'%s'" % value
                        else:
                            value = '"%s"' % value
                    return value, forced
                else:
                    value = self.Data[idx, 1]
                    if not raw and isinstance(value, FloatType):
                        value = "%.6g" % value
                    return value, self.Data[idx, 2]
            return self.Value, self.IsForced()
        elif not raw:
            if self.VariableType == "STRING":
                return "'%s'" % self.Value
            elif self.VariableType == "WSTRING":
                return '"%s"' % self.Value
            elif isinstance(self.Value, FloatType):
                return "%.6g" % self.Value
        return self.Value

    def GetNearestData(self, tick, adjust):
        if USE_MPL and self.IsNumVariable():
            ticks = self.Data[:, 0]
            new_cursor = numpy.argmin(abs(ticks - tick))
            if adjust == -1 and ticks[new_cursor] > tick and new_cursor > 0:
                new_cursor -= 1
            elif adjust == 1 and ticks[new_cursor] < tick and new_cursor < len(ticks):
                new_cursor += 1
            return new_cursor
        return None

class DebugVariableTable(CustomTable):
    
    def GetValue(self, row, col):
        if row < self.GetNumberRows():
            return self.GetValueByName(row, self.GetColLabelValue(col, False))
        return ""
    
    def SetValue(self, row, col, value):
        if col < len(self.colnames):
            self.SetValueByName(row, self.GetColLabelValue(col, False), value)
            
    def GetValueByName(self, row, colname):
        if row < self.GetNumberRows():
            if colname == "Variable":
                return self.data[row].GetVariable()
            elif colname == "Value":
                return self.data[row].GetValue()
        return ""

    def SetValueByName(self, row, colname, value):
        if row < self.GetNumberRows():
            if colname == "Variable":
                self.data[row].SetVariable(value)
            elif colname == "Value":
                self.data[row].SetValue(value)
    
    def IsForced(self, row):
        if row < self.GetNumberRows():
            return self.data[row].IsForced()
        return False
    
    def IsNumVariable(self, row):
        if row < self.GetNumberRows():
            return self.data[row].IsNumVariable()
        return False
    
    def _updateColAttrs(self, grid):
        """
        wx.grid.Grid -> update the column attributes to add the
        appropriate renderer given the column name.

        Otherwise default to the default renderer.
        """
        
        for row in range(self.GetNumberRows()):
            for col in range(self.GetNumberCols()):
                colname = self.GetColLabelValue(col, False)
                if colname == "Value":
                    if self.IsForced(row):
                        grid.SetCellTextColour(row, col, wx.BLUE)
                    else:
                        grid.SetCellTextColour(row, col, wx.BLACK)
                grid.SetReadOnly(row, col, True)
            self.ResizeRow(grid, row)
                
    def AppendItem(self, data):
        self.data.append(data)
    
    def InsertItem(self, idx, data):
        self.data.insert(idx, data)
    
    def RemoveItem(self, idx):
        self.data.pop(idx)
    
    def MoveItem(self, idx, new_idx):
        self.data.insert(new_idx, self.data.pop(idx))
        
    def GetItem(self, idx):
        return self.data[idx]

class DebugVariableDropTarget(wx.TextDropTarget):
    
    def __init__(self, parent, control=None):
        wx.TextDropTarget.__init__(self)
        self.ParentWindow = parent
        self.ParentControl = control
    
    def __del__(self):
        self.ParentWindow = None
        self.ParentControl = None
    
    def OnDragOver(self, x, y, d):
        if self.ParentControl is not None:
            self.ParentControl.OnCanvasDragging(x, y)
        return wx.TextDropTarget.OnDragOver(self, x, y, d)
        
    def OnDropText(self, x, y, data):
        message = None
        try:
            values = eval(data)
        except:
            message = _("Invalid value \"%s\" for debug variable")%data
            values = None
        if not isinstance(values, TupleType):
            message = _("Invalid value \"%s\" for debug variable")%data
            values = None
        
        if message is not None:
            wx.CallAfter(self.ShowMessage, message)
        elif values is not None and values[1] == "debug":
            if isinstance(self.ParentControl, CustomGrid):
                x, y = self.ParentControl.CalcUnscrolledPosition(x, y)
                row = self.ParentControl.YToRow(y - self.ParentControl.GetColLabelSize())
                if row == wx.NOT_FOUND:
                    row = self.ParentWindow.Table.GetNumberRows()
                self.ParentWindow.InsertValue(values[0], row, force=True)
            elif self.ParentControl is not None:
                width, height = self.ParentControl.Canvas.GetSize()
                target_idx = self.ParentControl.GetIndex()
                merge_type = GRAPH_PARALLEL
                if self.ParentControl.Is3DCanvas():
                    if y > height / 2:
                        target_idx += 1
                    self.ParentWindow.InsertValue(values[0], target_idx, force=True)
                else:
                    rect = self.ParentControl.GetAxesBoundingBox()
                    if rect.InsideXY(x, y):
                        merge_rect = wx.Rect(rect.x, rect.y, rect.width / 2., rect.height)
                        if merge_rect.InsideXY(x, y):
                            merge_type = GRAPH_ORTHOGONAL
                        wx.CallAfter(self.ParentWindow.MergeGraphs, values[0], target_idx, merge_type, force=True)
                    else:
                        if y > height / 2:
                            target_idx += 1
                        self.ParentWindow.InsertValue(values[0], target_idx, force=True)
            self.ParentWindow.InsertValue(values[0], force=True)
    
    def OnLeave(self):
        if self.ParentControl is not None:
            self.ParentControl.OnCanvasLeave()
        return wx.TextDropTarget.OnLeave(self)
        
    def ShowMessage(self, message):
        dialog = wx.MessageDialog(self.ParentWindow, message, _("Error"), wx.OK|wx.ICON_ERROR)
        dialog.ShowModal()
        dialog.Destroy()

if USE_MPL:
    MILLISECOND = 1000000
    SECOND = 1000 * MILLISECOND
    MINUTE = 60 * SECOND
    HOUR = 60 * MINUTE
    DAY = 24 * HOUR
    
    ZOOM_VALUES = map(lambda x:("x %.1f" % x, x), [math.sqrt(2) ** i for i in xrange(8)])
    RANGE_VALUES = map(lambda x: (str(x), x), [25 * 2 ** i for i in xrange(6)])
    TIME_RANGE_VALUES = [("%ds" % i, i * SECOND) for i in (1, 2, 5, 10, 20, 30)] + \
                        [("%dm" % i, i * MINUTE) for i in (1, 2, 5, 10, 20, 30)] + \
                        [("%dh" % i, i * HOUR) for i in (1, 2, 3, 6, 12, 24)]
    
    GRAPH_PARALLEL, GRAPH_ORTHOGONAL = range(2)
    
    SCROLLBAR_UNIT = 10
    
    def NextTick(variables):
        next_tick = None
        for item, data in variables:
            if len(data) > 0:
                if next_tick is None:
                    next_tick = data[0][0]
                else:
                    next_tick = min(next_tick, data[0][0])
        return next_tick
    
    def OrthogonalData(item, start_tick, end_tick):
        data = item.GetData(start_tick, end_tick)
        min_value, max_value = item.GetRange()
        if min_value is not None and max_value is not None:
            center = (min_value + max_value) / 2.
            range = max(1.0, max_value - min_value)
        else:
            center = 0.5
            range = 1.0
        return data, center - range * 0.55, center + range * 0.55
    
    class DebugVariableViewer(wx.Panel):
        
        def AddViewer(self):
            pass
        
        def AddButtons(self):
            pass
        
        def __init__(self, parent, window, items=[]):
            wx.Panel.__init__(self, parent)
            self.SetBackgroundColour(wx.WHITE)
            self.SetDropTarget(DebugVariableDropTarget(window, self))
            
            self.ParentWindow = window
            self.Items = items
            
        def __del__(self):
            self.ParentWindow = None
            
        def GetIndex(self):
            return self.ParentWindow.GetViewerIndex(self)
        
        def GetItem(self, variable):
            for item in self.Items:
                if item.GetVariable() == variable:
                    return item
            return None
        
        def GetItems(self):
            return self.Items
        
        def GetVariables(self):
            if len(self.Items) > 1:
                variables = [item.GetVariable() for item in self.Items]
                if self.GraphType == GRAPH_ORTHOGONAL:
                    return tuple(variables)
                return variables
            return self.Items[0].GetVariable()
        
        def AddItem(self, item):
            self.Items.append(item)
            
        def RemoveItem(self, item):
            if item in self.Items:
                self.Items.remove(item)
            
        def Clear(self):
            for item in self.Items:
                self.ParentWindow.RemoveDataConsumer(item)
            self.Items = []
            
        def IsEmpty(self):
            return len(self.Items) == 0
        
        def UnregisterObsoleteData(self):
            for item in self.Items[:]:
                iec_path = item.GetVariable().upper()
                if self.ParentWindow.GetDataType(iec_path) is None:
                    self.ParentWindow.RemoveDataConsumer(item)
                    self.RemoveItem(item)
                else:
                    self.ParentWindow.AddDataConsumer(iec_path, item)
                    item.RefreshVariableType()
            
        def ResetData(self):
            for item in self.Items:
                item.ResetData()
        
        def Refresh(self):
            pass
    
        def OnForceButton(self, event):
            if len(self.Items) == 1:
                wx.CallAfter(self.ForceValue, self.Items[0])
            else:
                menu = wx.Menu(title='')
                for item in self.Items:
                    new_id = wx.NewId()
                    AppendMenu(menu, help='', id=new_id, kind=wx.ITEM_NORMAL, 
                        text=item.GetVariable(self.ParentWindow.GetVariableNameMask()))
                    self.Bind(wx.EVT_MENU, 
                        self.GetForceVariableMenuFunction(item),
                        id=new_id)
                self.PopupMenu(menu)
            event.Skip()
        
        def OnReleaseButton(self, event):
            if len(self.Items) == 1:
                wx.CallAfter(self.ReleaseValue, self.Items[0])
            else:
                menu = wx.Menu(title='')
                for item in self.Items:
                    new_id = wx.NewId()
                    AppendMenu(menu, help='', id=new_id, kind=wx.ITEM_NORMAL, 
                        text=item.GetVariable(self.ParentWindow.GetVariableNameMask()))
                    self.Bind(wx.EVT_MENU, 
                        self.GetReleaseVariableMenuFunction(item),
                        id=new_id)
                
                self.PopupMenu(menu)
            event.Skip()
        
        def OnDeleteButton(self, event):
            if len(self.Items) == 1:
                wx.CallAfter(self.ParentWindow.DeleteValue, self, self.Items[0])
            else:
                menu = wx.Menu(title='')
                for item in self.Items:
                    new_id = wx.NewId()
                    AppendMenu(menu, help='', id=new_id, kind=wx.ITEM_NORMAL, 
                        text=item.GetVariable(self.ParentWindow.GetVariableNameMask()))
                    self.Bind(wx.EVT_MENU, 
                        self.GetDeleteValueMenuFunction(item),
                        id=new_id)
                
                new_id = wx.NewId()
                AppendMenu(menu, help='', id=new_id, kind=wx.ITEM_NORMAL, text=_("All"))
                self.Bind(wx.EVT_MENU, self.OnDeleteAllValuesMenu, id=new_id)
                
                self.PopupMenu(menu)
            event.Skip()
    
        def GetForceVariableMenuFunction(self, item):
            def ForceVariableFunction(event):
                self.ForceValue(item)
            return ForceVariableFunction
        
        def GetReleaseVariableMenuFunction(self, item):
            def ReleaseVariableFunction(event):
                self.ReleaseValue(item)
            return ReleaseVariableFunction
        
        def GetDeleteValueMenuFunction(self, item):
            def DeleteValueFunction(event):
                self.ParentWindow.DeleteValue(self, item)
            return DeleteValueFunction
        
        def ForceValue(self, item):
            iec_path = item.GetVariable().upper()
            iec_type = self.ParentWindow.GetDataType(iec_path)
            if iec_type is not None:
                dialog = ForceVariableDialog(self, iec_type, str(item.GetValue()))
                if dialog.ShowModal() == wx.ID_OK:
                    self.ParentWindow.ForceDataValue(iec_path, dialog.GetValue())
        
        def ReleaseValue(self, item):
            iec_path = item.GetVariable().upper()
            self.ParentWindow.ReleaseDataValue(iec_path)
        
        def OnDeleteAllValuesMenu(self, event):
            wx.CallAfter(self.ParentWindow.DeleteValue, self)
        
    class DebugVariableText(DebugVariableViewer):
        
        def __init__(self, parent, window, items=[]):
            DebugVariableViewer.__init__(self, parent, window, items)
        
            main_sizer = wx.FlexGridSizer(cols=2, hgap=0, rows=1, vgap=0)
            main_sizer.AddGrowableCol(0)
            
            viewer_sizer = wx.FlexGridSizer(cols=2, hgap=0, rows=1, vgap=0)
            viewer_sizer.AddGrowableCol(0)
            main_sizer.AddSizer(viewer_sizer, border=5, 
                flag=wx.ALL|wx.GROW|wx.ALIGN_CENTER_VERTICAL)
            
            variable_name_label = wx.TextCtrl(self, size=wx.Size(0, -1),
                value=self.Items[0].GetVariable(), style=wx.TE_READONLY|wx.TE_RIGHT|wx.NO_BORDER)
            variable_name_label.SetSelection(variable_name_label.GetLastPosition(), -1)
            viewer_sizer.AddWindow(variable_name_label, flag=wx.GROW)
            
            self.ValueLabel = wx.TextCtrl(self,
                size=wx.Size(100, -1), style=wx.TE_READONLY|wx.TE_RIGHT|wx.NO_BORDER)
            viewer_sizer.AddWindow(self.ValueLabel, 
                border=5, flag=wx.LEFT)
            
            button_sizer = wx.BoxSizer(wx.HORIZONTAL)
            self.MainSizer.AddSizer(button_sizer, border=5, 
                flag=wx.TOP|wx.BOTTOM|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL)
            
            buttons = [
                ("ForceButton", "force", _("Force value")),
                ("ReleaseButton", "release", _("Release value")),
                ("DeleteButton", "delete_graph", _("Remove debug variable"))]
            
            for name, bitmap, help in buttons:
                button = wx.lib.buttons.GenBitmapButton(self, bitmap=GetBitmap(bitmap), 
                      size=wx.Size(20, 20), style=wx.NO_BORDER)
                button.SetToolTipString(help)
                setattr(self, name, button)
                self.Bind(wx.EVT_BUTTON, getattr(self, "On" + name), button)
                button_sizer.AddWindow(button, border=5, flag=wx.LEFT)
            
            self.SetSizer(main_sizer)
    
        def Refresh(self):
            self.ValueLabel.ChangeValue(self.Items[0].GetValue())
            if self.Items[0].IsForced():
                self.ValueLabel.SetForegroundColour(wx.BLUE)
            else:
                self.ValueLabel.SetForegroundColour(wx.BLACK)
            self.ValueLabel.SetSelection(self.ValueLabel.GetLastPosition(), -1)
    
    def compute_mask(x, y):
        mask = []
        for xp, yp in zip(x, y):
            if xp == yp:
                mask.append(xp)
            else:
                mask.append("*")
        return mask
    
    #CANVAS_HIGHLIGHT_TYPES
    [HIGHLIGHT_NONE,
     HIGHLIGHT_BEFORE,
     HIGHLIGHT_AFTER,
     HIGHLIGHT_LEFT,
     HIGHLIGHT_RIGHT] = range(5)
    
    HIGHLIGHT_PEN = wx.Pen(wx.Colour(0, 128, 255))
    HIGHLIGHT_BRUSH = wx.Brush(wx.Colour(0, 128, 255, 128))
    
    #CANVAS_SIZE_TYPES
    [SIZE_MINI, SIZE_MIDDLE, SIZE_MAXI] = range(3)
    
    class GraphButton():
        
        def __init__(self, x, y, bitmap, callback):
            self.Position = wx.Point(x, y)
            self.Bitmap = bitmap
            self.Shown = True
            self.Callback = callback
        
        def __del__(self):
            self.callback = None
        
        def GetSize(self):
            return self.Bitmap.GetSize()
        
        def SetPosition(self, x, y):
            self.Position = wx.Point(x, y)
        
        def SetBitmap(self, bitmap):
            self.Bitmap = bitmap
            
        def SetCallback(self, callback):
            self.Callback = callback
        
        def Show(self):
            self.Shown = True
            
        def Hide(self):
            self.Shown = False
        
        def HitTest(self, x, y):
            if self.Shown:
                w, h = self.Bitmap.GetSize()
                rect = wx.Rect(self.Position.x, self.Position.y, w, h)
                if rect.InsideXY(x, y):
                    return True
            return False
        
        def ProcessCallback(self):
            if self.Callback is not None:
                wx.CallAfter(self.Callback)
                
        def Draw(self, dc):
            if self.Shown:
                dc.DrawBitmap(self.Bitmap, self.Position.x, self.Position.y, True)
    
    class DraggingFigureCanvas(FigureCanvas):
        
        def __init__(self, parent, window, *args, **kwargs):
            FigureCanvas.__init__(self, parent, *args, **kwargs)
            self.SetBackgroundColour(wx.WHITE)
            self.Bind(wx.EVT_ENTER_WINDOW, self.OnEnterWindow)
            self.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeaveWindow)
            self.Bind(wx.EVT_SIZE, self.OnResizeWindow)
            
            self.ParentWindow = window
            self.Highlight = HIGHLIGHT_NONE
            self.CanvasSize = SIZE_MAXI
            
            self.Buttons = []
            self.ContextualButtons = []
            self.ContextualButtonsItem = None
            
            self.Buttons.append(
                GraphButton(0, 0, GetBitmap("minimize_graph"), self.OnChangeSizeButton))
            self.Buttons.append(
                GraphButton(0, 0, GetBitmap("delete_graph"), self.OnCloseButton))
            
            self.ShowButtons(False)
            
        def SetHighlight(self, highlight):
            if self.Highlight != highlight:
                self.Highlight = highlight
                return True
            return False
        
        def GetAxesBoundingBox(self):
            width, height = self.GetSize()
            ax, ay, aw, ah = self.figure.gca().get_position().bounds
            return wx.Rect(ax * width, height - (ay + ah) * height - 1,
                           aw * width + 2, ah * height + 1)
        
        def draw(self, drawDC=None):
            FigureCanvasAgg.draw(self)
    
            self.bitmap = _convert_agg_to_wx_bitmap(self.get_renderer(), None)
            self.bitmap.UseAlpha() 
            width, height = self.GetSize()
            bbox = self.GetAxesBoundingBox()
            
            destDC = wx.MemoryDC()
            destDC.SelectObject(self.bitmap)
            
            destGC = wx.GCDC(destDC)
            
            destGC.BeginDrawing()
            destGC.SetPen(HIGHLIGHT_PEN)
            destGC.SetBrush(HIGHLIGHT_BRUSH)
            if self.Highlight == HIGHLIGHT_BEFORE:
                destGC.DrawLine(0, 0, width - 1, 0)
            elif self.Highlight == HIGHLIGHT_AFTER:
                destGC.DrawLine(0, height - 1, width - 1, height - 1)
            elif self.Highlight == HIGHLIGHT_LEFT:
                destGC.DrawRectangle(bbox.x, bbox.y, 
                                     bbox.width / 2, bbox.height)
            elif self.Highlight == HIGHLIGHT_RIGHT:
                destGC.DrawRectangle(bbox.x + bbox.width / 2, bbox.y, 
                                     bbox.width / 2, bbox.height)
            
            for button in self.Buttons + self.ContextualButtons:
                button.Draw(destGC)
            
            if self.ParentWindow.IsDragging():
                destBBox = self.ParentWindow.GetDraggingAxesClippingRegion(self.Parent)
                if destBBox.width > 0 and destBBox.height > 0:
                    srcPanel = self.ParentWindow.DraggingAxesPanel
                    srcBBox = srcPanel.GetAxesBoundingBox()
                    
                    if destBBox.x == 0:
                        srcX = srcBBox.x + srcBBox.width - destBBox.width
                    else:
                        srcX = srcBBox.x
                    if destBBox.y == 0:
                        srcY = srcBBox.y + srcBBox.height - destBBox.height
                    else:
                        srcY = srcBBox.y
                    
                    srcBmp = _convert_agg_to_wx_bitmap(srcPanel.Canvas.get_renderer(), None)
                    srcDC = wx.MemoryDC()
                    srcDC.SelectObject(srcBmp)
                    
                    destGC.Blit(destBBox.x, destBBox.y, 
                                int(destBBox.width), int(destBBox.height), 
                                srcDC, srcX, srcY)
                    
            destGC.EndDrawing()
            
            self._isDrawn = True
            self.gui_repaint(drawDC=drawDC)
        
        def HandleButtons(self, x, y):
            for button in self.Buttons + self.ContextualButtons:
                if button.HitTest(x, y):
                    button.ProcessCallback()
                    return True
            return False
        
        def PopupContextualButtons(self, item, rect, style=wx.HORIZONTAL):
            if self.ContextualButtonsItem is not None and item != self.ContextualButtonsItem:
                self.DismissContextualButtons()
            
            if self.ContextualButtonsItem is None:
                self.ContextualButtonsItem = item
                
                if self.ContextualButtonsItem.IsForced():
                    self.ContextualButtons.append(
                        GraphButton(0, 0, GetBitmap("release"), self.OnReleaseButton))
                else:
                    self.ContextualButtons.append(
                        GraphButton(0, 0, GetBitmap("force"), self.OnForceButton))
                self.ContextualButtons.append(
                    GraphButton(0, 0, GetBitmap("delete_graph"), self.OnRemoveItemButton))
                
                offset = 0
                buttons = self.ContextualButtons[:]
                if style == wx.VERTICAL:
                     buttons.reverse()
                for button in buttons:
                    w, h = button.GetSize()
                    if style == wx.HORIZONTAL:
                        x = rect.x + rect.width + offset
                        y = rect.y + (rect.height - h) / 2
                        offset += w
                    else:
                        x = rect.x + (rect.width - w ) / 2
                        y = rect.y - h - offset
                        offset += h
                    button.SetPosition(x, y)
            self.ParentWindow.ForceRefresh()
        
        def DismissContextualButtons(self):
            if self.ContextualButtonsItem is not None:
                self.ContextualButtonsItem = None
                self.ContextualButtons = []
            self.ParentWindow.ForceRefresh()
        
        def IsOverButton(self, x, y):
            for button in self.Buttons + self.ContextualButtons:
                if button.HitTest(x, y):
                    return True
            return False
        
        def IsOverContextualButton(self, x, y):
            for button in self.ContextualButtons:
                if button.HitTest(x, y):
                    return True
            return False
        
        def ShowButtons(self, show):
            for button in self.Buttons:
                if show:
                    button.Show()
                else:
                    button.Hide()
            self.ParentWindow.ForceRefresh()
        
        def OnEnterWindow(self, event):
            self.ShowButtons(True)
            event.Skip()
            
        def OnLeaveWindow(self, event):
            x, y = event.GetPosition()
            width, height = self.GetSize()
            if (x <= 0 or x >= width - 1 or
                y <= 0 or y >= height - 1):
                self.ShowButtons(False)
            event.Skip()
        
        def OnChangeSizeButton(self):
            if self.CanvasSize == SIZE_MAXI:
                self.CanvasSize = SIZE_MIDDLE
                self.Parent.Minimize()
            else:
                self.CanvasSize = SIZE_MAXI
                self.Parent.Maximize()
        
        def OnCloseButton(self):
            self.ParentWindow.DeleteValue(self.Parent)
        
        def OnForceButton(self):
            wx.CallAfter(self.Parent.ForceValue, 
                         self.ContextualButtonsItem)
            self.DismissContextualButtons()
            
        def OnReleaseButton(self):
            wx.CallAfter(self.Parent.ReleaseValue, 
                         self.ContextualButtonsItem)
            self.DismissContextualButtons()
            
        def OnRemoveItemButton(self):            
            wx.CallAfter(self.ParentWindow.DeleteValue, self.Parent, 
                         self.ContextualButtonsItem)
            self.DismissContextualButtons()
            
        def OnResizeWindow(self, event):
            width, height = self.GetSize()
            offset = 0
            buttons = self.Buttons[:]
            buttons.reverse()
            for button in buttons:
                w, h = button.GetSize()
                button.SetPosition(width - 5 - w - offset, 5)
                offset += w
            event.Skip()
    
    class DebugVariableGraphic(DebugVariableViewer):
        
        def __init__(self, parent, window, items, graph_type):
            DebugVariableViewer.__init__(self, parent, window, items)
        
            self.GraphType = graph_type
            self.CursorTick = None
            self.MouseStartPos = None
            self.StartCursorTick = None
            self.ItemButtons = None
            
            main_sizer = wx.BoxSizer(wx.VERTICAL)
            
            self.Figure = matplotlib.figure.Figure(facecolor='w')
            self.Figure.subplotpars.update(top=0.95, left=0.1, bottom=0.1, right=0.95)
            
            self.Canvas = DraggingFigureCanvas(self, self.ParentWindow, -1, self.Figure)
            self.Canvas.SetMinSize(wx.Size(200, 200))
            self.Canvas.SetDropTarget(DebugVariableDropTarget(self.ParentWindow, self))
            self.Canvas.Bind(wx.EVT_MOUSEWHEEL, self.OnCanvasMouseWheel)
            self.Canvas.mpl_connect('button_press_event', self.OnCanvasButtonPressed)
            self.Canvas.mpl_connect('motion_notify_event', self.OnCanvasMotion)
            self.Canvas.mpl_connect('button_release_event', self.OnCanvasButtonReleased)
            self.Canvas.mpl_connect('scroll_event', self.OnCanvasScroll)
            
            main_sizer.AddWindow(self.Canvas, 1, flag=wx.GROW)
            self.SetSizer(main_sizer)
            
            self.ResetGraphics()
        
        def RefreshLabelsPosition(self, ratio):
            self.MaskLabel.set_position((0.05, 1.0 - 0.1 * ratio))
            if self.GraphType == GRAPH_PARALLEL or self.Is3DCanvas():
                num_item = len(self.Items)
                for idx in xrange(num_item):
                    if not self.Is3DCanvas():
                        self.AxesLabels[idx].set_position((0.05, 1.0 - (0.1 + 0.075 * (idx + 1)) * ratio))
                    self.Labels[idx].set_position((0.95, 0.1 + (num_item - idx - 1) * 0.1 * ratio))
            else:
                self.AxesLabels[0].set_position((0.1, 0.05 * ratio))
                self.Labels[0].set_position((0.95, 0.05 * ratio))
                self.AxesLabels[1].set_position((0.05, 0.1 * ratio))
                self.Labels[1].set_position((0.05, 1.0 - 0.05 * ratio))
        
        def Minimize(self):
            self.Canvas.SetMinSize(wx.Size(200, 100))
            self.Figure.subplotpars.update(top=0.9, bottom=0.2)
            self.RefreshLabelsPosition(2)
            self.Figure.subplots_adjust()
            self.ParentWindow.RefreshGraphicsSizer()
            
        def Maximize(self):
            self.Canvas.SetMinSize(wx.Size(200, 200))
            self.Figure.subplotpars.update(top=0.95, bottom=0.1)
            self.RefreshLabelsPosition(1)
            self.Figure.subplots_adjust()
            self.ParentWindow.RefreshGraphicsSizer()
            
        def GetAxesBoundingBox(self, absolute=False):
            bbox = self.Canvas.GetAxesBoundingBox()
            if absolute:
                xw, yw = self.GetPosition()
                bbox.x += xw
                bbox.y += yw
            return bbox
        
        def OnCanvasButtonPressed(self, event):
            width, height = self.Canvas.GetSize()
            x, y = event.x, height - event.y
            if not self.Canvas.IsOverButton(x, y) and not self.Is3DCanvas():
                rect = self.GetAxesBoundingBox()
                if rect.InsideXY(x, y):
                    self.MouseStartPos = wx.Point(x, y)
                item_idx = None
                for i, t in enumerate(self.AxesLabels):
                    (x0, y0), (x1, y1) = t.get_window_extent().get_points()
                    rect = wx.Rect(x0, height - y1, x1 - x0, y1 - y0)
                    if rect.InsideXY(x, y):
                        item_idx = i
                        break
                if item_idx is not None:
                    self.Canvas.ShowButtons(False)
                    self.Canvas.DismissContextualButtons()
                    xw, yw = self.GetPosition()
                    self.ParentWindow.StartDragNDrop(self, 
                        self.Items[item_idx], x + xw, y + yw, x + xw, y + yw)
                elif event.button == 1 and event.inaxes == self.Axes:
                    self.HandleCursorMove(event)
                elif event.button == 2 and self.GraphType == GRAPH_PARALLEL:
                    width, height = self.Canvas.GetSize()
                    start_tick, end_tick = self.ParentWindow.GetRange()
                    self.MouseStartPos = wx.Point(x, y)
                    self.StartCursorTick = start_tick
        
        def OnCanvasButtonReleased(self, event):
            if self.ParentWindow.IsDragging():
                width, height = self.Canvas.GetSize()
                xw, yw = self.GetPosition()
                self.ParentWindow.StopDragNDrop(
                    self.Items[0].GetVariable(),
                    xw + event.x, 
                    yw + height - event.y)
            else:
                self.MouseStartPos = None
                self.StartCursorTick = None
                width, height = self.Canvas.GetSize()
                self.Canvas.HandleButtons(event.x, height - event.y)
        
        def OnCanvasMotion(self, event):
            width, height = self.Canvas.GetSize()
            if self.ParentWindow.IsDragging():
                xw, yw = self.GetPosition()
                self.ParentWindow.MoveDragNDrop(
                    xw + event.x, 
                    yw + height - event.y)
            elif not self.Is3DCanvas():
                if event.button == 1:
                    if event.inaxes == self.Axes:
                        if self.MouseStartPos is not None:
                            self.HandleCursorMove(event)
                    elif self.MouseStartPos is not None and len(self.Items) == 1:
                        xw, yw = self.GetPosition()
                        self.ParentWindow.StartDragNDrop(self, 
                            self.Items[0],
                            event.x + xw, height - event.y + yw, 
                            self.MouseStartPos.x + xw, self.MouseStartPos.y + yw)
                elif event.button == 2 and self.GraphType == GRAPH_PARALLEL:
                    start_tick, end_tick = self.ParentWindow.GetRange()
                    rect = self.GetAxesBoundingBox()
                    self.ParentWindow.SetCanvasPosition(
                        self.StartCursorTick + (self.MouseStartPos.x - event.x) *
                        (end_tick - start_tick) / rect.width)
                elif event.button is None:
                    if self.GraphType == GRAPH_PARALLEL:
                        orientation = [wx.HORIZONTAL] * len(self.AxesLabels)
                    elif len(self.AxesLabels) > 0:
                        orientation = [wx.HORIZONTAL, wx.VERTICAL]
                    item_idx = None
                    item_style = None
                    for i, (t, style) in enumerate(zip(self.AxesLabels, orientation)):
                        (x0, y0), (x1, y1) = t.get_window_extent().get_points()
                        rect = wx.Rect(x0, height - y1, x1 - x0, y1 - y0)
                        if rect.InsideXY(event.x, height - event.y):
                            item_idx = i
                            item_style = style
                            break
                    if item_idx is not None:
                        self.Canvas.PopupContextualButtons(self.Items[item_idx], rect, item_style)
                        return 
                    if not self.Canvas.IsOverContextualButton(event.x, height - event.y):
                        self.Canvas.DismissContextualButtons()
        
        def OnCanvasDragging(self, x, y, refresh=True):
            width, height = self.Canvas.GetSize()
            bbox = self.Canvas.GetAxesBoundingBox()
            if bbox.InsideXY(x, y) and not self.Is3DCanvas():
                rect = wx.Rect(bbox.x, bbox.y, bbox.width / 2, bbox.height)
                if rect.InsideXY(x, y):
                    self.Canvas.SetHighlight(HIGHLIGHT_LEFT)
                else:
                    self.Canvas.SetHighlight(HIGHLIGHT_RIGHT)
            elif y < height / 2:
                self.Canvas.SetHighlight(HIGHLIGHT_BEFORE)
            else:
                self.Canvas.SetHighlight(HIGHLIGHT_AFTER)
            if refresh:
                self.ParentWindow.ForceRefresh()
        
        def OnCanvasLeave(self, refresh=True):
            self.Canvas.SetHighlight(HIGHLIGHT_NONE)
            if refresh:
                self.ParentWindow.ForceRefresh()
        
        def OnCanvasScroll(self, event):
            if event.inaxes is not None:
                if self.GraphType == GRAPH_ORTHOGONAL:
                    start_tick, end_tick = self.ParentWindow.GetRange()
                    tick = (start_tick + end_tick) / 2.
                else:
                    tick = event.xdata
                self.ParentWindow.ChangeRange(int(-event.step) / 3, tick)
        
        def OnCanvasMouseWheel(self, event):
            if self.ItemButtons is not None:
                event.Skip()
        
        def HandleCursorMove(self, event):
            start_tick, end_tick = self.ParentWindow.GetRange()
            cursor_tick = None
            if self.GraphType == GRAPH_ORTHOGONAL:
                x_data = self.Items[0].GetData(start_tick, end_tick)
                y_data = self.Items[1].GetData(start_tick, end_tick)
                if len(x_data) > 0 and len(y_data) > 0:
                    length = min(len(x_data), len(y_data))
                    d = numpy.sqrt((x_data[:length,1]-event.xdata) ** 2 + (y_data[:length,1]-event.ydata) ** 2)
                    cursor_tick = x_data[numpy.argmin(d), 0]
            else:
                data = self.Items[0].GetData(start_tick, end_tick)
                if len(data) > 0:
                    cursor_tick = data[numpy.argmin(numpy.abs(data[:,0] - event.xdata)), 0]
            if cursor_tick is not None:
                self.ParentWindow.SetCursorTick(cursor_tick)
        
        def DoDragDrop(self, item_idx):
            self.Canvas.ShowButtons(False)
            self.Canvas.DismissContextualButtons()
            data = wx.TextDataObject(str((self.Items[item_idx].GetVariable(), "debug", "move")))
            dragSource = wx.DropSource(self.Canvas)
            dragSource.SetData(data)
            dragSource.DoDragDrop()
        
        def OnAxesMotion(self, event):
            if self.Is3DCanvas():
                current_time = gettime()
                if current_time - self.LastMotionTime > REFRESH_PERIOD:
                    self.LastMotionTime = current_time
                    Axes3D._on_move(self.Axes, event)
        
        def ResetGraphics(self):
            self.Figure.clear()
            if self.Is3DCanvas():
                self.Axes = self.Figure.gca(projection='3d')
                self.Axes.set_color_cycle(['b'])
                self.LastMotionTime = gettime()
                setattr(self.Axes, "_on_move", self.OnAxesMotion)
                self.Axes.mouse_init()
                self.Axes.tick_params(axis='z', labelsize='small')
            else:
                self.Axes = self.Figure.gca()
                self.Axes.set_color_cycle(color_cycle)
            self.Axes.tick_params(axis='x', labelsize='small')
            self.Axes.tick_params(axis='y', labelsize='small')
            self.Plots = []
            self.VLine = None
            self.HLine = None
            self.Labels = []
            self.AxesLabels = []
            if not self.Is3DCanvas():
                text_func = self.Axes.text
            else:
                text_func = self.Axes.text2D
            self.MaskLabel = text_func(0, 0, "", size='small', 
                                       transform=self.Axes.transAxes)
            if self.GraphType == GRAPH_PARALLEL or self.Is3DCanvas():
                num_item = len(self.Items)
                for idx in xrange(num_item):
                    if num_item == 1:
                        color = 'k'
                    else:
                        color = color_cycle[idx % len(color_cycle)]
                    if not self.Is3DCanvas():
                        self.AxesLabels.append(
                            text_func(0, 0, "", size='small', 
                                      color=color,
                                      transform=self.Axes.transAxes))
                    self.Labels.append(
                        text_func(0, 0, "", size='large', 
                                  horizontalalignment='right',
                                  color=color,
                                  transform=self.Axes.transAxes))
            else:
                self.AxesLabels.append(
                    self.Axes.text(0, 0, "", size='small',
                                   transform=self.Axes.transAxes))
                self.Labels.append(
                    self.Axes.text(0, 0, "", size='large',
                                   horizontalalignment='right',
                                   transform=self.Axes.transAxes))
                self.AxesLabels.append(
                    self.Axes.text(0, 0, "", size='small',
                                   rotation='vertical',
                                   verticalalignment='bottom',
                                   transform=self.Axes.transAxes))
                self.Labels.append(
                    self.Axes.text(0, 0, "", size='large',
                                   rotation='vertical',
                                   verticalalignment='top',
                                   transform=self.Axes.transAxes))
            if self.Canvas.CanvasSize == SIZE_MAXI:
                self.RefreshLabelsPosition(1)
            else:
                self.RefreshLabelsPosition(2)
            
        def AddItem(self, item):
            DebugVariableViewer.AddItem(self, item)
            self.ResetGraphics()
            
        def RemoveItem(self, item):
            DebugVariableViewer.RemoveItem(self, item)
            if not self.IsEmpty():
                if len(self.Items) == 1:
                    self.GraphType = GRAPH_PARALLEL
                self.ResetGraphics()
        
        def UnregisterObsoleteData(self):
            DebugVariableViewer.UnregisterObsoleteData(self)
            if not self.IsEmpty():
                self.ResetGraphics()
        
        def Is3DCanvas(self):
            return self.GraphType == GRAPH_ORTHOGONAL and len(self.Items) == 3
        
        def SetCursorTick(self, cursor_tick):
            self.CursorTick = cursor_tick
            
        def Refresh(self, refresh_graphics=True):
            
            if refresh_graphics:
                start_tick, end_tick = self.ParentWindow.GetRange()
                
                if self.GraphType == GRAPH_PARALLEL:    
                    min_value = max_value = None
                    
                    for idx, item in enumerate(self.Items):
                        data = item.GetData(start_tick, end_tick)
                        if data is not None:
                            item_min_value, item_max_value = item.GetRange()
                            if min_value is None:
                                min_value = item_min_value
                            elif item_min_value is not None:
                                min_value = min(min_value, item_min_value)
                            if max_value is None:
                                max_value = item_max_value
                            elif item_max_value is not None:
                                max_value = max(max_value, item_max_value)
                            
                            if len(self.Plots) <= idx:
                                self.Plots.append(
                                    self.Axes.plot(data[:, 0], data[:, 1])[0])
                            else:
                                self.Plots[idx].set_data(data[:, 0], data[:, 1])
                        
                    if min_value is not None and max_value is not None:
                        y_center = (min_value + max_value) / 2.
                        y_range = max(1.0, max_value - min_value)
                    else:
                        y_center = 0.5
                        y_range = 1.0
                    x_min, x_max = start_tick, end_tick
                    y_min, y_max = y_center - y_range * 0.55, y_center + y_range * 0.55
                    
                    if self.CursorTick is not None and start_tick <= self.CursorTick <= end_tick:
                        if self.VLine is None:
                            self.VLine = self.Axes.axvline(self.CursorTick, color=cursor_color)
                        else:
                            self.VLine.set_xdata((self.CursorTick, self.CursorTick))
                        self.VLine.set_visible(True)
                    else:
                        if self.VLine is not None:
                            self.VLine.set_visible(False)
                else:
                    min_start_tick = reduce(max, [item.GetData()[0, 0] 
                                                  for item in self.Items
                                                  if len(item.GetData()) > 0], 0)
                    start_tick = max(start_tick, min_start_tick)
                    end_tick = max(end_tick, min_start_tick)
                    x_data, x_min, x_max = OrthogonalData(self.Items[0], start_tick, end_tick)
                    y_data, y_min, y_max = OrthogonalData(self.Items[1], start_tick, end_tick)
                    if self.CursorTick is not None:
                        x_cursor, x_forced = self.Items[0].GetValue(self.CursorTick, raw=True)
                        y_cursor, y_forced = self.Items[1].GetValue(self.CursorTick, raw=True)
                    length = 0
                    if x_data is not None and y_data is not None:  
                        length = min(len(x_data), len(y_data))
                    if len(self.Items) < 3:
                        if x_data is not None and y_data is not None:
                            if len(self.Plots) == 0:
                                self.Plots.append(
                                    self.Axes.plot(x_data[:, 1][:length], 
                                                   y_data[:, 1][:length])[0])
                            else:
                                self.Plots[0].set_data(
                                    x_data[:, 1][:length], 
                                    y_data[:, 1][:length])
                        
                        if self.CursorTick is not None and start_tick <= self.CursorTick <= end_tick:
                            if self.VLine is None:
                                self.VLine = self.Axes.axvline(x_cursor, color=cursor_color)
                            else:
                                self.VLine.set_xdata((x_cursor, x_cursor))
                            if self.HLine is None:
                                self.HLine = self.Axes.axhline(y_cursor, color=cursor_color)
                            else:
                                self.HLine.set_ydata((y_cursor, y_cursor))
                            self.VLine.set_visible(True)
                            self.HLine.set_visible(True)
                        else:
                            if self.VLine is not None:
                                self.VLine.set_visible(False)
                            if self.HLine is not None:
                                self.HLine.set_visible(False)
                    else:
                        while len(self.Axes.lines) > 0:
                            self.Axes.lines.pop()
                        z_data, z_min, z_max = OrthogonalData(self.Items[2], start_tick, end_tick)
                        if self.CursorTick is not None:
                            z_cursor, z_forced = self.Items[2].GetValue(self.CursorTick, raw=True)
                        if x_data is not None and y_data is not None and z_data is not None:
                            length = min(length, len(z_data))
                            self.Axes.plot(x_data[:, 1][:length],
                                           y_data[:, 1][:length],
                                           zs = z_data[:, 1][:length])
                        self.Axes.set_zlim(z_min, z_max)
                        if self.CursorTick is not None and start_tick <= self.CursorTick <= end_tick:
                            for kwargs in [{"xs": numpy.array([x_min, x_max])},
                                           {"ys": numpy.array([y_min, y_max])},
                                           {"zs": numpy.array([z_min, z_max])}]:
                                for param, value in [("xs", numpy.array([x_cursor, x_cursor])),
                                                     ("ys", numpy.array([y_cursor, y_cursor])),
                                                     ("zs", numpy.array([z_cursor, z_cursor]))]:
                                    kwargs.setdefault(param, value)
                                kwargs["color"] = cursor_color
                                self.Axes.plot(**kwargs)
                    
                self.Axes.set_xlim(x_min, x_max)
                self.Axes.set_ylim(y_min, y_max)
            
            variable_name_mask = self.ParentWindow.GetVariableNameMask()
            if self.CursorTick is not None:
                values, forced = apply(zip, [item.GetValue(self.CursorTick) for item in self.Items])
            else:
                values, forced = apply(zip, [(item.GetValue(), item.IsForced()) for item in self.Items])
            labels = [item.GetVariable(variable_name_mask) for item in self.Items]
            styles = map(lambda x: {True: 'italic', False: 'normal'}[x], forced)
            self.MaskLabel.set_text('.'.join(variable_name_mask))
            if self.Is3DCanvas():
                for idx, label_func in enumerate([self.Axes.set_xlabel, 
                                                  self.Axes.set_ylabel,
                                                  self.Axes.set_zlabel]):
                    label_func(labels[idx], fontdict={'size': 'small','color': color_cycle[idx]})
            else:
                for label, text in zip(self.AxesLabels, labels):
                    label.set_text(text)
            for label, value, style in zip(self.Labels, values, styles):
                label.set_text(value)
                label.set_style(style)
                        
            self.Canvas.draw()
    
class DebugVariablePanel(wx.Panel, DebugViewer):
    
    def __init__(self, parent, producer, window):
        wx.Panel.__init__(self, parent, style=wx.SP_3D|wx.TAB_TRAVERSAL)
        self.SetBackgroundColour(wx.WHITE)
        
        self.ParentWindow = window
        
        DebugViewer.__init__(self, producer, True)
        
        self.HasNewData = False
        
        if USE_MPL:
            main_sizer = wx.BoxSizer(wx.VERTICAL)
            
            self.Ticks = numpy.array([])
            self.RangeValues = None
            self.StartTick = 0
            self.Fixed = False
            self.Force = False
            self.CursorTick = None
            self.DraggingAxesPanel = None
            self.DraggingAxesBoundingBox = None
            self.DraggingAxesMousePos = None
            self.VariableNameMask = None
            
            self.GraphicPanels = []
            
            graphics_button_sizer = wx.BoxSizer(wx.HORIZONTAL)
            main_sizer.AddSizer(graphics_button_sizer, border=5, flag=wx.GROW|wx.ALL)
            
            range_label = wx.StaticText(self, label=_('Range:'))
            graphics_button_sizer.AddWindow(range_label, flag=wx.ALIGN_CENTER_VERTICAL)
            
            self.CanvasRange = wx.ComboBox(self, style=wx.CB_READONLY)
            self.Bind(wx.EVT_COMBOBOX, self.OnRangeChanged, self.CanvasRange)
            graphics_button_sizer.AddWindow(self.CanvasRange, 1, 
                  border=5, flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL)
            
            for name, bitmap, help in [
                ("ResetButton", "reset", _("Clear the graph values")),
                ("CurrentButton", "current", _("Go to current value")),
                ("ExportGraphButton", "export_graph", _("Export graph values to clipboard"))]:
                button = wx.lib.buttons.GenBitmapButton(self, 
                      bitmap=GetBitmap(bitmap), 
                      size=wx.Size(28, 28), style=wx.NO_BORDER)
                button.SetToolTipString(help)
                setattr(self, name, button)
                self.Bind(wx.EVT_BUTTON, getattr(self, "On" + name), button)
                graphics_button_sizer.AddWindow(button, border=5, flag=wx.LEFT)
            
            self.CanvasPosition = wx.ScrollBar(self, 
                  size=wx.Size(0, 16), style=wx.SB_HORIZONTAL)
            self.CanvasPosition.Bind(wx.EVT_SCROLL_THUMBTRACK, 
                  self.OnPositionChanging, self.CanvasPosition)
            self.CanvasPosition.Bind(wx.EVT_SCROLL_LINEUP, 
                  self.OnPositionChanging, self.CanvasPosition)
            self.CanvasPosition.Bind(wx.EVT_SCROLL_LINEDOWN, 
                  self.OnPositionChanging, self.CanvasPosition)
            self.CanvasPosition.Bind(wx.EVT_SCROLL_PAGEUP, 
                  self.OnPositionChanging, self.CanvasPosition)
            self.CanvasPosition.Bind(wx.EVT_SCROLL_PAGEDOWN, 
                  self.OnPositionChanging, self.CanvasPosition)
            main_sizer.AddWindow(self.CanvasPosition, border=5, flag=wx.GROW|wx.LEFT|wx.RIGHT|wx.BOTTOM)
            
            self.TickSizer = wx.BoxSizer(wx.HORIZONTAL)
            main_sizer.AddSizer(self.TickSizer, border=5, flag=wx.ALL|wx.GROW)
            
            self.TickLabel = wx.StaticText(self)
            self.TickSizer.AddWindow(self.TickLabel, 1, border=5, flag=wx.RIGHT|wx.GROW)
            
            self.TickTimeLabel = wx.StaticText(self)
            self.TickSizer.AddWindow(self.TickTimeLabel)
            
            self.GraphicsWindow = wx.ScrolledWindow(self, style=wx.HSCROLL|wx.VSCROLL)
            self.GraphicsWindow.SetBackgroundColour(wx.WHITE)
            self.GraphicsWindow.SetDropTarget(DebugVariableDropTarget(self))
            self.GraphicsWindow.Bind(wx.EVT_SIZE, self.OnGraphicsWindowResize)
            main_sizer.AddWindow(self.GraphicsWindow, 1, flag=wx.GROW)
            
            self.GraphicsSizer = wx.BoxSizer(wx.VERTICAL)
            self.GraphicsWindow.SetSizer(self.GraphicsSizer)
            
            self.RefreshCanvasRange()
            
        else:
            main_sizer = wx.FlexGridSizer(cols=1, hgap=0, rows=2, vgap=0)
            main_sizer.AddGrowableCol(0)
            main_sizer.AddGrowableRow(1)
            
            button_sizer = wx.BoxSizer(wx.HORIZONTAL)
            main_sizer.AddSizer(button_sizer, border=5, 
                  flag=wx.ALIGN_RIGHT|wx.ALL)
            
            for name, bitmap, help in [
                    ("DeleteButton", "remove_element", _("Remove debug variable")),
                    ("UpButton", "up", _("Move debug variable up")),
                    ("DownButton", "down", _("Move debug variable down"))]:
                button = wx.lib.buttons.GenBitmapButton(self, bitmap=GetBitmap(bitmap), 
                      size=wx.Size(28, 28), style=wx.NO_BORDER)
                button.SetToolTipString(help)
                setattr(self, name, button)
                button_sizer.AddWindow(button, border=5, flag=wx.LEFT)
            
            self.VariablesGrid = CustomGrid(self, size=wx.Size(-1, 150), style=wx.VSCROLL)
            self.VariablesGrid.SetDropTarget(DebugVariableDropTarget(self, self.VariablesGrid))
            self.VariablesGrid.Bind(wx.grid.EVT_GRID_CELL_RIGHT_CLICK, 
                  self.OnVariablesGridCellRightClick)
            self.VariablesGrid.Bind(wx.grid.EVT_GRID_CELL_LEFT_CLICK, 
                  self.OnVariablesGridCellLeftClick)
            main_sizer.AddWindow(self.VariablesGrid, flag=wx.GROW)
        
            self.Table = DebugVariableTable(self, [], GetDebugVariablesTableColnames())
            self.VariablesGrid.SetTable(self.Table)
            self.VariablesGrid.SetButtons({"Delete": self.DeleteButton,
                                           "Up": self.UpButton,
                                           "Down": self.DownButton})
        
            def _AddVariable(new_row):
                return self.VariablesGrid.GetGridCursorRow()
            setattr(self.VariablesGrid, "_AddRow", _AddVariable)
        
            def _DeleteVariable(row):
                item = self.Table.GetItem(row)
                self.RemoveDataConsumer(item)
                self.Table.RemoveItem(row)
                self.RefreshView()
            setattr(self.VariablesGrid, "_DeleteRow", _DeleteVariable)
            
            def _MoveVariable(row, move):
                new_row = max(0, min(row + move, self.Table.GetNumberRows() - 1))
                if new_row != row:
                    self.Table.MoveItem(row, new_row)
                    self.RefreshView()
                return new_row
            setattr(self.VariablesGrid, "_MoveRow", _MoveVariable)
            
            self.VariablesGrid.SetRowLabelSize(0)
            
            self.GridColSizes = [200, 100]
            
            for col in range(self.Table.GetNumberCols()):
                attr = wx.grid.GridCellAttr()
                attr.SetAlignment(wx.ALIGN_RIGHT, wx.ALIGN_CENTER)
                self.VariablesGrid.SetColAttr(col, attr)
                self.VariablesGrid.SetColSize(col, self.GridColSizes[col])
            
            self.Table.ResetView(self.VariablesGrid)
            self.VariablesGrid.RefreshButtons()
        
        self.SetSizer(main_sizer)
        
    def SetDataProducer(self, producer):
        DebugViewer.SetDataProducer(self, producer)
        
        if USE_MPL:
            if self.DataProducer is not None:
                self.Ticktime = self.DataProducer.GetTicktime()
                self.RefreshCanvasRange()
            else:
                self.Ticktime = 0
    
    def RefreshNewData(self, *args, **kwargs):
        if self.HasNewData or self.Force:
            self.HasNewData = False
            self.RefreshView(only_values=True)
        DebugViewer.RefreshNewData(self, *args, **kwargs)
    
    def NewDataAvailable(self, tick, *args, **kwargs):
        if USE_MPL and tick is not None:
            if len(self.Ticks) == 0:
                self.StartTick = tick 
            self.Ticks = numpy.append(self.Ticks, [tick])
            if not self.Fixed or tick < self.StartTick + self.CurrentRange:
                self.StartTick = max(self.StartTick, tick - self.CurrentRange)
            if self.Fixed and self.Ticks[-1] - self.Ticks[0] < self.CurrentRange:
                self.Force = True
        DebugViewer.NewDataAvailable(self, tick, *args, **kwargs)
    
    def ForceRefresh(self):
        self.Force = True
        wx.CallAfter(self.NewDataAvailable, None, True)
    
    def RefreshGraphicsSizer(self):
        self.GraphicsSizer.Clear()
        
        for panel in self.GraphicPanels:
            self.GraphicsSizer.AddWindow(panel, flag=wx.GROW)
            
        self.GraphicsSizer.Layout()
        self.RefreshGraphicsWindowScrollbars()
    
    def SetCanvasPosition(self, tick):
        tick = max(self.Ticks[0], min(tick, self.Ticks[-1] - self.CurrentRange))
        self.StartTick = self.Ticks[numpy.argmin(numpy.abs(self.Ticks - tick))]
        self.Fixed = True
        self.RefreshCanvasPosition()
        self.ForceRefresh()
    
    def SetCursorTick(self, cursor_tick):
        self.CursorTick = cursor_tick
        self.Fixed = True
        self.ResetCursorTick() 
    
    def ResetCursorTick(self):
        self.CursorTick = None
        self.ResetCursorTick()
    
    def ResetCursorTick(self):
        for panel in self.GraphicPanels:
            if isinstance(panel, DebugVariableGraphic):
                panel.SetCursorTick(self.CursorTick)
        self.ForceRefresh()
    
    def StartDragNDrop(self, panel, item, x_mouse, y_mouse, x_mouse_start, y_mouse_start):
        if len(panel.GetItems()) > 1:
            self.DraggingAxesPanel = DebugVariableGraphic(self.GraphicsWindow, self, [item], GRAPH_PARALLEL)
            self.DraggingAxesPanel.SetCursorTick(self.CursorTick)
            width, height = panel.GetSize()
            self.DraggingAxesPanel.SetMinSize(wx.Size(width, height))
            self.DraggingAxesPanel.SetPosition(wx.Point(0, -height))
        else:
            self.DraggingAxesPanel = panel
        self.DraggingAxesBoundingBox = panel.GetAxesBoundingBox(absolute=True)
        self.DraggingAxesMousePos = wx.Point(
            x_mouse_start - self.DraggingAxesBoundingBox.x, 
            y_mouse_start - self.DraggingAxesBoundingBox.y)
        self.MoveDragNDrop(x_mouse, y_mouse)
        
    def MoveDragNDrop(self, x_mouse, y_mouse):
        self.DraggingAxesBoundingBox.x = x_mouse - self.DraggingAxesMousePos.x
        self.DraggingAxesBoundingBox.y = y_mouse - self.DraggingAxesMousePos.y
        for idx, panel in enumerate(self.GraphicPanels):
            x, y = panel.GetPosition()
            width, height = panel.Canvas.GetSize()
            rect = wx.Rect(x, y, width, height)
            if (rect.InsideXY(x_mouse, y_mouse) or 
                idx == 0 and y_mouse < 0 or
                idx == len(self.GraphicPanels) - 1 and y_mouse > panel.GetPosition()[1]):
                panel.OnCanvasDragging(x_mouse - x, y_mouse - y, False)
            else:
                panel.OnCanvasLeave(False)
        self.ForceRefresh()
    
    def IsDragging(self):
        return self.DraggingAxesPanel is not None
    
    def GetDraggingAxesClippingRegion(self, panel):
        x, y = panel.GetPosition()
        width, height = panel.Canvas.GetSize()
        bbox = wx.Rect(x, y, width, height)
        bbox = bbox.Intersect(self.DraggingAxesBoundingBox)
        bbox.x -= x
        bbox.y -= y
        return bbox
    
    def StopDragNDrop(self, variable, x_mouse, y_mouse):
        self.DraggingAxesPanel = None
        self.DraggingAxesBoundingBox = None
        self.DraggingAxesMousePos = None
        for idx, panel in enumerate(self.GraphicPanels):
            panel.OnCanvasLeave(False)
            xw, yw = panel.GetPosition()
            width, height = panel.Canvas.GetSize()
            bbox = wx.Rect(xw, yw, width, height)
            if bbox.InsideXY(x_mouse, y_mouse):
                merge_type = GRAPH_PARALLEL
                if panel.Is3DCanvas():
                    if y_mouse > yw + height / 2:
                        idx += 1
                    wx.CallAfter(self.MoveGraph, variable, idx)
                else:
                    rect = panel.GetAxesBoundingBox(True)
                    if rect.InsideXY(x_mouse, y_mouse):
                        merge_rect = wx.Rect(rect.x, rect.y, rect.width / 2., rect.height)
                        if merge_rect.InsideXY(x_mouse, y_mouse):
                            merge_type = GRAPH_ORTHOGONAL
                        wx.CallAfter(self.MergeGraphs, variable, idx, merge_type, force=True)
                    else:
                        if y_mouse > yw + height / 2:
                            idx += 1
                        wx.CallAfter(self.MoveGraph, variable, idx)
                self.ForceRefresh()
                return 
        width, height = self.GraphicsWindow.GetVirtualSize()
        rect = wx.Rect(0, 0, width, height)
        if rect.InsideXY(x_mouse, y_mouse):
            wx.CallAfter(self.MoveGraph, variable, len(self.GraphicPanels))
        self.ForceRefresh()
    
    def RefreshView(self, only_values=False):
        if USE_MPL:
            self.RefreshCanvasPosition()
            
            width, height = self.GraphicsWindow.GetVirtualSize()
            bitmap = wx.EmptyBitmap(width, height)
            dc = wx.BufferedPaintDC(self.GraphicsWindow, bitmap)
            dc.Clear()
            dc.BeginDrawing()
            if self.DraggingAxesPanel is not None:
                destBBox = self.DraggingAxesBoundingBox
                srcBBox = self.DraggingAxesPanel.GetAxesBoundingBox()
                
                srcBmp = _convert_agg_to_wx_bitmap(self.DraggingAxesPanel.Canvas.get_renderer(), None)
                srcDC = wx.MemoryDC()
                srcDC.SelectObject(srcBmp)
                    
                dc.Blit(destBBox.x, destBBox.y, 
                        int(destBBox.width), int(destBBox.height), 
                        srcDC, srcBBox.x, srcBBox.y)
            dc.EndDrawing()
            
            if not self.Fixed or self.Force:
                self.Force = False
                refresh_graphics = True
            else:
                refresh_graphics = False
            
            if self.DraggingAxesPanel is not None and self.DraggingAxesPanel not in self.GraphicPanels:
                self.DraggingAxesPanel.Refresh()
            for panel in self.GraphicPanels:
                if isinstance(panel, DebugVariableGraphic):
                    panel.Refresh(refresh_graphics)
                else:
                    panel.Refresh()
            
            if self.CursorTick is not None:
                tick = self.CursorTick
            elif len(self.Ticks) > 0:
                tick = self.Ticks[-1]
            else:
                tick = None
            if tick is not None:
                self.TickLabel.SetLabel("Tick: %d" % tick)
                if self.Ticktime > 0:
                    tick_duration = int(tick * self.Ticktime)
                    not_null = False
                    duration = ""
                    for value, format in [(tick_duration / DAY, "%dd"),
                                          ((tick_duration % DAY) / HOUR, "%dh"),
                                          ((tick_duration % HOUR) / MINUTE, "%dm"),
                                          ((tick_duration % MINUTE) / SECOND, "%ds")]:
                        
                        if value > 0 or not_null:
                            duration += format % value
                            not_null = True
                    
                    duration += "%gms" % (float(tick_duration % SECOND) / MILLISECOND) 
                    self.TickTimeLabel.SetLabel("t: %s" % duration)
                else:
                    self.TickTimeLabel.SetLabel("")
            else:
                self.TickLabel.SetLabel("")
                self.TickTimeLabel.SetLabel("")
            self.TickSizer.Layout()
        else:
            self.Freeze()
            
            if only_values:
                for col in xrange(self.Table.GetNumberCols()):
                    if self.Table.GetColLabelValue(col, False) == "Value":
                        for row in xrange(self.Table.GetNumberRows()):
                            self.VariablesGrid.SetCellValue(row, col, str(self.Table.GetValueByName(row, "Value")))
            else:
                self.Table.ResetView(self.VariablesGrid)
            self.VariablesGrid.RefreshButtons()
            
            self.Thaw()
        
    def UnregisterObsoleteData(self):
        if USE_MPL:
            if self.DataProducer is not None:
                self.Ticktime = self.DataProducer.GetTicktime()
                self.RefreshCanvasRange()
            
            for panel in self.GraphicPanels:
                panel.UnregisterObsoleteData()
                if panel.IsEmpty():
                    if panel.Canvas.HasCapture():
                        panel.Canvas.ReleaseMouse()
                    self.GraphicPanels.remove(panel)
                    panel.Destroy()
            
            self.ResetVariableNameMask()
            self.RefreshGraphicsSizer()
            self.ForceRefresh()
            
        else:
            items = [(idx, item) for idx, item in enumerate(self.Table.GetData())]
            items.reverse()
            for idx, item in items:
                iec_path = item.GetVariable().upper()
                if self.GetDataType(iec_path) is None:
                    self.RemoveDataConsumer(item)
                    self.Table.RemoveItem(idx)
                else:
                    self.AddDataConsumer(iec_path, item)
                    item.RefreshVariableType()
            self.Freeze()
            self.Table.ResetView(self.VariablesGrid)
            self.VariablesGrid.RefreshButtons()
            self.Thaw()
    
    def ResetView(self):
        self.DeleteDataConsumers()
        if USE_MPL:
            self.Fixed = False
            for panel in self.GraphicPanels:
                panel.Destroy()
            self.GraphicPanels = []
            self.ResetVariableNameMask()
            self.RefreshGraphicsSizer()
        else:
            self.Table.Empty()
            self.Freeze()
            self.Table.ResetView(self.VariablesGrid)
            self.VariablesGrid.RefreshButtons()
            self.Thaw()
    
    def RefreshCanvasRange(self):
        if self.Ticktime == 0 and self.RangeValues != RANGE_VALUES:
            self.RangeValues = RANGE_VALUES
            self.CanvasRange.Clear()
            for text, value in RANGE_VALUES:
                self.CanvasRange.Append(text)
            self.CanvasRange.SetStringSelection(RANGE_VALUES[0][0])
            self.CurrentRange = RANGE_VALUES[0][1]
            self.RefreshView(True)
        elif self.Ticktime != 0 and self.RangeValues != TIME_RANGE_VALUES:
            self.RangeValues = TIME_RANGE_VALUES
            self.CanvasRange.Clear()
            for text, value in TIME_RANGE_VALUES:
                self.CanvasRange.Append(text)
            self.CanvasRange.SetStringSelection(TIME_RANGE_VALUES[0][0])
            self.CurrentRange = TIME_RANGE_VALUES[0][1] / self.Ticktime
            self.RefreshView(True)
    
    def RefreshCanvasPosition(self):
        if len(self.Ticks) > 0:
            pos = int(self.StartTick - self.Ticks[0])
            range = int(self.Ticks[-1] - self.Ticks[0])
        else:
            pos = 0
            range = 0
        self.CanvasPosition.SetScrollbar(pos, self.CurrentRange, range, self.CurrentRange)
    
    def GetForceVariableMenuFunction(self, iec_path, item):
        iec_type = self.GetDataType(iec_path)
        def ForceVariableFunction(event):
            if iec_type is not None:
                dialog = ForceVariableDialog(self, iec_type, str(item.GetValue()))
                if dialog.ShowModal() == wx.ID_OK:
                    self.ForceDataValue(iec_path, dialog.GetValue())
        return ForceVariableFunction

    def GetReleaseVariableMenuFunction(self, iec_path):
        def ReleaseVariableFunction(event):
            self.ReleaseDataValue(iec_path)
        return ReleaseVariableFunction
    
    def OnVariablesGridCellLeftClick(self, event):
        if event.GetCol() == 0:
            row = event.GetRow()
            data = wx.TextDataObject(str((self.Table.GetValueByName(row, "Variable"), "debug")))
            dragSource = wx.DropSource(self.VariablesGrid)
            dragSource.SetData(data)
            dragSource.DoDragDrop()
        event.Skip()
    
    def OnVariablesGridCellRightClick(self, event):
        row, col = event.GetRow(), event.GetCol()
        if self.Table.GetColLabelValue(col, False) == "Value":
            iec_path = self.Table.GetValueByName(row, "Variable").upper()

            menu = wx.Menu(title='')
            
            new_id = wx.NewId()
            AppendMenu(menu, help='', id=new_id, kind=wx.ITEM_NORMAL, text=_("Force value"))
            self.Bind(wx.EVT_MENU, self.GetForceVariableMenuFunction(iec_path.upper(), self.Table.GetItem(row)), id=new_id)
            
            new_id = wx.NewId()
            AppendMenu(menu, help='', id=new_id, kind=wx.ITEM_NORMAL, text=_("Release value"))
            self.Bind(wx.EVT_MENU, self.GetReleaseVariableMenuFunction(iec_path.upper()), id=new_id)
            
            if self.Table.IsForced(row):
                menu.Enable(new_id, True)
            else:
                menu.Enable(new_id, False)
            
            self.PopupMenu(menu)
            
            menu.Destroy()
        event.Skip()
    
    def ChangeRange(self, dir, tick):
        current_range = self.CurrentRange
        current_range_idx = self.CanvasRange.GetSelection()
        new_range_idx = max(0, min(current_range_idx + dir, len(self.RangeValues) - 1))
        if new_range_idx != current_range_idx:
            self.CanvasRange.SetSelection(new_range_idx)
            if self.Ticktime == 0:
                self.CurrentRange = self.RangeValues[new_range_idx][1]
            else:
                self.CurrentRange = self.RangeValues[new_range_idx][1] / self.Ticktime
            if len(self.Ticks) > 0:
                new_start_tick = tick - (tick - self.StartTick) * self.CurrentRange / current_range 
                self.StartTick = self.Ticks[numpy.argmin(numpy.abs(self.Ticks - new_start_tick))]
                self.Fixed = self.StartTick < self.Ticks[-1] - self.CurrentRange
            self.ForceRefresh()
    
    def RefreshRange(self):
        if len(self.Ticks) > 0:
            if self.Fixed and self.Ticks[-1] - self.Ticks[0] < self.CurrentRange:
                self.Fixed = False
            if self.Fixed:
                self.StartTick = min(self.StartTick, self.Ticks[-1] - self.CurrentRange)
            else:
                self.StartTick = max(self.Ticks[0], self.Ticks[-1] - self.CurrentRange)
        self.ForceRefresh()
    
    def OnRangeChanged(self, event):
        try:
            if self.Ticktime == 0:
                self.CurrentRange = self.RangeValues[self.CanvasRange.GetSelection()][1]
            else:
                self.CurrentRange = self.RangeValues[self.CanvasRange.GetSelection()][1] / self.Ticktime
        except ValueError, e:
            self.CanvasRange.SetValue(str(self.CurrentRange))
        wx.CallAfter(self.RefreshRange)
        event.Skip()
    
    def OnResetButton(self, event):
        self.ResetGraphicsValues()
        event.Skip()

    def OnCurrentButton(self, event):
        if len(self.Ticks) > 0:
            self.StartTick = max(self.Ticks[0], self.Ticks[-1] - self.CurrentRange)
            self.Fixed = False
            self.CursorTick = None
            self.ResetCursorTick()
        event.Skip()
    
    def CopyDataToClipboard(self, variables):
        text = "tick;%s;\n" % ";".join([item.GetVariable() for item, data in variables])
        next_tick = NextTick(variables)
        while next_tick is not None:
            values = []
            for item, data in variables:
                if len(data) > 0:
                    if next_tick == data[0][0]:
                        var_type = item.GetVariableType()
                        if var_type in ["STRING", "WSTRING"]:
                            value = item.GetRawValue(int(data.pop(0)[2]))
                            if var_type == "STRING":
                                values.append("'%s'" % value)
                            else:
                                values.append('"%s"' % value)
                        else:
                            values.append("%.3f" % data.pop(0)[1])
                    else:
                        values.append("")
                else:
                    values.append("")
            text += "%d;%s;\n" % (next_tick, ";".join(values))
            next_tick = NextTick(variables)
        self.ParentWindow.SetCopyBuffer(text)
    
    def OnExportGraphButton(self, event):
        variables = []
        if USE_MPL:
            items = []
            for panel in self.GraphicPanels:
                items.extend(panel.GetItems())
        else:
            items = self.Table.GetData()
        for item in items:
            if item.IsNumVariable():
                variables.append((item, [entry for entry in item.GetData()]))
        wx.CallAfter(self.CopyDataToClipboard, variables)
        event.Skip()
    
    def OnPositionChanging(self, event):
        if len(self.Ticks) > 0:
            self.StartTick = self.Ticks[0] + event.GetPosition()
            self.Fixed = True
            self.ForceRefresh()
        event.Skip()
    
    def GetRange(self):
        return self.StartTick, self.StartTick + self.CurrentRange
    
    def GetViewerIndex(self, viewer):
        if viewer in self.GraphicPanels:
            return self.GraphicPanels.index(viewer)
        return None
    
    def ResetVariableNameMask(self):
        items = []
        for panel in self.GraphicPanels:
            items.extend(panel.GetItems())
        if len(items) > 1:
            self.VariableNameMask = reduce(compute_mask,
                [item.GetVariable().split('.') for item in items])
        elif len(items) > 0:
            self.VariableNameMask = items[0].GetVariable().split('.')[:-1] + ['*']
        else:
            self.VariableNameMask = []
            
    def GetVariableNameMask(self):
        return self.VariableNameMask
    
    def InsertValue(self, iec_path, idx = None, force=False):
        if USE_MPL:
            for panel in self.GraphicPanels:
                if panel.GetItem(iec_path) is not None:
                    return
            if idx is None:
                idx = len(self.GraphicPanels)
        else:
            for item in self.Table.GetData():
                if iec_path == item.GetVariable():
                    return
            if idx is None:
                idx = self.Table.GetNumberRows()
        item = VariableTableItem(self, iec_path)
        result = self.AddDataConsumer(iec_path.upper(), item)
        if result is not None or force:
            
            if USE_MPL:
                if item.IsNumVariable():
                    panel = DebugVariableGraphic(self.GraphicsWindow, self, [item], GRAPH_PARALLEL)
                    if self.CursorTick is not None:
                        panel.SetCursorTick(self.CursorTick)
                else:
                    panel = DebugVariableText(self.GraphicsWindow, self, [item])
                if idx is not None:
                    self.GraphicPanels.insert(idx, panel)
                else:
                    self.GraphicPanels.append(panel)
                self.ResetVariableNameMask()
                self.RefreshGraphicsSizer()
            else:
                self.Table.InsertItem(idx, item)
            
            self.ForceRefresh()
    
    def MoveGraph(self, iec_path, idx = None):
        if idx is None:
            idx = len(self.GraphicPanels)
        source_panel = None
        item = None
        for panel in self.GraphicPanels:
            item = panel.GetItem(iec_path)
            if item is not None:
                source_panel = panel
                break
        if source_panel is not None:
            source_panel.RemoveItem(item)
            if source_panel.IsEmpty():
                if source_panel.Canvas.HasCapture():
                    source_panel.Canvas.ReleaseMouse()
                self.GraphicPanels.remove(source_panel)
                source_panel.Destroy()
            
            panel = DebugVariableGraphic(self.GraphicsWindow, self, [item], GRAPH_PARALLEL)
            if self.CursorTick is not None:
                panel.SetCursorTick(self.CursorTick)
            self.GraphicPanels.insert(idx, panel)
            self.ResetVariableNameMask()
            self.RefreshGraphicsSizer()
            self.ForceRefresh()
    
    def MergeGraphs(self, source, target_idx, merge_type, force=False):
        source_item = None
        source_panel = None
        for panel in self.GraphicPanels:
            source_item = panel.GetItem(source)
            if source_item is not None:
                source_panel = panel
                break
        if source_item is None:
            item = VariableTableItem(self, source)
            if item.IsNumVariable():
                result = self.AddDataConsumer(source.upper(), item)
                if result is not None or force:
                    source_item = item
        if source_item is not None:
            target_panel = self.GraphicPanels[target_idx]
            graph_type = target_panel.GraphType
            if target_panel != source_panel:
                if (merge_type == GRAPH_PARALLEL and graph_type != merge_type or
                    merge_type == GRAPH_ORTHOGONAL and 
                    (graph_type == GRAPH_PARALLEL and len(target_panel.Items) > 1 or
                     graph_type == GRAPH_ORTHOGONAL and len(target_panel.Items) >= 3)):
                    return
                
                if source_panel is not None:
                    source_panel.RemoveItem(source_item)
                    if source_panel.IsEmpty():
                        if source_panel.Canvas.HasCapture():
                            source_panel.Canvas.ReleaseMouse()
                        self.GraphicPanels.remove(source_panel)
                        source_panel.Destroy()
                        
                target_panel.AddItem(source_item)
                target_panel.GraphType = merge_type
                target_panel.ResetGraphics()
                
                self.ResetVariableNameMask()
                self.RefreshGraphicsSizer()
                self.ForceRefresh()
    
    def DeleteValue(self, source_panel, item=None):
        source_idx = self.GetViewerIndex(source_panel)
        if source_idx is not None:
            
            if item is None:
                source_panel.Clear()
                source_panel.Destroy()
                self.GraphicPanels.remove(source_panel)
                self.ResetVariableNameMask()
                self.RefreshGraphicsSizer()
            else:
                source_panel.RemoveItem(item)
                if source_panel.IsEmpty():
                    source_panel.Destroy()
                    self.GraphicPanels.remove(source_panel)
                    self.ResetVariableNameMask()
                    self.RefreshGraphicsSizer()
            self.ForceRefresh()
    
    def GetDebugVariables(self):
        if USE_MPL:
            return [panel.GetVariables() for panel in self.GraphicPanels]
        else:
            return [item.GetVariable() for item in self.Table.GetData()]
    
    def SetDebugVariables(self, variables):
        if USE_MPL:
            for variable in variables:
                if isinstance(variable, (TupleType, ListType)):
                    items = []
                    for iec_path in variable:
                        item = VariableTableItem(self, iec_path)
                        if not item.IsNumVariable():
                            continue
                        self.AddDataConsumer(iec_path.upper(), item)
                        items.append(item)
                    if isinstance(variable, ListType):
                        panel = DebugVariableGraphic(self.GraphicsWindow, self, items, GRAPH_PARALLEL)
                    elif isinstance(variable, TupleType) and len(items) <= 3:
                        panel = DebugVariableGraphic(self.GraphicsWindow, self, items, GRAPH_ORTHOGONAL)
                    else:
                        continue
                    self.GraphicPanels.append(panel)
                    self.ResetVariableNameMask()
                    self.RefreshGraphicsSizer()
                else:
                    self.InsertValue(variable, force=True)
            self.ForceRefresh()
        else:
            for variable in variables:
                if isinstance(variable, (ListType, TupleType)):
                    for iec_path in variable:
                        self.InsertValue(iec_path, force=True)
                else:
                    self.InsertValue(variable, force=True)
    
    def ResetGraphicsValues(self):
        if USE_MPL:
            self.Ticks = numpy.array([])
            self.StartTick = 0
            self.Fixed = False
            for panel in self.GraphicPanels:
                panel.ResetData()

    def RefreshGraphicsWindowScrollbars(self):
        xstart, ystart = self.GraphicsWindow.GetViewStart()
        window_size = self.GraphicsWindow.GetClientSize()
        vwidth, vheight = self.GraphicsSizer.GetMinSize()
        posx = max(0, min(xstart, (vwidth - window_size[0]) / SCROLLBAR_UNIT))
        posy = max(0, min(ystart, (vheight - window_size[1]) / SCROLLBAR_UNIT))
        self.GraphicsWindow.Scroll(posx, posy)
        self.GraphicsWindow.SetScrollbars(SCROLLBAR_UNIT, SCROLLBAR_UNIT, 
                vwidth / SCROLLBAR_UNIT, vheight / SCROLLBAR_UNIT, posx, posy)
    
    def OnGraphicsWindowResize(self, event):
        self.RefreshGraphicsWindowScrollbars()
        event.Skip()
