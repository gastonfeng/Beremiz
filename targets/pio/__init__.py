# !/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz, a Integrated Development Environment for
# programming IEC 61131-3 automates supporting plcopen standard and CanFestival.
#
# Copyright (C) 2007: Edouard TISSERANT and Laurent BESSARD
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

from targets.toolchain_pio import toolchain_pio

extra_flag = {'USE_NTPClient': ['LWIP_DNS']}


class stdout:
    def __init__(self, logger):
        self.logger = logger

    def write(self, txt):
        self.logger.write(txt)

    def closed(self):
        pass


class stderr:
    def __init__(self, logger):
        self.logger = logger

    def write(self, txt):
        self.logger.write_error(txt)

    def closed(self):
        pass


class pio_target(toolchain_pio):
    dlopen_prefix = ""
    extension = '.bin'
    platform_static = 'ststm32@10.0.73'
    platform_dev = 'https://gitee.com/kaikong/platform-ststm32.git#kaikong'
    exe = 'firmware.bin'
    build_flags = []
    static = True

    def getBoard(self):
        boardNode = self.CTRInstance.GetChildByName('board_0')
        if not boardNode:
            self.CTRInstance.logger.write_error(_('Can not Found "board_0",Please attach one board.'))
            return False
        board = boardNode.BoardRoot.getBoard()[0]
        rte = board.getFirmware()
        if not rte:
            raise Exception(_('Please select one Firmware.'))
        node = boardNode.GetBoardFile()
        board = node['class']
        self.model = board.model
        self.board = 'board = %s' % node['class'].board
        self.upload_protocol = node['class'].upload_protocol
        self.framework = ""
        rtes = board.rtes
        self.rte = rtes[rte]
        self.build_flags += node['class'].LDFLAGS + self.rte.get('LDFLAGS') or []
        self.libs = self.rte.get('lib') or []
        self.lib_other = node.get('lib_other') or []
        self.options = self.rte.get('options') or []
        if self.rte.get('bin'):
            self.mode = 'APP'
        else:
            self.mode = 'PLC'
        if self.rte.get('framework'):
            self.framework = 'framework = %s' % self.rte.get('framework')

    def findObject(self, paths, test):
        path = None
        for p in paths:
            if test(p):
                path = p
                break
        return path

    def getPlatform(self):
        if self.static:
            return self.platform_static
        else:
            return self.platform_dev
