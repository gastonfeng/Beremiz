
import wx

from subindextable import EditingPanel
from nodeeditortemplate import NodeEditorTemplate
from editors.ConfTreeNodeEditor import ConfTreeNodeEditor

[ID_SLAVEEDITORCONFNODEMENUNODEINFOS, ID_SLAVEEDITORCONFNODEMENUDS301PROFILE,
 ID_SLAVEEDITORCONFNODEMENUDS302PROFILE, ID_SLAVEEDITORCONFNODEMENUDSOTHERPROFILE,
 ID_SLAVEEDITORCONFNODEMENUADD, 
] = [wx.NewId() for _init_coll_ConfNodeMenu_Items in range(5)]

[ID_SLAVEEDITORADDMENUSDOSERVER, ID_SLAVEEDITORADDMENUSDOCLIENT,
 ID_SLAVEEDITORADDMENUPDOTRANSMIT, ID_SLAVEEDITORADDMENUPDORECEIVE,
 ID_SLAVEEDITORADDMENUMAPVARIABLE, ID_SLAVEEDITORADDMENUUSERTYPE,
] = [wx.NewId() for _init_coll_AddMenu_Items in range(6)]

class SlaveEditor(ConfTreeNodeEditor, NodeEditorTemplate):
    
    CONFNODEEDITOR_TABS = [
        (_("CANOpen slave"), "_create_SlaveNodeEditor")]
    
    def _create_SlaveNodeEditor(self, prnt):
        self.SlaveNodeEditor = EditingPanel(prnt, self, self.Controler, self.Editable)
        return self.SlaveNodeEditor
        
    def __init__(self, parent, controler, window, editable=True):
        self.Editable = editable
        ConfTreeNodeEditor.__init__(self, parent, controler, window)
        NodeEditorTemplate.__init__(self, controler, window, False)
    
    def __del__(self):
        self.Controler.OnCloseEditor(self)
    
    def GetConfNodeMenuItems(self):
        if self.Editable:
            add_menu = [(wx.ITEM_NORMAL, (_('SDO Server'), ID_SLAVEEDITORADDMENUSDOSERVER, '', self.OnAddSDOServerMenu)),
                        (wx.ITEM_NORMAL, (_('SDO Client'), ID_SLAVEEDITORADDMENUSDOCLIENT, '', self.OnAddSDOClientMenu)),
                        (wx.ITEM_NORMAL, (_('PDO Transmit'), ID_SLAVEEDITORADDMENUPDOTRANSMIT, '', self.OnAddPDOTransmitMenu)),
                        (wx.ITEM_NORMAL, (_('PDO Receive'), ID_SLAVEEDITORADDMENUPDORECEIVE, '', self.OnAddPDOReceiveMenu)),
                        (wx.ITEM_NORMAL, (_('Map Variable'), ID_SLAVEEDITORADDMENUMAPVARIABLE, '', self.OnAddMapVariableMenu)),
                        (wx.ITEM_NORMAL, (_('User Type'), ID_SLAVEEDITORADDMENUUSERTYPE, '', self.OnAddUserTypeMenu))]
            
            profile = self.Controler.GetCurrentProfileName()
            if profile not in ("None", "DS-301"):
                other_profile_text = _("%s Profile") % profile
                add_menu.append((wx.ITEM_SEPARATOR, None))
                for text, indexes in self.Manager.GetCurrentSpecificMenu():
                    add_menu.append((wx.ITEM_NORMAL, (text, wx.NewId(), '', self.GetProfileCallBack(text))))
            else:
                other_profile_text = _('Other Profile')
            
            return [(wx.ITEM_NORMAL, (_('DS-301 Profile'), ID_SLAVEEDITORCONFNODEMENUDS301PROFILE, '', self.OnCommunicationMenu)),
                    (wx.ITEM_NORMAL, (_('DS-302 Profile'), ID_SLAVEEDITORCONFNODEMENUDS302PROFILE, '', self.OnOtherCommunicationMenu)),
                    (wx.ITEM_NORMAL, (other_profile_text, ID_SLAVEEDITORCONFNODEMENUDSOTHERPROFILE, '', self.OnEditProfileMenu)),
                    (wx.ITEM_SEPARATOR, None),
                    (add_menu, (_('Add'), ID_SLAVEEDITORCONFNODEMENUADD))]
        return []
    
    def RefreshConfNodeMenu(self, confnode_menu):
        if self.Editable:
            confnode_menu.Enable(ID_SLAVEEDITORCONFNODEMENUDSOTHERPROFILE, False)

    def RefreshView(self):
        ConfTreeNodeEditor.RefreshView(self)
        self.SlaveNodeEditor.RefreshIndexList()

    def RefreshCurrentIndexList(self):
        self.RefreshView()
    
    def RefreshBufferState(self):
        self.ParentWindow.RefreshTitle()
        self.ParentWindow.RefreshFileMenu()
        self.ParentWindow.RefreshEditMenu()
        self.ParentWindow.RefreshPageTitles()

class MasterViewer(SlaveEditor):
    SHOW_PARAMS = False

    def __init__(self, parent, controler, window, tagname):
        SlaveEditor.__init__(self, parent, controler, window, False)
    
        self.TagName = tagname
    
    def GetTagName(self):
        return self.TagName
    
    def GetCurrentNodeId(self):
        return None
    
    def GetInstancePath(self):
        return self.Controler.CTNFullName() + ".generated_master"
    
    def GetTitle(self):
        return self.GetInstancePath()
        
    def IsViewing(self, tagname):
        return self.GetInstancePath() == tagname
