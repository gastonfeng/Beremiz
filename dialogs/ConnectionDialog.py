#!/usr/bin/env python
# -*- coding: utf-8 -*-

#This file is part of PLCOpenEditor, a library implementing an IEC 61131-3 editor
#based on the plcopen standard. 
#
#Copyright (C) 2007: Edouard TISSERANT and Laurent BESSARD
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

from graphics.GraphicCommons import CONNECTOR, CONTINUATION
from graphics.FBD_Objects import FBD_Connector
from BlockPreviewDialog import BlockPreviewDialog

#-------------------------------------------------------------------------------
#                       Set Connection Parameters Dialog
#-------------------------------------------------------------------------------

"""
Class that implements a dialog for defining parameters of a connection graphic
element
"""

class ConnectionDialog(BlockPreviewDialog):
    
    def __init__(self, parent, controller, tagname, apply_button=False):
        """
        Constructor
        @param parent: Parent wx.Window of dialog for modal
        @param controller: Reference to project controller
        @param tagname: Tagname of project POU edited
        @param apply_button: Enable button for applying connector modification
        to all connector having the same name in POU (default: False)
        """
        BlockPreviewDialog.__init__(self, parent, controller, tagname, 
              size=wx.Size(350, 220), title=_('Connection Properties'))
        
        # Init common sizers
        self._init_sizers(2, 0, 5, None, 2, 1)
        
        # Create label for connection type
        type_label = wx.StaticText(self, label=_('Type:'))
        self.LeftGridSizer.AddWindow(type_label, flag=wx.GROW)
        
        # Create radio buttons for selecting connection type
        self.TypeRadioButtons = {}
        first = True
        for type, label in [(CONNECTOR, _('Connector')),
                            (CONTINUATION, _('Continuation'))]:
            radio_button = wx.RadioButton(self, label=label, 
                  style=(wx.RB_GROUP if first else 0))
            radio_button.SetValue(first)
            self.Bind(wx.EVT_RADIOBUTTON, self.OnTypeChanged, radio_button)
            self.LeftGridSizer.AddWindow(radio_button, flag=wx.GROW)
            self.TypeRadioButtons[type] = radio_button
            first = False
        
        # Create label for connection name
        name_label = wx.StaticText(self, label=_('Name:'))
        self.LeftGridSizer.AddWindow(name_label, flag=wx.GROW)
        
        # Create text control for defining connection name
        self.ConnectionName = wx.TextCtrl(self)
        self.Bind(wx.EVT_TEXT, self.OnNameChanged, self.ConnectionName)
        self.LeftGridSizer.AddWindow(self.ConnectionName, flag=wx.GROW)
        
        # Add preview panel and associated label to sizers
        self.RightGridSizer.AddWindow(self.PreviewLabel, flag=wx.GROW)
        self.RightGridSizer.AddWindow(self.Preview, flag=wx.GROW)
        
        # Add buttons sizer to sizers
        self.MainSizer.AddSizer(self.ButtonSizer, border=20, 
              flag=wx.ALIGN_RIGHT|wx.BOTTOM|wx.LEFT|wx.RIGHT)
        
        # Add button for applying connection name modification to all connection
        # of POU
        if apply_button:
            self.ApplyToAllButton = wx.Button(self, label=_("Propagate Name"))
            self.ApplyToAllButton.SetToolTipString(
                _("Apply name modification to all continuations with the same name"))
            self.Bind(wx.EVT_BUTTON, self.OnApplyToAll, self.ApplyToAllButton)
            self.ButtonSizer.AddWindow(self.ApplyToAllButton, 
                    border=(3 if wx.Platform == '__WXMSW__' else 10),
                    flag=wx.LEFT)
        else:
            self.ConnectionName.ChangeValue(
                controller.GenerateNewName(
                        tagname, None, "Connection%d", 0))
        
        # Connector radio button is default control having keyboard focus
        self.TypeRadioButtons[CONNECTOR].SetFocus()
    
    def GetConnectionType(self):
        """
        Return type selected for connection
        @return: Type selected (CONNECTOR or CONTINUATION)
        """
        return (CONNECTOR
                if self.TypeRadioButtons[CONNECTOR].GetValue()
                else CONTINUATION)
    
    def SetValues(self, values):
        """
        Set default connection parameters
        @param values: Connection parameters values
        """
        # For each parameters defined, set corresponding control value
        for name, value in values.items():
            
            # Parameter is connection type
            if name == "type":
                self.TypeRadioButtons[value].SetValue(True)
            
            # Parameter is connection name
            elif name == "name":
                self.ConnectionName.SetValue(value)
        
        # Refresh preview panel
        self.RefreshPreview()
    
    def GetValues(self):
        """
        Return connection parameters defined in dialog
        @return: {parameter_name: parameter_value,...}
        """
        values = {
            "type": self.GetConnectionType(),
            "name": self.ConnectionName.GetValue()}
        values["width"], values["height"] = self.Element.GetSize()
        return values

    def TestConnectionName(self):
        """
        Test that connection name is valid
        @return: True if connection name is valid
        """
        message = None
        
        # Get connection name typed by user
        connection_name = self.ConnectionName.GetValue()
        
        # Test that a name have been defined
        if connection_name == "":
            message = _("Form isn't complete. Name must be filled!")
        
        # If an error have been identify, show error message dialog
        if message is not None:
            self.ShowErrorMessage(message)
            # Test failed
            return False
        
        # Return result of element name test
        return self.TestElementName(connection_name)
        
    def OnOK(self, event):
        """
        Called when dialog OK button is pressed
        Test if connection name is valid
        @param event: wx.Event from OK button
        """
        # Close dialog if connection name is valid
        if self.TestConnectionName():
            self.EndModal(wx.ID_OK)

    def OnApplyToAll(self, event):
        """
        Called when Apply To All button is pressed
        Test if connection name is valid
        @param event: wx.Event from OK button
        """
        # Close dialog if connection name is valid
        if self.TestConnectionName():
            self.EndModal(wx.ID_YESTOALL)

    def OnTypeChanged(self, event):
        """
        Called when connection type changed
        @param event: wx.RadioButtonEvent
        """
        self.RefreshPreview()
        event.Skip()

    def OnNameChanged(self, event):
        """
        Called when connection name value changed
        @param event: wx.TextEvent
        """
        self.RefreshPreview()
        event.Skip()
        
    def RefreshPreview(self):
        """
        Refresh preview panel of graphic element
        Override BlockPreviewDialog function
        """
        # Set graphic element displayed, creating a FBD connection element
        self.Element = FBD_Connector(self.Preview, 
                self.GetConnectionType(),
                self.ConnectionName.GetValue())
        
        # Call BlockPreviewDialog function
        BlockPreviewDialog.RefreshPreview(self)
        