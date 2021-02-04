#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This file is part of Beremiz.
# See COPYING file for copyrights details.


import os

from XSLTransform import XSLTransform
from plcopen.structures import StdBlckLibs
from util import paths

ScriptDirectory = paths.AbsDir(__file__)


class XSLTModelQuery(XSLTransform):
    """ a class to handle XSLT queries on project and libs """
    def __init__(self, controller, xsltpath, ext=None):
        # arbitrary set debug to false, updated later
        self.debug = False

        # merge xslt extensions for library access to query specific ones
        xsltext = [
            ("GetProject", lambda *_ignored:
             [controller.GetProject(self.debug)]),
            ("GetStdLibs", lambda *_ignored:
            [lib for lib in list(StdBlckLibs.values())]),
            ("GetExtensions", lambda *_ignored:
             [ctn["types"] for ctn in controller.ConfNodeTypes])
        ]

        if ext is not None:
            xsltext.extend(ext)

        # parse and compile. "beremiz" arbitrary namespace for extensions
        XSLTransform.__init__(self,
                              os.path.join(ScriptDirectory, xsltpath),
                              xsltext)

    def _process_xslt(self, root, debug, **kwargs):
        self.debug = debug
        return self.transform(root, **kwargs)
        # print(self.xslt.error_log)


# -------------------------------------------------------------------------------
#           Helpers functions for translating list of arguments
#                       from xslt to valid arguments
# -------------------------------------------------------------------------------


def _StringValue(x):
    return x


def _BoolValue(x):
    return x in ["true", "0"]


def _translate_args(translations, args):
    return [translate(arg[0]) if len(arg) > 0 else None
            for translate, arg in
            list(zip(translations, args))]
