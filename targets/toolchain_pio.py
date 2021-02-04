#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz, a Integrated Development Environment for
# programming IEC 61131-3 automates supporting plcopen standard and CanFestival.
#
# Copyright (C) 2007: Edouard TISSERANT and Laurent BESSARD
# Copyright (C) 2017: Paul Beltyukov
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


import hashlib
import json
import operator
import os
import re
import shutil
import sys
import traceback
from functools import reduce
from os.path import exists

from jinja2 import Environment, FileSystemLoader
from pypinyin import lazy_pinyin

from APPVersion import appchannel
from targets.packageManger import package_get
from util import paths
from util.ProcessLogger import ProcessLogger

includes_re = re.compile(r'\s*#include\s*["<]([^">]*)[">].*')
sys.path.append(os.path.dirname(sys.executable))
extra_flag = {'USE_NTPClient': ['LWIP_DNS']}
staticPackage = ['STM32Ethernet', 'modbus', 'NTPClient', "LwIP", "SPIFlash", "ShiftRegister74HC595", "Rtc_Pcf8563",
                 "Q2-HX711-Arduino-Library", "pt100rtd", "pt100_hx711", "MCPDAC", "littlefs", "FatFs", "debouncer",
                 "ch423", "STM32FreeRTOS", "USBStick_stm32", "STM32_USB_Host_Library", "ad7689", 'ArduinoJson',
                 'msgpack-arduino', 'ArduinoHttpClient']


class toolchain_pio(object):
    """
    This abstract class contains GCC specific code.
    It cannot be used as this and should be inherited in a target specific
    class such as target_linux or target_win32
    """
    mode = None
    libs = []
    lib_other = []

    def __init__(self, CTRInstance):
        self.CTRInstance = CTRInstance
        self.prjpath = self.CTRInstance.GetProjectPath()
        app_path = self.CTRInstance.GetIECLibPath()
        self.app_path = os.path.abspath(os.path.join(app_path, '../../..', ))
        self.buildpath = None
        self.SetBuildPath(self.CTRInstance._getBuildPath())
        self.upload_protocol = None
        self.options = []
        self.deps = []
        self.build_flags = []

    def getBuilderCFLAGS(self):
        """
        Returns list of builder specific CFLAGS
        """
        return [self.CTRInstance.GetTarget().getcontent().getCFLAGS()]

    def getBuilderLDFLAGS(self):
        """
        Returns list of builder specific LDFLAGS
        """
        return self.CTRInstance.LDFLAGS + \
               [self.CTRInstance.GetTarget().getcontent().getLDFLAGS()]

    def getCompiler(self):
        """
        Returns compiler
        """
        return self.CTRInstance.GetTarget().getcontent().getCompiler()

    def getLinker(self):
        """
        Returns linker
        """
        return self.CTRInstance.GetTarget().getcontent().getLinker()

    def GetBinaryPath(self):
        return self.exe_path

    def GetBinaryCode(self):
        try:
            return open(self.exe_path, "rb").read()
        except Exception:
            return None

    def _GetMD5FileName(self):
        return os.path.join(self.prjpath, "lastbuildPLC.md5")

    def ResetBinaryCodeMD5(self):
        try:
            os.remove(self._GetMD5FileName())
        except Exception:
            pass

    def GetBinaryCodeMD5(self):
        try:
            return open(self._GetMD5FileName(), "r").read()
        except Exception:
            return None

    def SetBuildPath(self, buildpath):
        if self.buildpath != buildpath:
            self.buildpath = buildpath
            # self.exe = self.CTRInstance.GetProjectName() + self.extension
            self.exe_path = os.path.join(self.prjpath, '.pio', 'build', 'plcapp', self.exe)
            self.srcmd5 = {}

    def append_cfile_deps(self, src, deps):
        for l in src.splitlines():
            res = includes_re.match(l)
            if res is not None:
                depfn = res.groups()[0]
                if os.path.exists(os.path.join(self.buildpath, depfn)):
                    if depfn not in self.deps:
                        self.deps.append(depfn)

    def concat_deps(self, bn):
        # read source
        src = open(os.path.join(self.buildpath, bn), "r", encoding='utf-8', errors='ignore').read()
        # update direct dependencies
        self.append_cfile_deps(src, self.deps)
        # recurse through deps
        # TODO detect cicular deps.
        if bn in self.deps:
            return src
        return reduce(operator.concat, list(map(self.concat_deps, self.deps)), src)

    def check_and_update_hash_and_deps(self, bn):
        # Get latest computed hash and deps
        oldhash, self.deps = self.srcmd5.get(bn, (None, []))
        # read source
        src = open(os.path.join(self.buildpath, bn), encoding='utf-8', errors='ignore').read()
        # compute new hash
        newhash = hashlib.md5(src.encode()).hexdigest()
        # compare
        match = (oldhash == newhash)
        if not match:
            # file have changed
            # update direct dependencies
            self.append_cfile_deps(src, self.deps)
            # store that hashand deps
            self.srcmd5[bn] = (newhash, self.deps)
        # recurse through deps
        # TODO detect cicular deps.
        # return reduce(operator.and_, list(map(self.check_and_update_hash_and_deps, deps)), match)
        return match

    def calc_source_md5(self):
        wholesrcdata = ""
        for _Location, CFilesAndCFLAGS, _DoCalls in self.CTRInstance.LocationCFilesAndCFLAGS:
            # Get CFiles list to give it to makefile
            for CFile, _CFLAGS in CFilesAndCFLAGS:
                CFileName = os.path.basename(CFile)
                wholesrcdata += self.concat_deps(CFileName)
        return hashlib.md5(wholesrcdata.encode()).hexdigest()

    def calc_md5(self):
        return hashlib.md5(self.GetBinaryCode()).hexdigest()

    async def build(self):
        res = False
        gitPath = os.path.join(self.app_path, 'tool', 'Git', 'cmd')
        os.environ['PATH'] += ';' + gitPath
        if exists(os.path.join(gitPath, 'git.exe')):
            self.CTRInstance.logger.write("git path:%s\n" % gitPath)
        else:
            self.CTRInstance.logger.write_error("git not found:%s\n" % gitPath)
            return res
        old_path = os.getcwd()
        os.chdir(self.prjpath)
        try:
            f = 'src/POUS.cpp'
            if exists(f):
                os.remove(f)
            md5key = self.calc_source_md5()
            # 生成platformio.ini
            self.getBoard()

            appname = self.CTRInstance.GetProject().getcontentHeader()
            appname = lazy_pinyin(appname['projectName'])
            appname = ''.join(appname)
            appname = appname.replace(" ", "")
            build_flags = self.build_flags + self.CTRInstance.LDFLAGS + ['-D SWNAME=\\"%s\\"' % appname,
                                                                         '-DPLC_MD5=%s' % md5key]

            config = self.CTRInstance.GetTarget().getcontent()
            attrib = {}
            optimization = True
            for key, value in config.attrib.items():
                if value == 'false':
                    attrib[key] = False
                elif value == 'true':
                    attrib[key] = True
                else:
                    attrib[key] = value
                if key == 'STATIC': self.static = attrib[key]
                if key == 'optimization': optimization = attrib[key]
            libs = self.libs + self.CTRInstance.Libs
            if self.mode == 'APP' and 'modbus' in libs:
                libs.remove('modbus')
            # 检查
            # if 'IP' not in attrib:
            #     raise Exception(_("Please input default ip!"))

            def_dict = {'LOCAL_PACKAGE': True if appchannel != 'alpha' else False, 'ONLINE_DEBUG': True}
            def_dict.update(attrib)

            packages = package_get(self.CTRInstance.logger, def_dict, libs, staticPackage if self.static else [],
                                   self.app_path)
            package_all = package_get(self.CTRInstance.logger, def_dict, libs + self.lib_other, [], self.app_path)
            platform = self.getPlatform()
            for att in def_dict:
                val = def_dict[att]
                if val:
                    build_flags.append('-D %s' % att)
                    extra = extra_flag.get(att) or []
                    for e in extra:
                        build_flags.append('-D %s' % e)
            build_flags = list(set(build_flags))

            self.platformio_ini(platform, self.framework, self.board, build_flags, package_prog=packages,
                                package_test=package_all, upload_protocol=self.upload_protocol, options=self.options)

            # shutil.copy(os.path.join(self.app_path, 'rtconfig.h'), 'src/rtconfig.h')
            # shutil.copy(os.path.join(self.app_path, 'rtconfig_cm3.h'), 'src/rtconfig_cm3.h')
            # shutil.copy(os.path.join(self.app_path, 'rtconfig_stm32.h'), 'src/rtconfig_stm32.h')
            # if not exists('src/spiffs_config.h'):
            #     shutil.copy(os.path.join(self.app_path, 'spiffs_config.h'), 'src/spiffs_config.h')
            shutil.copy(os.path.join(os.path.dirname(__file__), 'extra_script.py'), 'extra_script.py')
            # shutil.copy(os.path.join(self.app_path, 'tool', 'makefsdata.exe'), 'makefsdata.exe')
            # shutil.copy(os.path.join(self.app_path, 'tool', 'msvcr100d.dll'), 'msvcr100d.dll')

            # 输出buildnumer
            json_build = 'build.json'
            if exists(json_build):
                with open(json_build, 'r', encoding='utf-8') as f:
                    build = json.load(f)
                    build['build'] += 1
                    # if build.get('platform') != platform:
                    #     build['platform'] = platform
                    #     self.CTRInstance.logger.write(_("Platform Changed . Clean Project ... \n"))
                    # os.system("runas /user:Administrator rd /s /q src")
                    os.system("rd /s /q .pio")
                with open(json_build, 'w', encoding='utf-8') as f:
                    json.dump(build, f)
            else:
                build = {'build': 1}
                with open(json_build, 'w', encoding='utf-8') as f:
                    json.dump(build, f)
            buildnumber_c = "src/buildnumber.c"
            f = open(buildnumber_c, "w+")
            f.write("const unsigned short build_number=%d;" % build['build'])
            f.close()
            # f = 'src/LOGGER.c'
            # if exists(f):
            #     os.remove(f)
            # self.CTRInstance.logger.write(_("update Compiler Env ... \n"))
            # status, _result, _err_result = ProcessLogger(self.CTRInstance.logger, "pio --version", no_gui=False, ).spin()
            # status, _result, _err_result = ProcessLogger(self.CTRInstance.logger, "pio update", no_gui=False, ).spin()
            # status, _result, _err_result = ProcessLogger(self.CTRInstance.logger, "pio lib update", no_gui=False, ).spin()
            # if status:
            #     self.CTRInstance.logger.write_error(_("update  failed.\n"))
            #     os.chdir(old_path)
            #     return False
            self.CTRInstance.logger.write(_("Compiling ... \n"))
            cmd = 'pio.exe'
            application_path = os.path.dirname(sys.executable)
            pio_paths = [
                os.path.join(self.app_path, 'Python36', 'Scripts'),
                os.path.join(application_path, 'Scripts')
            ]
            pio = self.findObject(
                pio_paths, lambda p: os.path.isfile(os.path.join(p, cmd)))
            # if hasattr(sys, "frozen"):
            #     cmdd = "%s/Python36/python.exe %s/%s run --disable-auto-clean" % (
            #         mt.replace('\\', '/'), pio.replace('\\', '/'), cmd)
            # else:
            if optimization:
                cmdd = "%s/%s run --disable-auto-clean" % (pio.replace('\\', '/'), cmd)
            else:
                cmdd = "%s/%s debug --disable-auto-clean" % (pio.replace('\\', '/'), cmd)
            cmdd = cmdd.replace('/', '\\')
            self.CTRInstance.logger.write(cmdd)
            status, _result, _err_result = ProcessLogger(self.CTRInstance.logger, cmdd, no_gui=True, ).spin()
            if status:
                self.CTRInstance.logger.write_error(_("C compilation  failed.\n"))
                os.chdir(old_path)
            f = open(self._GetMD5FileName(), "w", encoding='utf-8')
            f.write(md5key)
            f.close()
            res = True
        except Exception as e:
            print(traceback.format_exc())
            self.CTRInstance.logger.write_error(_("C Build failed.\n"))
        os.chdir(old_path)
        return res

    def findObject(self, paths, test):
        path = None
        for p in paths:
            if test(p):
                path = p
                break
        return path

    def platformio_ini(self, platform, framework, board, build_flags, package_prog, package_test,
                       upload_protocol=None, options=[]):
        env = Environment(loader=FileSystemLoader(searchpath=paths.AbsDir(__file__)))
        ps = env.get_template("platformio.ini")
        txt = ps.render(platform=platform, framework=framework, model=board,
                        lib_path=os.path.join(self.app_path, 'lib'),
                        core_dir=os.path.join(self.app_path, '.platformio'),
                        library_dir=os.path.join(self.app_path, 'library'), build_flags=build_flags,
                        package_prog=package_prog, package_test=package_test,
                        upload_protocol=upload_protocol, options=options)
        overwrite = True
        if exists('platformio.ini'):
            with open('platformio.ini', 'r') as output:
                t = output.read()
                if t == txt:
                    overwrite = False
        if overwrite:
            with open('platformio.ini', 'w') as output:
                output.write(txt)
            self.CTRInstance.logger.write(_("reBuild config File.\n"))
        else:
            self.CTRInstance.logger.write(_("config File no change.\n"))

    def _GetProgFlagFileName(self):
        app_path = os.getcwd()
        mt = os.path.abspath(os.path.join(app_path, 'prog.flag', ))
        return mt
