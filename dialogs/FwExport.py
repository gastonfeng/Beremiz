import os
import shutil
import traceback
from os.path import exists

import wx

from LogPseudoFile import LogPseudoFile
from controls import CustomStyledTextCtrl
from util.disk import usbpath

if wx.Platform == '__WXMSW__':
    faces = {
        'mono': 'Courier New',
        'size': 8,
    }
else:
    faces = {
        'mono': 'Courier',
        'size': 10,
    }


class UCopyEditor(wx.Dialog):
    def _init_ctrls(self, parent):
        self.UriTypeChoice = wx.Choice(parent=self, choices=self.choices, size=wx.Size(200, 32))
        self.UriTypeChoice.SetSelection(0)
        self.Bind(wx.EVT_CHOICE, self.OnTypeChoice, self.UriTypeChoice)
        self.editor_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.LogConsole = CustomStyledTextCtrl(name='LogConsole', parent=self, size=wx.Size(400, 200))
        self.LogConsole.SetReadOnly(True)
        self.LogConsole.SetWrapMode(wx.stc.STC_WRAP_CHAR)

        # Define Log Console styles
        self.LogConsole.StyleSetSpec(wx.stc.STC_STYLE_DEFAULT, "face:%(mono)s,size:%(size)d" % faces)
        self.LogConsole.StyleClearAll()
        self.LogConsole.StyleSetSpec(1, "face:%(mono)s,fore:#FF0000,size:%(size)d" % faces)
        self.LogConsole.StyleSetSpec(2, "face:%(mono)s,fore:#FF0000,back:#FFFF00,size:%(size)d" % faces)

        # Define Log Console markers
        self.LogConsole.SetMarginSensitive(1, True)
        self.LogConsole.SetMarginType(1, wx.stc.STC_MARGIN_SYMBOL)
        self.LogConsole.MarkerDefine(0, wx.stc.STC_MARK_CIRCLE, "BLACK", "RED")

        self.LogConsole.SetModEventMask(wx.stc.STC_MOD_INSERTTEXT)

        self.ButtonSizer = self.CreateButtonSizer(wx.CANCEL)

        self.ButtonFlash = wx.Button(self, -1, _('Copy'))
        self.ButtonFlash.Bind(wx.EVT_BUTTON, self.flash)
        self.prgRte = wx.CheckBox(self, label=_("Copy Runtime Firmware"))
        self.prgApp = wx.CheckBox(self, label=_("Copy PLC APP"))
        self.prgRte.SetValue(True)
        self.prgApp.SetValue(True)

    def _init_sizers(self):
        self.mainSizer = wx.BoxSizer(wx.VERTICAL)
        typeSizer = wx.BoxSizer(wx.HORIZONTAL)
        typeSizer.Add(wx.StaticText(self, wx.ID_ANY, _("disk :")), border=5,
                      flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL)
        typeSizer.Add(self.UriTypeChoice, border=5, flag=wx.ALIGN_CENTER_VERTICAL | wx.EXPAND | wx.ALL)
        self.mainSizer.Add(typeSizer, border=5, flag=wx.EXPAND | wx.ALL)

        optionSizer = wx.BoxSizer(wx.VERTICAL)
        optionSizer.Add(self.prgRte)
        optionSizer.Add(self.prgApp)
        self.mainSizer.Add(optionSizer, border=5, flag=wx.ALL)

        self.mainSizer.Add(self.editor_sizer, border=5, flag=wx.ALL)
        self.mainSizer.Add(self.LogConsole, border=5, flag=wx.EXPAND | wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, )
        buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        buttonSizer.Add(self.ButtonFlash, border=5,
                        flag=wx.BOTTOM | wx.ALIGN_CENTER_HORIZONTAL)
        buttonSizer.Add(self.ButtonSizer, border=5,
                        flag=wx.BOTTOM | wx.ALIGN_CENTER_HORIZONTAL)
        self.mainSizer.Add(buttonSizer, border=5, flag=wx.ALIGN_CENTER_HORIZONTAL | wx.ALL)
        self.SetSizer(self.mainSizer)
        self.Layout()
        self.Fit()

    def __init__(self, parent, ctr):
        wx.Dialog.__init__(self, name='UCopyEditor', parent=parent, title=_('Copy Firmware to UDisk'))
        self.ctr = ctr
        self.choices = []
        self._init_ctrls(parent)
        self._init_sizers()
        self.CenterOnParent()
        self.Log = LogPseudoFile(self.LogConsole, self.output)
        # self.Log = LogViewer(self.LogConsole, self)
        # self.LogConsole.SetLogSource(logging)
        self.verify = False

        # return
        self.CenterOnParent()
        self.tmr = wx.Timer(parent, -1)
        parent.Bind(wx.EVT_TIMER, self.onTmr, self.tmr)
        self.tmr.Start(1000)
        try:
            app_path = self.ctr.GetIECLibPath()
            progBase = os.path.abspath(os.path.join(app_path, '../../..', ))
            board = self.ctr.GetChildByName('board_0')
            if not board:
                dialog = wx.MessageDialog(parent, _('Can not Found "board_0",Please attach one board.'),
                                          style=wx.YES_DEFAULT | wx.CENTRE)
                dialog.ShowModal()
                wx.CallAfter(self.Close)
                return
            node = board.GetBoardFile()
            self.model = node['class'].custom_model or node['class'].model
            self.dev_id = node.get('dev_id', None)
            builder = self.ctr.GetBuilder()
            self.appBin = builder.GetBinaryPath()

            Board = board.BoardRoot.getBoard()[0]
            rte = Board.getFirmware()
            if not rte:
                dialog = wx.MessageDialog(parent, '未选择使用的RTE固件,请检查board配置.',
                                          style=wx.YES_DEFAULT | wx.CENTRE)
                dialog.ShowModal()
                wx.CallAfter(self.Close)
                return
            self.rtes = node.get('class').rtes
            for x in self.rtes.values():
                if x['name'] == rte:
                    self.rte = x
                    break
            self.rtebin = os.path.join(progBase, "firmware", self.rte.get('bin'))
            self.BlkRte = self.rte.get('blocks')
            self.BlkApp = self.rte.get('app_blocks')
            self.adrRte = self.rte['start']
            self.adrApp = self.rte.get('app_start')
            if not exists(self.rtebin):
                dialog = wx.MessageDialog(parent, _("Cannot Get Boot bin."), style=wx.YES_DEFAULT | wx.CENTRE)
                dialog.ShowModal()
                wx.CallAfter(self.Close)
            if not exists(self.appBin):
                dialog = wx.MessageDialog(parent, _("Cannot Get PLC Firmware.Please Exec Build."),
                                          style=wx.YES_DEFAULT | wx.CENTRE)
                dialog.ShowModal()
                wx.CallAfter(self.Close)
        except Exception as ex:
            print(traceback.print_exc())
            dialog = wx.MessageDialog(parent, str(ex), style=wx.YES_DEFAULT | wx.CENTRE)
            dialog.ShowModal()
            wx.CallAfter(self.Close)

    def onTmr(self, event):
        choices = usbpath()
        if choices != self.choices:
            self.choices = choices
            strList = [x[1] for x in choices]
            self.UriTypeChoice.SetItems(strList)
            if len(choices) == 1:
                self.UriTypeChoice.SetSelection(0)
        if self.UriTypeChoice.GetSelection() >= 0 and (self.prgApp.IsChecked() or self.prgRte.IsChecked()):
            self.ButtonFlash.Enable()
        else:
            self.ButtonFlash.Disable()
        event.Skip()

    def OnTypeChoice(self, event):
        index = event.GetSelection()
        self.udrive = self.choices[index]

    def flash(self, event):
        self.Log.flush()
        index = self.UriTypeChoice.GetSelection()
        udisk = self.choices[index][0]
        self.udrive = self.choices[index]
        self.Log.write(_('Copy firmware to UDisk %s') % udisk)
        rte = os.path.join(udisk, 'rte.bin')
        if self.prgRte.IsChecked():
            shutil.copy(self.rtebin, rte)
            self.Log.write('RTE固件已复制.')
        elif exists(rte):
            os.remove(rte)
            self.Log.write('从U盘删除了RTE固件.')

        app = os.path.join(udisk, 'plc.bin')
        if self.prgApp.IsChecked():
            shutil.copy(self.appBin, app)
            self.Log.write('PLC程序已复制.')
        elif exists(app):
            os.remove(app)
            self.Log.write('从U盘删除了PLC程序.')
        self.Log.write('复制完成.')

    def output(self, txt):
        pass
        # self.LogConsole.AppendText(txt)
