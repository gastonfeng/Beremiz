#!/usr/bin/env python
# -*- coding: utf-8 -*-

#This file is part of PLCOpenEditor, a library implementing an IEC 61131-3 editor
#based on the plcopen standard. 
#
#Copyright (C) 2013: Edouard TISSERANT and Laurent BESSARD
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

import wx

from plcopen.structures import TestIdentifier, IEC_KEYWORDS
from graphics.GraphicCommons import FREEDRAWING_MODE

#-------------------------------------------------------------------------------
#                    Dialog with preview for graphic block
#-------------------------------------------------------------------------------

"""
Class that implements a generic dialog containing a preview panel for displaying
graphic created by dialog
"""

class BlockPreviewDialog(wx.Dialog):

    def __init__(self, parent, controller, tagname, size, title):
        """
        Constructor
        @param parent: Parent wx.Window of dialog for modal
        @param controller: Reference to project controller
        @param tagname: Tagname of project POU edited
        @param size: wx.Size object containing size of dialog
        @param title: Title of dialog frame
        """
        wx.Dialog.__init__(self, parent, size=size, title=title)
        
        # Save reference to
        self.Controller = controller
        self.TagName = tagname
        
        # Label for preview
        self.PreviewLabel = wx.StaticText(self, label=_('Preview:'))
        
        # Create Preview panel
        self.Preview = wx.Panel(self, style=wx.SIMPLE_BORDER)
        self.Preview.SetBackgroundColour(wx.WHITE)
        
        # Add function to preview panel so that it answers to graphic elements
        # like Viewer
        setattr(self.Preview, "GetDrawingMode", lambda:FREEDRAWING_MODE)
        setattr(self.Preview, "GetScaling", lambda:None)
        setattr(self.Preview, "GetBlockType", controller.GetBlockType)
        setattr(self.Preview, "IsOfType", controller.IsOfType)
        
        # Bind paint event on Preview panel
        self.Preview.Bind(wx.EVT_PAINT, self.OnPaint)
        
        # Add default dialog buttons sizer
        self.ButtonSizer = self.CreateButtonSizer(wx.OK|wx.CANCEL|wx.CENTRE)
        self.Bind(wx.EVT_BUTTON, self.OnOK, 
                  self.ButtonSizer.GetAffirmativeButton())
        
        self.Element = None            # Graphic element to display in preview
        self.MinElementSize = None     # Graphic element minimal size
        
        # Variable containing the graphic element name when dialog is opened
        self.DefaultElementName = None
        
    def __del__(self):
        """
        Destructor
        """
        # Remove reference to project controller
        self.Controller = None
    
    def SetMinElementSize(self, size):
        """
        Define minimal graphic element size
        @param size: Tuple containing minimal size (width, height)
        """
        self.MinElementSize = size
    
    def SetPreviewFont(self, font):
        """
        Set font of Preview panel
        @param font: wx.Font object containing font style
        """
        self.Preview.SetFont(font)
    
    def TestElementName(self, element_name):
        """
        Test displayed graphic element name
        @param element_name: Graphic element name
        """
        # Variable containing error message format
        message_format = None
        # Get graphic element name in upper case
        uppercase_element_name = element_name.upper()
        
        # Test if graphic element name is a valid identifier
        if not TestIdentifier(element_name):
            message_format = _("\"%s\" is not a valid identifier!")
        
        # Test that graphic element name isn't a keyword
        elif uppercase_element_name in IEC_KEYWORDS:
            message_format = _("\"%s\" is a keyword. It can't be used!")
        
        # Test that graphic element name isn't a POU name
        elif uppercase_element_name in self.Controller.GetProjectPouNames():
            message_format = _("\"%s\" pou already exists!")
        
        # Test that graphic element name isn't already used in POU by a variable
        # or another graphic element
        elif ((self.DefaultElementName is None or 
               self.DefaultElementName.upper() != uppercase_element_name) and 
              uppercase_element_name in self.Controller.\
                    GetEditedElementVariables(self.TagName)):
            message_format = _("\"%s\" element for this pou already exists!")
        
        # If an error have been identify, show error message dialog
        if message_format is not None:
            self.ShowErrorMessage(message_format % element_name)
            # Test failed
            return False
        
        # Test succeed
        return True
    
    def ShowErrorMessage(self, message):
        """
        Show an error message dialog over this dialog
        @param message: Error message to display
        """
        dialog = wx.MessageDialog(self, message, 
                                  _("Error"), 
                                  wx.OK|wx.ICON_ERROR)
        dialog.ShowModal()
        dialog.Destroy()
    
    def OnOK(self, event):
        """
        Called when dialog OK button is pressed
        Need to be overridden by inherited classes to check that dialog values
        are valid
        @param event: wx.Event from OK button
        """
        # Close dialog
        self.EndModal(wx.ID_OK)
    
    def RefreshPreview(self):
        """
        Refresh preview panel of graphic element
        May be overridden by inherited classes
        """
        # Init preview panel paint device context
        dc = wx.ClientDC(self.Preview)
        dc.SetFont(self.Preview.GetFont())
        dc.Clear()
        
        # Return immediately if no graphic element defined
        if self.Element is None:
            return
        
        # Calculate block size according to graphic element min size due to its
        # parameters and graphic element min size defined
        min_width, min_height = self.Element.GetMinSize()
        width = max(self.MinElementSize[0], min_width)
        height = max(self.MinElementSize[1], min_height)
        self.Element.SetSize(width, height)
        
        # Get Preview panel size
        client_size = self.Preview.GetClientSize()
        
        # If graphic element is too big to be displayed in preview panel,
        # calculate preview panel scale so that graphic element fit inside
        scale = (max(float(width) / client_size.width, 
                     float(height) / client_size.height) * 1.2
                 if width * 1.2 > client_size.width or 
                    height * 1.2 > client_size.height
                 else 1.0)
        dc.SetUserScale(1.0 / scale, 1.0 / scale)
        
        # Center graphic element in preview panel
        x = int(client_size.width * scale - width) / 2
        y = int(client_size.height * scale - height) / 2
        self.Element.SetPosition(x, y)
        
        # Draw graphic element
        self.Element.Draw(dc)
    
    def OnPaint(self, event):
        """
        Called when Preview panel need to be redraw
        @param event: wx.PaintEvent
        """
        self.RefreshPreview()
        event.Skip()
        