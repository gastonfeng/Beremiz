#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz, a Integrated Development Environment for
# programming IEC 61131-3 automates supporting plcopen standard and CanFestival.
#
# Copyright (C) 2016 - 2017: Andrey Skvortsov <andrej.skvortzov@gmail.com>
#
# See COPYING file for copyrights details.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.


import getopt
import os
import sys
from asyncio.events import get_event_loop

import wx
from past.builtins import execfile
from wx.lib.agw.advancedsplash import AdvancedSplash, AS_NOTIMEOUT, AS_CENTER_ON_SCREEN

from BeremizIDE import Beremiz
from oem import oem
from wxasync.src.wxasync import WxAsyncApp, StartCoroutine

sys.path.append('.')

from APPVersion import appversion, appchannel
from alpha import alpha_test
from util import paths


class BeremizIDELauncher(object):
    def __init__(self):
        self.app = None
        self.frame = None
        self.updateinfo_url = None
        self.extensions = []
        self.app_dir = paths.AbsDir(__file__)
        if hasattr(sys, 'frozen'):
            self.app_dir = os.path.join(self.app_dir, '..')
        self.projectOpen = None
        self.buildpath = None
        self.splash = None
        self.splashPath = self.Bpath("images", oem.logo)
        self.modules = ["BeremizIDE"]
        self.debug = os.path.exists("BEREMIZ_DEBUG")
        self.handle_exception = None
        self.test = False

    def Bpath(self, *args):
        return os.path.join(self.app_dir, *args)

    def Usage(self):
        print("Usage:")
        print("%s [Options] [Projectpath] [Buildpath]" % sys.argv[0])
        print("")
        print("Supported options:")
        print("-h --help                    Print this help")
        print("-u --updatecheck URL         Retrieve update information by checking URL")
        print("-e --extend PathToExtension  Extend IDE functionality by loading at start additional extensions")
        print("")
        print("")

    def SetCmdOptions(self):
        self.shortCmdOpts = "htu:e:"
        self.longCmdOpts = ["help", "test", "updatecheck=", "extend="]

    def ProcessOption(self, o, a):
        if o in ("-h", "--help"):
            self.Usage()
            sys.exit()
        if o in ("-u", "--updatecheck"):
            self.updateinfo_url = a
        if o in ("-e", "--extend"):
            self.extensions.append(a)
        if o in ("-t", "--test"):
            self.test = True

    def ProcessCommandLineArgs(self):
        self.SetCmdOptions()
        try:
            opts, args = getopt.getopt(sys.argv[1:], self.shortCmdOpts, self.longCmdOpts)
        except getopt.GetoptError:
            # print help information and exit:
            self.Usage()
            sys.exit(2)

        for o, a in opts:
            self.ProcessOption(o, a)

        if len(args) > 2:
            self.Usage()
            sys.exit()

        elif len(args) == 1:
            self.projectOpen = args[0]
            self.buildpath = None
        elif len(args) == 2:
            self.projectOpen = args[0]
            self.buildpath = args[1]

    def CreateApplication(self):

        class BeremizApp(WxAsyncApp):
            def OnInit(_self):  # pylint: disable=no-self-argument
                self.ShowSplashScreen()
                return True

        self.app = BeremizApp()
        self.app.SetAppName(oem.title)

    @alpha_test
    def ShowSplashScreen(self):
        class Splash(AdvancedSplash):
            Painted = False

            def OnPaint(_self, event):  # pylint: disable=no-self-argument
                AdvancedSplash.OnPaint(_self, event)
                if not _self.Painted:  # trigger app start only once
                    _self.Painted = True
                    wx.CallAfter(self.AppStart)

        bmp = wx.Image(self.splashPath).ConvertToBitmap()
        self.splash = Splash(None, bitmap=bmp, agwStyle=AS_NOTIMEOUT | AS_CENTER_ON_SCREEN)

    def BackgroundInitialization(self):
        self.InitI18n()
        # self.CheckUpdates()
        self.LoadExtensions()
        # self.ImportModules()
        # if appchannel == 'alpha':
        #     self.alpha = alphaView()

    def InitI18n(self):
        from util.misc import InstallLocalRessources
        InstallLocalRessources(self.app_dir)

    def globals(self):
        """
        allows customizations to specify what globals
        are passed to extensions
        """
        return globals()

    def LoadExtensions(self):
        for extfilename in self.extensions:
            from util.TranslationCatalogs import AddCatalog
            from util.BitmapLibrary import AddBitmapFolder
            extension_folder = os.path.split(os.path.realpath(extfilename))[0]
            sys.path.append(extension_folder)
            AddCatalog(os.path.join(extension_folder, "locale"))
            AddBitmapFolder(os.path.join(extension_folder, "images"))
            execfile(extfilename, self.globals())

    def CheckUpdates(self):
        if self.updateinfo_url is not None:
            self.updateinfo = _("Fetching %s") % self.updateinfo_url

            def updateinfoproc():
                try:
                    import urllib2
                    self.updateinfo = urllib2.urlopen(self.updateinfo_url, None).read()
                except Exception:
                    self.updateinfo = _("update info unavailable.")

            from threading import Thread
            self.splash.SetText(text=self.updateinfo)
            updateinfoThread = Thread(target=updateinfoproc, name='updateinfoproc')
            updateinfoThread.start()
            updateinfoThread.join(2)
            self.splash.SetText(text=self.updateinfo)

    def ImportModules(self):
        for modname in self.modules:
            mod = __import__(modname)
            setattr(self, modname, mod)

    def InstallExceptionHandler(self):
        import util.ExceptionHandler
        self.handle_exception = util.ExceptionHandler.AddExceptHook(appversion)

    def CreateUI(self):
        self.frame = Beremiz(self.app, self.projectOpen, self.buildpath)
        self.app.SetTopWindow(self.frame)

    def CloseSplash(self):
        if self.splash:
            self.splash.Close()

    def ShowUI(self):
        self.frame.Show()

    def PreStart(self):
        self.ProcessCommandLineArgs()
        self.CreateApplication()

    def AppStart(self):
        self.BackgroundInitialization()
        self.CreateUI()
        self.CloseSplash()
        self.ShowUI()
        if self.test:
            StartCoroutine(self.frame.test, self.frame)
            self.app.ExitMainLoop()

    def MainLoop(self):
        import sys
        if '--inspect' in sys.argv:
            import wx.lib.inspection
            wx.lib.inspection.InspectionTool().Show()
        loop = get_event_loop()
        loop.run_until_complete(self.app.MainLoop())
        # if appchannel == 'alpha':
        #     self.alpha.shutdown()

    def Start(self):
        self.PreStart()
        if appchannel != 'alpha':
            self.InstallExceptionHandler()
        self.MainLoop()


if __name__ == '__main__':
    beremiz = BeremizIDELauncher()
    beremiz.Start()
