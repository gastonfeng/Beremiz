import os
import threading
import traceback
from os.path import exists

import wx
from pyocd.core.helpers import ConnectHelper
from pyocd.flash.file_programmer import FileProgrammer
from serial.tools import list_ports

from LogPseudoFile import LogPseudoFile
from controls import CustomStyledTextCtrl
from controls.DiscoveryPanel import DiscoveryPanel
from stm32bl.stm32bl_net import stm32bl_net
from stm32bl.stm32bls import Stm32bl, SerialException

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


class ProgEditor(wx.Dialog):
    def _init_ctrls(self, parent):
        self.UriTypeChoice = wx.Choice(parent=self, choices=self.choices)
        self.UriTypeChoice.SetSelection(0)
        self.Bind(wx.EVT_CHOICE, self.OnTypeChoice, self.UriTypeChoice)
        self.editor_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.scheme_editor = None
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

        self.ButtonFlash = wx.Button(self, -1, 'Flash')
        self.ButtonFlash.Bind(wx.EVT_BUTTON, self.flash)
        self.prgBoot = wx.CheckBox(self, label=_("prog Bootloader"))
        self.prgRte = wx.CheckBox(self, label=_("prog Runtime Firmware"))
        self.prgApp = wx.CheckBox(self, label=_("prog PLC APP"))
        self.prgApp.SetValue(True)
        self.prgBoot.SetValue(True)
        self.prgRte.SetValue(True)

    def _init_sizers(self):
        self.mainSizer = wx.BoxSizer(wx.VERTICAL)
        typeSizer = wx.BoxSizer(wx.HORIZONTAL)
        typeSizer.Add(wx.StaticText(self, wx.ID_ANY, _("Scheme :")), border=5,
                      flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL)
        typeSizer.Add(self.UriTypeChoice, border=5, flag=wx.ALL)
        self.mainSizer.Add(typeSizer)

        optionSizer = wx.BoxSizer(wx.VERTICAL)
        optionSizer.Add(self.prgBoot)
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
        self.ctr = ctr
        prjBase = self.ctr.GetProjectPath()

        wx.Dialog.__init__(self,
                           name='ProgEditor', parent=parent,
                           title=_('Prog with Serial'))
        ports = [d.product_name for d in ConnectHelper.get_all_connected_probes(blocking=False)] + [d.device for d in
                                                                                                    list_ports.comports()]

        self.choices = ports + [_('ESP-Link')]
        self._init_ctrls(parent)
        self._init_sizers()
        self.CenterOnParent()
        self.Log = LogPseudoFile(self.LogConsole, self.output)
        # self.Log = LogViewer(self.LogConsole, self)
        # self.LogConsole.SetLogSource(logging)
        self.verify = False
        self.boot = 0
        self.reset = 1
        try:
            prjBase = self.ctr.GetProjectPath()
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
            model = node['class']
            self.rtes = node.get('class').rtes
            self.rtebin = None
            for x in self.rtes.values():
                if x['name'] == rte:
                    self.rte = x
                    break
            if self.rte.get('bin'):
                self.rtebin = os.path.join(progBase, "firmware", self.rte.get('bin'))
            self.BlkRte = self.rte.get('blocks')
            self.BlkApp = self.rte.get('app_blocks')
            self.adrRte = self.rte.get('start')
            self.adrApp = self.rte.get('app_start')
            self.BlkBoot = None
            bootloader = self.rte.get('bootloader')
            bootName = None
            self.boot = model.prog_boot
            self.reset = model.prog_reset
            if bootloader:
                self.BlkBoot = bootloader.get('blocks')
                bootName = bootloader.get('bin')
            else:
                self.prgBoot.SetValue(False)
                self.prgBoot.Hide()
            if bootName:
                self.bootbin = os.path.join(progBase, "firmware", bootName)
                if not exists(self.bootbin):
                    dialog = wx.MessageDialog(parent, _("Cannot Get Boot bin."), style=wx.YES_DEFAULT | wx.CENTRE)
                    dialog.ShowModal()
                    return
            if self.rtebin and not exists(self.rtebin):
                dialog = wx.MessageDialog(parent, _("Cannot Get Rte bin."), style=wx.YES_DEFAULT | wx.CENTRE)
                dialog.ShowModal()
                wx.CallAfter(self.Close)
            if not exists(self.appBin):
                dialog = wx.MessageDialog(parent, _("Cannot Get PLC Firmware.Please Exec Build."),
                                          style=wx.YES_DEFAULT | wx.CENTRE)
                dialog.ShowModal()
                wx.CallAfter(self.Close)
            if not self.rtebin:
                self.prgRte.SetValue(False)
                self.prgRte.Hide()
        except Exception as ex:
            print(traceback.print_exc())
            dialog = wx.MessageDialog(parent, str(ex), style=wx.YES_DEFAULT | wx.CENTRE)
            dialog.ShowModal()
            wx.CallAfter(self.Close)

    def close(self):
        if self.scheme_editor:
            self.scheme_editor.close()

    def OnTypeChoice(self, event):
        index = event.GetSelection()
        self._replaceSchemeEditor(event.GetString() if index > 0 else None)

    def _replaceSchemeEditor(self, scheme):
        self.scheme = scheme

        if scheme != 'ESP-Link' and self.scheme_editor:
            self.editor_sizer.Detach(self.scheme_editor)
            self.scheme_editor.close()
            self.scheme_editor.Destroy()
            self.scheme_editor = None
        elif scheme == 'ESP-Link' and not self.scheme_editor:
            # None is for searching local network
            self.scheme_editor = DiscoveryPanel(self, service_type='_%s._tcp.local.' % self.model)
            self.editor_sizer.Add(self.scheme_editor)
            self.scheme_editor.Refresh()
        self.editor_sizer.Layout()
        self.mainSizer.Layout()
        self.Fit()

    def flash(self, val):
        Serial = self.UriTypeChoice.GetString(self.UriTypeChoice.GetSelection())
        self.Log.flush()
        self.Log.write(_('Current Board Model :%s\n') % (self.model))

        if Serial == 'ESP-Link':
            location = self.scheme_editor.GetURI()
            # scheme, location = uri.split("://")
            ip, port = location.split(':')
            threading.Thread(target=self.netFlash, args=[ip], name='netFLash').start()
        elif Serial == 'STM32 STLink':
            threading.Thread(target=self.stlinkFlash, args=[], name="STLink").start()
        else:
            threading.Thread(target=self.serialFlash, args=[Serial, self.boot, self.reset], name='serialFlash').start()

    def netFlash(self, ip):
        self.Log.write(_('Flash PLC use Esp Link :%s\n') % (ip))
        try:
            stm = stm32bl_net(ip, logger=self.Log)
            if self.dev_id and stm._dev_id != self.dev_id:
                self.Log.write_error(_("MCU ID Don't Match!"))
                return
            stm.mass_erase()
            if self.bootbin:
                self.Log.write(_('Flash BootLoader ...'))
                stm.write_file(0x8000000, self.bootbin, verify=self.verify)
            self.Log.write(_('Flash firmware ...'))
            stm.write_file(self.adrApp, self.appBin, verify=self.verify)
            stm.exit_bootloader()
            self.Log.write(_('Flash end.'))
        except SerialException as ex:
            self.Log.write_error(str(ex))
        except Exception as e:
            self.Log.write_error(str(e))
            self.Log.write_error(_('Flash Failed.'))

    def serialFlash(self, com, boot, reset):
        self.Log.write(" Flash PLC use %s\n" % (com))
        try:
            stm = Stm32bl(com, logger=self.Log, Boot=boot, Reset=reset)
            if self.dev_id and stm._dev_id != self.dev_id:
                self.Log.write_error(_("MCU ID Don't Match!"))
                return
            # stm.mass_erase()
            if self.prgBoot.IsChecked():
                self.Log.write(_('Flash BootLoader ...'))
                stm.erase_blocks(self.BlkBoot)
                stm.write_file(0x8000000, self.bootbin, verify=self.verify)
            if self.prgRte.IsChecked():
                self.Log.write(_('Flash RTE firmware ...'))
                stm.erase_blocks(self.BlkRte)
                stm.write_file(self.adrRte, self.rtebin, verify=self.verify)
            if self.prgApp.IsChecked():
                self.Log.write(_('Flash PLC APP ...'))
                if len(self.BlkApp) > 128:
                    stm.erase_blocks(self.BlkApp[0:128])
                    self.BlkApp = self.BlkApp[128:]
                stm.erase_blocks(self.BlkApp)
                stm.write_file(self.adrApp, self.appBin, verify=self.verify)
            stm.exit_bootloader()
            self.Log.write(_('Flash end.'))
        except Exception as e:
            self.Log.write_error(_('Error:%s') % str(e))
            self.Log.write_error(_('Flash Failed.'))

    def stlinkFlash(self):
        self.Log.write(" Flash PLC use STLink\n")
        try:
            with ConnectHelper.session_with_chosen_probe() as session:
                target = session.target
                # todo:stlink read cpu id
                # if self.dev_id and stm._dev_id != self.dev_id:
                #     self.Log.write_error(_("MCU ID Don't Match!"))
                #     return
                if self.prgBoot.IsChecked():
                    self.Log.write(_('Flash BootLoader ...'))
                    with FileProgrammer(session, chip_erase='auto', smart_flash=True) as programmer:
                        programmer.program(self.bootbin, file_format='bin', base_address=0x8000000)
                if self.prgRte.IsChecked():
                    self.Log.write(_('Flash RTE firmware ...'))
                    with FileProgrammer(session, chip_erase='auto', smart_flash=True) as programmer:
                        programmer.program(self.rtebin, file_format='bin', base_address=self.adrRte)
                if self.prgApp.IsChecked():
                    self.Log.write(_('Flash PLC APP ...'))
                    with FileProgrammer(session, chip_erase='auto', smart_flash=True) as programmer:
                        programmer.program(self.appBin, file_format='bin', base_address=self.adrApp)
            self.Log.write(_('Flash end.'))
        except Exception as e:
            self.Log.write_error(_('Error:%s') % str(e))
            self.Log.write_error(_('Flash Failed.'))

    def output(self, txt):
        pass
        # self.LogConsole.AppendText(txt)
