"""
Beremiz Project Controller 
"""
import os,sys,traceback
import time
import features
import shutil
import wx
import re, tempfile
from types import ListType
from threading import Timer, Lock, Thread
from time import localtime
from datetime import datetime
from weakref import WeakKeyDictionary

import targets
import connectors
from util.misc import CheckPathPerm, GetClassImporter
from util.MiniTextControler import MiniTextControler
from util.ProcessLogger import ProcessLogger
from util.BitmapLibrary import GetBitmap
from editors.FileManagementPanel import FileManagementPanel
from editors.ProjectNodeEditor import ProjectNodeEditor
from editors.IECCodeViewer import IECCodeViewer
from editors.DebugViewer import DebugViewer
from dialogs import DiscoveryDialog
from PLCControler import PLCControler
from plcopen.structures import IEC_KEYWORDS
from targets.typemapping import DebugTypesSize, LogLevelsCount, LogLevels
from ConfigTreeNode import ConfigTreeNode

base_folder = os.path.split(sys.path[0])[0]

MATIEC_ERROR_MODEL = re.compile(".*\.st:(\d+)-(\d+)\.\.(\d+)-(\d+): (?:error)|(?:warning) : (.*)$")

DEBUG_RETRIES_WARN = 3
DEBUG_RETRIES_REREGISTER = 4

ITEM_CONFNODE = 25

def ExtractChildrenTypesFromCatalog(catalog):
    children_types = []
    for n,d,h,c in catalog:
        if isinstance(c, ListType):
            children_types.extend(ExtractChildrenTypesFromCatalog(c))
        else:
            children_types.append((n, GetClassImporter(c), d))
    return children_types

def ExtractMenuItemsFromCatalog(catalog):
    menu_items = []
    for n,d,h,c in catalog:
        if isinstance(c, ListType):
            children = ExtractMenuItemsFromCatalog(c)
        else:
            children = []
        menu_items.append((n, d, h, children))
    return menu_items

def GetAddMenuItems():
    return ExtractMenuItemsFromCatalog(features.catalog)

class ProjectController(ConfigTreeNode, PLCControler):
    """
    This class define Root object of the confnode tree. 
    It is responsible of :
    - Managing project directory
    - Building project
    - Handling PLCOpenEditor controler and view
    - Loading user confnodes and instanciante them as children
    - ...
    
    """

    # For root object, available Children Types are modules of the confnode packages.
    CTNChildrenTypes = ExtractChildrenTypesFromCatalog(features.catalog)

    XSD = """<?xml version="1.0" encoding="ISO-8859-1" ?>
    <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
      <xsd:element name="BeremizRoot">
        <xsd:complexType>
          <xsd:sequence>
            <xsd:element name="TargetType">
              <xsd:complexType>
                <xsd:choice minOccurs="0">
                """+targets.GetTargetChoices()+"""
                </xsd:choice>
              </xsd:complexType>
            </xsd:element>
            <xsd:element name="Libraries" minOccurs="0">"""+(("""
              <xsd:complexType>
              """+"\n".join(['<xsd:attribute name='+
                             '"Enable_'+ libname + '_Library" '+
                             'type="xsd:boolean" use="optional" default="true"/>' 
                             for libname,lib in features.libraries])+"""
              </xsd:complexType>""") if len(features.libraries)>0 else '<xsd:complexType/>') + """
            </xsd:element>
          </xsd:sequence>
          <xsd:attribute name="URI_location" type="xsd:string" use="optional" default=""/>
          <xsd:attribute name="Disable_Extensions" type="xsd:boolean" use="optional" default="false"/>
        </xsd:complexType>
      </xsd:element>
    </xsd:schema>
    """
    EditorType = ProjectNodeEditor
    
    def __init__(self, frame, logger):
        PLCControler.__init__(self)

        self.MandatoryParams = None
        self._builder = None
        self._connector = None
        self.SetAppFrame(frame, logger)
        
        self.iec2c_path = os.path.join(base_folder, "matiec", "iec2c"+(".exe" if wx.Platform == '__WXMSW__' else ""))
        self.ieclib_path = os.path.join(base_folder, "matiec", "lib")
        
        # Setup debug information
        self.IECdebug_datas = {}
        self.IECdebug_lock = Lock()

        self.DebugTimer=None
        self.ResetIECProgramsAndVariables()

        # In both new or load scenario, no need to save
        self.ChangesToSave = False
        # root have no parent
        self.CTNParent = None
        # Keep track of the confnode type name
        self.CTNType = "Beremiz"
        self.Children = {}
        self._View = None
        # After __init__ root confnode is not valid
        self.ProjectPath = None
        self._setBuildPath(None)
        self.DebugThread = None
        self.debug_break = False
        self.previous_plcstate = None
        # copy ConfNodeMethods so that it can be later customized
        self.StatusMethods = [dic.copy() for dic in self.StatusMethods]

    def __del__(self):
        if self.DebugTimer:
            self.DebugTimer.cancel()
        self.KillDebugThread()
    
    def LoadLibraries(self):
        self.Libraries = []
        TypeStack=[]
        for libname,clsname in features.libraries:
            if self.BeremizRoot.Libraries is None or getattr(self.BeremizRoot.Libraries, "Enable_"+libname+"_Library"):
                Lib = GetClassImporter(clsname)()(self, libname, TypeStack)
                TypeStack.append(Lib.GetTypes())
                self.Libraries.append(Lib)
    
    def SetAppFrame(self, frame, logger):
        self.AppFrame = frame
        self.logger = logger
        self.StatusTimer = None
        
        if frame is not None:
            frame.LogViewer.SetLogSource(self._connector)
            
            # Timer to pull PLC status
            ID_STATUSTIMER = wx.NewId()
            self.StatusTimer = wx.Timer(self.AppFrame, ID_STATUSTIMER)
            self.AppFrame.Bind(wx.EVT_TIMER, self.PullPLCStatusProc, self.StatusTimer)
        
            self.RefreshConfNodesBlockLists()

    def ResetAppFrame(self, logger):
        if self.AppFrame is not None:
            self.AppFrame.Unbind(wx.EVT_TIMER, self.StatusTimer)
            self.StatusTimer = None
            self.AppFrame = None
        
        self.logger = logger

    def CTNName(self):
        return "Project"

    def CTNTestModified(self):
         return self.ChangesToSave or not self.ProjectIsSaved()

    def CTNFullName(self):
        return ""

    def GetCTRoot(self):
        return self

    def GetIECLibPath(self):
        return self.ieclib_path
    
    def GetIEC2cPath(self):
        return self.iec2c_path
    
    def GetCurrentLocation(self):
        return ()

    def GetCurrentName(self):
        return ""
    
    def _GetCurrentName(self):
        return ""

    def GetProjectPath(self):
        return self.ProjectPath

    def GetProjectName(self):
        return os.path.split(self.ProjectPath)[1]
    
    def GetIconName(self):
        return "PROJECT"
    
    def GetDefaultTargetName(self):
        if wx.Platform == '__WXMSW__':
            return "Win32"
        else:
            return "Linux"

    def GetTarget(self):
        target = self.BeremizRoot.getTargetType()
        if target.getcontent() is None:
            target = self.Classes["BeremizRoot_TargetType"]()
            target_name = self.GetDefaultTargetName()
            target.setcontent({"name": target_name, "value": self.Classes["TargetType_%s"%target_name]()})
        return target
    
    def GetParamsAttributes(self, path = None):
        params = ConfigTreeNode.GetParamsAttributes(self, path)
        if params[0]["name"] == "BeremizRoot":
            for child in params[0]["children"]:
                if child["name"] == "TargetType" and child["value"] == '':
                    child.update(self.GetTarget().getElementInfos("TargetType")) 
        return params
        
    def SetParamsAttribute(self, path, value):
        if path.startswith("BeremizRoot.TargetType.") and self.BeremizRoot.getTargetType().getcontent() is None:
            self.BeremizRoot.setTargetType(self.GetTarget())
        res = ConfigTreeNode.SetParamsAttribute(self, path, value)
        if path.startswith("BeremizRoot.Libraries."):
            wx.CallAfter(self.RefreshConfNodesBlockLists)
        return res
        
    # helper func to check project path write permission
    def CheckProjectPathPerm(self, dosave=True):
        if CheckPathPerm(self.ProjectPath):
            return True
        if self.AppFrame is not None:
            dialog = wx.MessageDialog(self.AppFrame, 
                        _('You must have permission to work on the project\nWork on a project copy ?'),
                        _('Error'), 
                        wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
            answer = dialog.ShowModal()
            dialog.Destroy()
            if answer == wx.ID_YES:
                if self.SaveProjectAs():
                    self.AppFrame.RefreshTitle()
                    self.AppFrame.RefreshFileMenu()
                    self.AppFrame.RefreshPageTitles()
                    return True
        return False
    
    def _getProjectFilesPath(self, project_path=None):
        if project_path is not None:
            return os.path.join(project_path, "project_files")
        projectfiles_path = os.path.join(self.GetProjectPath(), "project_files")
        if not os.path.exists(projectfiles_path):
            os.mkdir(projectfiles_path)
        return projectfiles_path
    
    def AddProjectDefaultConfiguration(self, config_name="config", res_name="resource1"):
        self.ProjectAddConfiguration(config_name)
        self.ProjectAddConfigurationResource(config_name, res_name)

    def NewProject(self, ProjectPath, BuildPath=None):
        """
        Create a new project in an empty folder
        @param ProjectPath: path of the folder where project have to be created
        @param PLCParams: properties of the PLCOpen program created
        """
        # Verify that chosen folder is empty
        if not os.path.isdir(ProjectPath) or len(os.listdir(ProjectPath)) > 0:
            return _("Chosen folder isn't empty. You can't use it for a new project!")
        
        # Create PLCOpen program
        self.CreateNewProject(
            {"projectName": _("Unnamed"),
             "productName": _("Unnamed"),
             "productVersion": "1",
             "companyName": _("Unknown"),
             "creationDateTime": datetime(*localtime()[:6])})
        self.AddProjectDefaultConfiguration()
        
        # Change XSD into class members
        self._AddParamsMembers()
        self.Children = {}
        # Keep track of the root confnode (i.e. project path)
        self.ProjectPath = ProjectPath
        self._setBuildPath(BuildPath)
        # get confnodes bloclist (is that usefull at project creation?)
        self.RefreshConfNodesBlockLists()
        # this will create files base XML files
        self.SaveProject()
        return None
        
    def LoadProject(self, ProjectPath, BuildPath=None):
        """
        Load a project contained in a folder
        @param ProjectPath: path of the project folder
        """
        if os.path.basename(ProjectPath) == "":
            ProjectPath = os.path.dirname(ProjectPath)
        # Verify that project contains a PLCOpen program
        plc_file = os.path.join(ProjectPath, "plc.xml")
        if not os.path.isfile(plc_file):
            return _("Chosen folder doesn't contain a program. It's not a valid project!")
        # Load PLCOpen file
        result = self.OpenXMLFile(plc_file)
        if result:
            return result
        if len(self.GetProjectConfigNames()) == 0:
            self.AddProjectDefaultConfiguration()
        # Change XSD into class members
        self._AddParamsMembers()
        self.Children = {}
        # Keep track of the root confnode (i.e. project path)
        self.ProjectPath = ProjectPath
        self._setBuildPath(BuildPath)
        # If dir have already be made, and file exist
        if os.path.isdir(self.CTNPath()) and os.path.isfile(self.ConfNodeXmlFilePath()):
            #Load the confnode.xml file into parameters members
            result = self.LoadXMLParams()
            if result:
                return result
            #Load and init all the children
            self.LoadChildren()
        self.RefreshConfNodesBlockLists()
        
        if os.path.exists(self._getBuildPath()):
            self.EnableMethod("_Clean", True)

        if os.path.isfile(self._getIECcodepath()):
            self.ShowMethod("_showIECcode", True)
        
        self.UpdateMethodsFromPLCStatus()
        
        return None
    
    def RecursiveConfNodeInfos(self, confnode):
        values = []
        for CTNChild in confnode.IECSortedChildren():
            values.append(
                {"name": "%s: %s" % (CTNChild.GetFullIEC_Channel(),
                                     CTNChild.CTNName()), 
                 "tagname": CTNChild.CTNFullName(),
                 "type": ITEM_CONFNODE, 
                 "confnode": CTNChild,
                 "icon": CTNChild.GetIconName(),
                 "values": self.RecursiveConfNodeInfos(CTNChild)})
        return values
    
    def GetProjectInfos(self):
        infos = PLCControler.GetProjectInfos(self)
        configurations = infos["values"].pop(-1)
        resources = None
        for config_infos in configurations["values"]:
            if resources is None:
                resources = config_infos["values"][0]
            else:
                resources["values"].extend(config_infos["values"][0]["values"])
        if resources is not None:
            infos["values"].append(resources)
        infos["values"].extend(self.RecursiveConfNodeInfos(self))
        return infos
    
    def CloseProject(self):
        self.ClearChildren()
        self.ResetAppFrame(None)
        
    def SaveProject(self, from_project_path=None):
        if self.CheckProjectPathPerm(False):
            if from_project_path is not None:
                old_projectfiles_path = self._getProjectFilesPath(from_project_path)
                if os.path.isdir(old_projectfiles_path):
                    shutil.copytree(old_projectfiles_path, 
                                    self._getProjectFilesPath(self.ProjectPath))
            self.SaveXMLFile(os.path.join(self.ProjectPath, 'plc.xml'))
            result = self.CTNRequestSave(from_project_path)
            if result:
                self.logger.write_error(result)
    
    def SaveProjectAs(self):
        # Ask user to choose a path with write permissions
        if wx.Platform == '__WXMSW__':
            path = os.getenv("USERPROFILE")
        else:
            path = os.getenv("HOME")
        dirdialog = wx.DirDialog(self.AppFrame , _("Choose a directory to save project"), path, wx.DD_NEW_DIR_BUTTON)
        answer = dirdialog.ShowModal()
        dirdialog.Destroy()
        if answer == wx.ID_OK:
            newprojectpath = dirdialog.GetPath()
            if os.path.isdir(newprojectpath):
                self.ProjectPath, old_project_path = newprojectpath, self.ProjectPath
                self.SaveProject(old_project_path)
                self._setBuildPath(self.BuildPath)
                return True
        return False

    def GetLibrariesTypes(self):
        self.LoadLibraries()
        return [ lib.GetTypes() for lib in self.Libraries ]

    def GetLibrariesSTCode(self):
        return "\n".join([ lib.GetSTCode() for lib in self.Libraries ])

    def GetLibrariesCCode(self, buildpath):
        if len(self.Libraries)==0:
            return [],[],()
        self.GetIECProgramsAndVariables()
        LibIECCflags = '"-I%s"'%os.path.abspath(self.GetIECLibPath())
        LocatedCCodeAndFlags=[]
        Extras=[]
        for lib in self.Libraries:
            res=lib.Generate_C(buildpath,self._VariablesList,LibIECCflags)  
            LocatedCCodeAndFlags.append(res[:2])
            if len(res)>2:
                Extras.extend(res[2:])
        return map(list,zip(*LocatedCCodeAndFlags))+[tuple(Extras)]
    
    # Update PLCOpenEditor ConfNode Block types from loaded confnodes
    def RefreshConfNodesBlockLists(self):
        if getattr(self, "Children", None) is not None:
            self.ClearConfNodeTypes()
            self.AddConfNodeTypesList(self.GetLibrariesTypes())
        if self.AppFrame is not None:
            self.AppFrame.RefreshLibraryPanel()
            self.AppFrame.RefreshEditor()
    
    # Update a PLCOpenEditor Pou variable location
    def UpdateProjectVariableLocation(self, old_leading, new_leading):
        self.Project.updateElementAddress(old_leading, new_leading)
        self.BufferProject()
        if self.AppFrame is not None:
            self.AppFrame.RefreshTitle()
            self.AppFrame.RefreshPouInstanceVariablesPanel()
            self.AppFrame.RefreshFileMenu()
            self.AppFrame.RefreshEditMenu()
            wx.CallAfter(self.AppFrame.RefreshEditor)
    
    def GetVariableLocationTree(self):
        '''
        This function is meant to be overridden by confnodes.

        It should returns an list of dictionaries
        
        - IEC_type is an IEC type like BOOL/BYTE/SINT/...
        - location is a string of this variable's location, like "%IX0.0.0"
        '''
        children = []
        for child in self.IECSortedChildren():
            children.append(child.GetVariableLocationTree())
        return children
    
    def ConfNodePath(self):
        return os.path.split(__file__)[0]
    
    def CTNPath(self, CTNName=None):
        return self.ProjectPath
    
    def ConfNodeXmlFilePath(self, CTNName=None):
        return os.path.join(self.CTNPath(CTNName), "beremiz.xml")

    def ParentsTypesFactory(self):
        return self.ConfNodeTypesFactory()

    def _setBuildPath(self, buildpath):
        if CheckPathPerm(buildpath):
            self.BuildPath = buildpath
        else:
            self.BuildPath = None
        self.BuildPath = buildpath
        self.DefaultBuildPath = None
        if self._builder is not None:
            self._builder.SetBuildPath(self._getBuildPath())

    def _getBuildPath(self):
        # BuildPath is defined by user
        if self.BuildPath is not None:
            return self.BuildPath
        # BuildPath isn't defined by user but already created by default
        if self.DefaultBuildPath is not None:
            return self.DefaultBuildPath
        # Create a build path in project folder if user has permissions
        if CheckPathPerm(self.ProjectPath):
            self.DefaultBuildPath = os.path.join(self.ProjectPath, "build")
        # Create a build path in temp folder
        else:
            self.DefaultBuildPath = os.path.join(tempfile.mkdtemp(), os.path.basename(self.ProjectPath), "build")
            
        if not os.path.exists(self.DefaultBuildPath):
            os.makedirs(self.DefaultBuildPath)
        return self.DefaultBuildPath
    
    def _getExtraFilesPath(self):
        return os.path.join(self._getBuildPath(), "extra_files")

    def _getIECcodepath(self):
        # define name for IEC code file
        return os.path.join(self._getBuildPath(), "plc.st")
    
    def _getIECgeneratedcodepath(self):
        # define name for IEC generated code file
        return os.path.join(self._getBuildPath(), "generated_plc.st")
    
    def _getIECrawcodepath(self):
        # define name for IEC raw code file
        return os.path.join(self.CTNPath(), "raw_plc.st")
    
    def GetLocations(self):
        locations = []
        filepath = os.path.join(self._getBuildPath(),"LOCATED_VARIABLES.h")
        if os.path.isfile(filepath):
            # IEC2C compiler generate a list of located variables : LOCATED_VARIABLES.h
            location_file = open(os.path.join(self._getBuildPath(),"LOCATED_VARIABLES.h"))
            # each line of LOCATED_VARIABLES.h declares a located variable
            lines = [line.strip() for line in location_file.readlines()]
            # This regular expression parses the lines genereated by IEC2C
            LOCATED_MODEL = re.compile("__LOCATED_VAR\((?P<IEC_TYPE>[A-Z]*),(?P<NAME>[_A-Za-z0-9]*),(?P<DIR>[QMI])(?:,(?P<SIZE>[XBWDL]))?,(?P<LOC>[,0-9]*)\)")
            for line in lines:
                # If line match RE, 
                result = LOCATED_MODEL.match(line)
                if result:
                    # Get the resulting dict
                    resdict = result.groupdict()
                    # rewrite string for variadic location as a tuple of integers
                    resdict['LOC'] = tuple(map(int,resdict['LOC'].split(',')))
                    # set located size to 'X' if not given 
                    if not resdict['SIZE']:
                        resdict['SIZE'] = 'X'
                    # finally store into located variable list
                    locations.append(resdict)
        return locations
    
    def GetConfNodeGlobalInstances(self):
        return self._GlobalInstances()
    
    def _Generate_SoftPLC(self):
        """
        Generate SoftPLC ST/IL/SFC code out of PLCOpenEditor controller, and compile it with IEC2C
        @param buildpath: path where files should be created
        """

        # Update PLCOpenEditor ConfNode Block types before generate ST code
        self.RefreshConfNodesBlockLists()
        
        self.logger.write(_("Generating SoftPLC IEC-61131 ST/IL/SFC code...\n"))
        buildpath = self._getBuildPath()
        # ask PLCOpenEditor controller to write ST/IL/SFC code file
        program, errors, warnings = self.GenerateProgram(self._getIECgeneratedcodepath())
        if len(warnings) > 0:
            self.logger.write_warning(_("Warnings in ST/IL/SFC code generator :\n"))
            for warning in warnings:
                self.logger.write_warning("%s\n"%warning)
        if len(errors) > 0:
            # Failed !
            self.logger.write_error(_("Error in ST/IL/SFC code generator :\n%s\n")%errors[0])
            return False
        plc_file = open(self._getIECcodepath(), "w")
        # Add ST Library from confnodes
        plc_file.write(self.GetLibrariesSTCode())
        if os.path.isfile(self._getIECrawcodepath()):
            plc_file.write(open(self._getIECrawcodepath(), "r").read())
            plc_file.write("\n")
        plc_file.close()
        plc_file = open(self._getIECcodepath(), "r")
        self.ProgramOffset = 0
        for line in plc_file.xreadlines():
            self.ProgramOffset += 1
        plc_file.close()
        plc_file = open(self._getIECcodepath(), "a")
        plc_file.write(open(self._getIECgeneratedcodepath(), "r").read())
        plc_file.close()

        self.logger.write(_("Compiling IEC Program into C code...\n"))

        # Now compile IEC code into many C files
        # files are listed to stdout, and errors to stderr. 
        status, result, err_result = ProcessLogger(
               self.logger,
               "\"%s\" -f -I \"%s\" -T \"%s\" \"%s\""%(
                         self.iec2c_path,
                         self.ieclib_path, 
                         buildpath,
                         self._getIECcodepath()),
               no_stdout=True, no_stderr=True).spin()
        if status:
            # Failed !
            
            # parse iec2c's error message. if it contains a line number,
            # then print those lines from the generated IEC file.
            for err_line in err_result.split('\n'):
                self.logger.write_warning(err_line + "\n")

                m_result = MATIEC_ERROR_MODEL.match(err_line)
                if m_result is not None:
                    first_line, first_column, last_line, last_column, error = m_result.groups()
                    first_line, last_line = int(first_line), int(last_line)
                    
                    last_section = None
                    f = open(self._getIECcodepath())

                    for i, line in enumerate(f.readlines()):
                        i = i + 1
                        if line[0] not in '\t \r\n':
                            last_section = line

                        if first_line <= i <= last_line:
                            if last_section is not None:
                                self.logger.write_warning("In section: " + last_section)
                                last_section = None # only write section once
                            self.logger.write_warning("%04d: %s" % (i, line))

                    f.close()
            
            self.logger.write_error(_("Error : IEC to C compiler returned %d\n")%status)
            return False
        
        # Now extract C files of stdout
        C_files = [ fname for fname in result.splitlines() if fname[-2:]==".c" or fname[-2:]==".C" ]
        # remove those that are not to be compiled because included by others
        C_files.remove("POUS.c")
        if not C_files:
            self.logger.write_error(_("Error : At least one configuration and one resource must be declared in PLC !\n"))
            return False
        # transform those base names to full names with path
        C_files = map(lambda filename:os.path.join(buildpath, filename), C_files)

        # prepend beremiz include to configuration header
        H_files = [ fname for fname in result.splitlines() if fname[-2:]==".h" or fname[-2:]==".H" ]
        H_files.remove("LOCATED_VARIABLES.h")
        H_files = map(lambda filename:os.path.join(buildpath, filename), H_files)
        for H_file in H_files:
            with file(H_file, 'r') as original: data = original.read()
            with file(H_file, 'w') as modified: modified.write('#include "beremiz.h"\n' + data)

        self.logger.write(_("Extracting Located Variables...\n"))
        # Keep track of generated located variables for later use by self._Generate_C
        self.PLCGeneratedLocatedVars = self.GetLocations()
        # Keep track of generated C files for later use by self.CTNGenerate_C
        self.PLCGeneratedCFiles = C_files
        # compute CFLAGS for plc
        self.plcCFLAGS = "\"-I"+self.ieclib_path+"\""
        return True

    def GetBuilder(self):
        """
        Return a Builder (compile C code into machine code)
        """
        # Get target, module and class name
        targetname = self.GetTarget().getcontent()["name"]
        targetclass = targets.GetBuilder(targetname)

        # if target already 
        if self._builder is None or not isinstance(self._builder,targetclass):
            # Get classname instance
            self._builder = targetclass(self)
        return self._builder

    def ResetBuildMD5(self):
        builder=self.GetBuilder()
        if builder is not None:
            builder.ResetBinaryCodeMD5()
        self.EnableMethod("_Transfer", False)

    def GetLastBuildMD5(self):
        builder=self.GetBuilder()
        if builder is not None:
            return builder.GetBinaryCodeMD5()
        else:
            return None

    #######################################################################
    #
    #                C CODE GENERATION METHODS
    #
    #######################################################################
    
    def CTNGenerate_C(self, buildpath, locations):
        """
        Return C code generated by iec2c compiler 
        when _generate_softPLC have been called
        @param locations: ignored
        @return: [(C_file_name, CFLAGS),...] , LDFLAGS_TO_APPEND
        """

        return ([(C_file_name, self.plcCFLAGS) 
                for C_file_name in self.PLCGeneratedCFiles ], 
               "", # no ldflags
               False) # do not expose retreive/publish calls
    
    def ResetIECProgramsAndVariables(self):
        """
        Reset variable and program list that are parsed from
        CSV file generated by IEC2C compiler.
        """
        self._ProgramList = None
        self._VariablesList = None
        self._IECPathToIdx = {}
        self._Ticktime = 0
        self.TracedIECPath = []

    def GetIECProgramsAndVariables(self):
        """
        Parse CSV-like file  VARIABLES.csv resulting from IEC2C compiler.
        Each section is marked with a line staring with '//'
        list of all variables used in various POUs
        """
        if self._ProgramList is None or self._VariablesList is None:
            try:
                csvfile = os.path.join(self._getBuildPath(),"VARIABLES.csv")
                # describes CSV columns
                ProgramsListAttributeName = ["num", "C_path", "type"]
                VariablesListAttributeName = ["num", "vartype", "IEC_path", "C_path", "type"]
                self._ProgramList = []
                self._VariablesList = []
                self._IECPathToIdx = {}
                
                # Separate sections
                ListGroup = []
                for line in open(csvfile,'r').xreadlines():
                    strippedline = line.strip()
                    if strippedline.startswith("//"):
                        # Start new section
                        ListGroup.append([])
                    elif len(strippedline) > 0 and len(ListGroup) > 0:
                        # append to this section
                        ListGroup[-1].append(strippedline)
        
                # first section contains programs
                for line in ListGroup[0]:
                    # Split and Maps each field to dictionnary entries
                    attrs = dict(zip(ProgramsListAttributeName,line.strip().split(';')))
                    # Truncate "C_path" to remove conf an ressources names
                    attrs["C_path"] = '__'.join(attrs["C_path"].split(".",2)[1:])
                    # Push this dictionnary into result.
                    self._ProgramList.append(attrs)
        
                # second section contains all variables
                config_FBs = {}
                for line in ListGroup[1]:
                    # Split and Maps each field to dictionnary entries
                    attrs = dict(zip(VariablesListAttributeName,line.strip().split(';')))
                    # Truncate "C_path" to remove conf an ressources names
                    parts = attrs["C_path"].split(".",2)
                    if len(parts) > 2:
                        config_FB = config_FBs.get(tuple(parts[:2]))
                        if config_FB:
                            parts = [config_FB] + parts[2:]
                            attrs["C_path"] = '.'.join(parts)
                        else: 
                            attrs["C_path"] = '__'.join(parts[1:])
                    else:
                        attrs["C_path"] = '__'.join(parts)
                        if attrs["vartype"] == "FB":
                            config_FBs[tuple(parts)] = attrs["C_path"]
                    # Push this dictionnary into result.
                    self._VariablesList.append(attrs)
                    # Fill in IEC<->C translation dicts
                    IEC_path=attrs["IEC_path"]
                    Idx=int(attrs["num"])
                    self._IECPathToIdx[IEC_path]=(Idx, attrs["type"])
                
                # third section contains ticktime
                if len(ListGroup) > 2:
                    self._Ticktime = int(ListGroup[2][0]) 
                
            except Exception,e:
                self.logger.write_error(_("Cannot open/parse VARIABLES.csv!\n"))
                self.logger.write_error(traceback.format_exc())
                self.ResetIECProgramsAndVariables()
                return False

        return True

    def Generate_plc_debugger(self):
        """
        Generate trace/debug code out of PLC variable list
        """
        self.GetIECProgramsAndVariables()

        # prepare debug code
        debug_code = targets.GetCode("plc_debug") % {
           "buffer_size": reduce(lambda x, y: x + y, [DebugTypesSize.get(v["type"], 0) for v in self._VariablesList], 0),
           "programs_declarations":
               "\n".join(["extern %(type)s %(C_path)s;"%p for p in self._ProgramList]),
           "extern_variables_declarations":"\n".join([
              {"EXT":"extern __IEC_%(type)s_p %(C_path)s;",
               "IN":"extern __IEC_%(type)s_p %(C_path)s;",
               "MEM":"extern __IEC_%(type)s_p %(C_path)s;",
               "OUT":"extern __IEC_%(type)s_p %(C_path)s;",
               "VAR":"extern __IEC_%(type)s_t %(C_path)s;",
               "FB":"extern %(type)s %(C_path)s;"}[v["vartype"]]%v 
               for v in self._VariablesList if v["C_path"].find('.')<0]),
           "for_each_variable_do_code":"\n".join([
               {"EXT":"    (*fp)((void*)&(%(C_path)s),%(type)s_P_ENUM);\n",
                "IN":"    (*fp)((void*)&(%(C_path)s),%(type)s_P_ENUM);\n",
                "MEM":"    (*fp)((void*)&(%(C_path)s),%(type)s_O_ENUM);\n",
                "OUT":"    (*fp)((void*)&(%(C_path)s),%(type)s_O_ENUM);\n",
                "VAR":"    (*fp)((void*)&(%(C_path)s),%(type)s_ENUM);\n"}[v["vartype"]]%v
                for v in self._VariablesList if v["vartype"] != "FB" and v["type"] in DebugTypesSize ]),
           "find_variable_case_code":"\n".join([
               "    case %(num)s:\n"%v+
               "        *varp = (void*)&(%(C_path)s);\n"%v+
               {"EXT":"        return %(type)s_P_ENUM;\n",
                "IN":"        return %(type)s_P_ENUM;\n",
                "MEM":"        return %(type)s_O_ENUM;\n",
                "OUT":"        return %(type)s_O_ENUM;\n",
                "VAR":"        return %(type)s_ENUM;\n"}[v["vartype"]]%v
                for v in self._VariablesList if v["vartype"] != "FB" and v["type"] in DebugTypesSize ])}
        
        return debug_code
        
    def Generate_plc_main(self):
        """
        Use confnodes layout given in LocationCFilesAndCFLAGS to
        generate glue code that dispatch calls to all confnodes
        """
        # filter location that are related to code that will be called
        # in retreive, publish, init, cleanup
        locstrs = map(lambda x:"_".join(map(str,x)),
           [loc for loc,Cfiles,DoCalls in self.LocationCFilesAndCFLAGS if loc and DoCalls])
        
        # Generate main, based on template
        if not self.BeremizRoot.getDisable_Extensions():
            plc_main_code = targets.GetCode("plc_main_head") % {
                "calls_prototypes":"\n".join([(
                      "int __init_%(s)s(int argc,char **argv);\n"+
                      "void __cleanup_%(s)s(void);\n"+
                      "void __retrieve_%(s)s(void);\n"+
                      "void __publish_%(s)s(void);")%{'s':locstr} for locstr in locstrs]),
                "retrieve_calls":"\n    ".join([
                      "__retrieve_%s();"%locstr for locstr in locstrs]),
                "publish_calls":"\n    ".join([ #Call publish in reverse order
                      "__publish_%s();"%locstrs[i-1] for i in xrange(len(locstrs), 0, -1)]),
                "init_calls":"\n    ".join([
                      "init_level=%d; "%(i+1)+
                      "if((res = __init_%s(argc,argv))){"%locstr +
                      #"printf(\"%s\"); "%locstr + #for debug
                      "return res;}" for i,locstr in enumerate(locstrs)]),
                "cleanup_calls":"\n    ".join([
                      "if(init_level >= %d) "%i+
                      "__cleanup_%s();"%locstrs[i-1] for i in xrange(len(locstrs), 0, -1)])
                }
        else:
            plc_main_code = targets.GetCode("plc_main_head") % {
                "calls_prototypes":"\n",
                "retrieve_calls":"\n",
                "publish_calls":"\n",
                "init_calls":"\n",
                "cleanup_calls":"\n"
                }
        plc_main_code += targets.GetTargetCode(self.GetTarget().getcontent()["name"])
        plc_main_code += targets.GetCode("plc_main_tail")
        return plc_main_code

        
    def _Build(self):
        """
        Method called by user to (re)build SoftPLC and confnode tree
        """
        if self.AppFrame is not None:
            self.AppFrame.ClearErrors()
        self._CloseView(self._IECCodeView)
        
        buildpath = self._getBuildPath()

        # Eventually create build dir
        if not os.path.exists(buildpath):
            os.mkdir(buildpath)
        # There is something to clean
        self.EnableMethod("_Clean", True)

        self.logger.flush()
        self.logger.write(_("Start build in %s\n") % buildpath)

        # Generate SoftPLC IEC code
        IECGenRes = self._Generate_SoftPLC()
        self.ShowMethod("_showIECcode", True)

        # If IEC code gen fail, bail out.
        if not IECGenRes:
            self.logger.write_error(_("IEC-61131-3 code generation failed !\n"))
            self.ResetBuildMD5()
            return False

        # Reset variable and program list that are parsed from
        # CSV file generated by IEC2C compiler.
        self.ResetIECProgramsAndVariables()
        
        # Generate C code and compilation params from confnode hierarchy
        try:
            CTNLocationCFilesAndCFLAGS, CTNLDFLAGS, CTNExtraFiles = self._Generate_C(
                buildpath, 
                self.PLCGeneratedLocatedVars)
        except Exception, exc:
            self.logger.write_error(_("Runtime extensions C code generation failed !\n"))
            self.logger.write_error(traceback.format_exc())
            self.ResetBuildMD5()
            return False

        # Generate C code and compilation params from liraries
        try:
            LibCFilesAndCFLAGS, LibLDFLAGS, LibExtraFiles = self.GetLibrariesCCode(buildpath)
        except Exception, exc:
            self.logger.write_error(_("Runtime extensions C code generation failed !\n"))
            self.logger.write_error(traceback.format_exc())
            self.ResetBuildMD5()
            return False

        self.LocationCFilesAndCFLAGS =  CTNLocationCFilesAndCFLAGS + LibCFilesAndCFLAGS
        self.LDFLAGS = CTNLDFLAGS + LibLDFLAGS
        ExtraFiles = CTNExtraFiles + LibExtraFiles
        
        # Get temporary directory path
        extrafilespath = self._getExtraFilesPath()
        # Remove old directory
        if os.path.exists(extrafilespath):
            shutil.rmtree(extrafilespath)
        # Recreate directory
        os.mkdir(extrafilespath)
        # Then write the files
        for fname,fobject in ExtraFiles:
            fpath = os.path.join(extrafilespath,fname)
            open(fpath, "wb").write(fobject.read())
        # Now we can forget ExtraFiles (will close files object)
        del ExtraFiles
        
        # Header file for extensions
        open(os.path.join(buildpath,"beremiz.h"), "w").write(targets.GetHeader())

        # Template based part of C code generation
        # files are stacked at the beginning, as files of confnode tree root
        for generator, filename, name in [
           # debugger code
           (self.Generate_plc_debugger, "plc_debugger.c", "Debugger"),
           # init/cleanup/retrieve/publish, run and align code
           (self.Generate_plc_main,"plc_main.c","Common runtime")]:
            try:
                # Do generate
                code = generator()
                if code is None:
                     raise
                code_path = os.path.join(buildpath,filename)
                open(code_path, "w").write(code)
                # Insert this file as first file to be compiled at root confnode
                self.LocationCFilesAndCFLAGS[0][1].insert(0,(code_path, self.plcCFLAGS))
            except Exception, exc:
                self.logger.write_error(name+_(" generation failed !\n"))
                self.logger.write_error(traceback.format_exc())
                self.ResetBuildMD5()
                return False

        self.logger.write(_("C code generated successfully.\n"))

        # Get current or fresh builder
        builder = self.GetBuilder()
        if builder is None:
            self.logger.write_error(_("Fatal : cannot get builder.\n"))
            self.ResetBuildMD5()
            return False

        # Build
        try:
            if not builder.build() :
                self.logger.write_error(_("C Build failed.\n"))
                return False
        except Exception, exc:
            self.logger.write_error(_("C Build crashed !\n"))
            self.logger.write_error(traceback.format_exc())
            self.ResetBuildMD5()
            return False

        self.logger.write(_("Successfully built.\n"))
        # Update GUI status about need for transfer
        self.CompareLocalAndRemotePLC()
        return True
    
    def ShowError(self, logger, from_location, to_location):
        chunk_infos = self.GetChunkInfos(from_location, to_location)
        for infos, (start_row, start_col) in chunk_infos:
            start = (from_location[0] - start_row, from_location[1] - start_col)
            end = (to_location[0] - start_row, to_location[1] - start_col)
            if self.AppFrame is not None:
                self.AppFrame.ShowError(infos, start, end)
    
    _IECCodeView = None
    def _showIECcode(self):
        self._OpenView("IEC code")

    _IECRawCodeView = None
    def _editIECrawcode(self):
        self._OpenView("IEC raw code")
    
    _ProjectFilesView = None
    def _OpenProjectFiles(self):
        self._OpenView("Project Files")
    
    _FileEditors = {}
    def _OpenFileEditor(self, filepath):
        self._OpenView(filepath)
    
    def _OpenView(self, name=None, onlyopened=False):
        if name == "IEC code":
            if self._IECCodeView is None:
                plc_file = self._getIECcodepath()
            
                self._IECCodeView = IECCodeViewer(self.AppFrame.TabsOpened, "", self.AppFrame, None, instancepath=name)
                self._IECCodeView.SetTextSyntax("ALL")
                self._IECCodeView.SetKeywords(IEC_KEYWORDS)
                try:
                    text = file(plc_file).read()
                except:
                    text = '(* No IEC code have been generated at that time ! *)'
                self._IECCodeView.SetText(text = text)
                self._IECCodeView.SetIcon(GetBitmap("ST"))
                setattr(self._IECCodeView, "_OnClose", self.OnCloseEditor)
            
            if self._IECCodeView is not None:
                self.AppFrame.EditProjectElement(self._IECCodeView, name)
            
            return self._IECCodeView
        
        elif name == "IEC raw code":
            if self._IECRawCodeView is None:
                controler = MiniTextControler(self._getIECrawcodepath(), self)
                
                self._IECRawCodeView = IECCodeViewer(self.AppFrame.TabsOpened, "", self.AppFrame, controler, instancepath=name)
                self._IECRawCodeView.SetTextSyntax("ALL")
                self._IECRawCodeView.SetKeywords(IEC_KEYWORDS)
                self._IECRawCodeView.RefreshView()
                self._IECRawCodeView.SetIcon(GetBitmap("ST"))
                setattr(self._IECRawCodeView, "_OnClose", self.OnCloseEditor)
            
            if self._IECRawCodeView is not None:
                self.AppFrame.EditProjectElement(self._IECRawCodeView, name)
            
            return self._IECRawCodeView
        
        elif name == "Project Files":
            if self._ProjectFilesView is None:
                self._ProjectFilesView = FileManagementPanel(self.AppFrame.TabsOpened, self, name, self._getProjectFilesPath(), True)
                
                extensions = []
                for extension, name, editor in features.file_editors:
                    if extension not in extensions:
                        extensions.append(extension)
                self._ProjectFilesView.SetEditableFileExtensions(extensions) 
                
            if self._ProjectFilesView is not None:
                self.AppFrame.EditProjectElement(self._ProjectFilesView, name)
            
            return self._ProjectFilesView
        
        elif name is not None and name.find("::") != -1:
            filepath, editor_name = name.split("::")
            if not self._FileEditors.has_key(filepath):
                if os.path.isfile(filepath):
                    file_extension = os.path.splitext(filepath)[1]
                        
                    editors = dict([(edit_name, edit_class)
                                    for extension, edit_name, edit_class in features.file_editors
                                    if extension == file_extension])
                    
                    if editor_name == "":
                        if len(editors) == 1:
                            editor_name = editors.keys()[0]
                        elif len(editors) > 0:
                            names = editors.keys()
                            dialog = wx.SingleChoiceDialog(self.AppFrame, 
                                  _("Select an editor:"), _("Editor selection"), 
                                  names, wx.DEFAULT_DIALOG_STYLE|wx.OK|wx.CANCEL)
                            if dialog.ShowModal() == wx.ID_OK:
                                editor_name = names[dialog.GetSelection()]
                            dialog.Destroy()
                        
                    if editor_name != "":
                        name = "::".join([filepath, editor_name])
                        
                        editor = editors[editor_name]()
                        self._FileEditors[filepath] = editor(self.AppFrame.TabsOpened, self, name, self.AppFrame)
                        self._FileEditors[filepath].SetIcon(GetBitmap("FILE"))
                        if isinstance(self._FileEditors[filepath], DebugViewer):
                            self._FileEditors[filepath].SetDataProducer(self)
            
            if self._FileEditors.has_key(filepath):
                editor = self._FileEditors[filepath]
                self.AppFrame.EditProjectElement(editor, editor.GetTagName())
                
            return self._FileEditors.get(filepath)
        else:
            return ConfigTreeNode._OpenView(self, self.CTNName(), onlyopened)

    def OnCloseEditor(self, view):
        ConfigTreeNode.OnCloseEditor(self, view)
        if self._IECCodeView == view:
            self._IECCodeView = None
        if self._IECRawCodeView == view:
            self._IECRawCodeView = None
        if self._ProjectFilesView == view:
            self._ProjectFilesView = None
        if view in self._FileEditors.values():
            self._FileEditors.pop(view.GetFilePath())

    def _Clean(self):
        self._CloseView(self._IECCodeView)
        if os.path.isdir(os.path.join(self._getBuildPath())):
            self.logger.write(_("Cleaning the build directory\n"))
            shutil.rmtree(os.path.join(self._getBuildPath()))
        else:
            self.logger.write_error(_("Build directory already clean\n"))
        self.ShowMethod("_showIECcode", False)
        self.EnableMethod("_Clean", False)
        # kill the builder
        self._builder = None
        self.CompareLocalAndRemotePLC()

    def UpdatePLCLog(self, log_count):
        if log_count:
            if self.AppFrame is not None:
                self.AppFrame.LogViewer.SetLogCounters(log_count)
    
    def UpdateMethodsFromPLCStatus(self):
        status = None
        if self._connector is not None:
            PLCstatus = self._connector.GetPLCstatus()
            if PLCstatus is not None:
                status, log_count = PLCstatus
                self.UpdatePLCLog(log_count)
        if status is None:
            self._SetConnector(None, False)
            status = "Disconnected"
        if(self.previous_plcstate != status):
            for args in {
                     "Started" :     [("_Run", False),
                                      ("_Stop", True)],
                     "Stopped" :     [("_Run", True),
                                      ("_Stop", False)],
                     "Empty" :       [("_Run", False),
                                      ("_Stop", False)],
                     "Broken" :      [],
                     "Disconnected" :[("_Run", False),
                                      ("_Stop", False),
                                      ("_Transfer", False),
                                      ("_Connect", True),
                                      ("_Disconnect", False)],
                   }.get(status,[]):
                self.ShowMethod(*args)
            self.previous_plcstate = status
            if self.AppFrame is not None:
                self.AppFrame.RefreshStatusToolBar()
                if status == "Disconnected":
                    self.AppFrame.ConnectionStatusBar.SetStatusText(_(status), 1)
                    self.AppFrame.ConnectionStatusBar.SetStatusText('', 2)
                else:
                    self.AppFrame.ConnectionStatusBar.SetStatusText(
                        _("Connected to URI: %s") % self.BeremizRoot.getURI_location().strip(), 1)
                    self.AppFrame.ConnectionStatusBar.SetStatusText(_(status), 2)
                
    def PullPLCStatusProc(self, event):
        self.UpdateMethodsFromPLCStatus()
        
    def RegisterDebugVarToConnector(self):
        self.DebugTimer=None
        Idxs = []
        self.TracedIECPath = []
        if self._connector is not None:
            self.IECdebug_lock.acquire()
            IECPathsToPop = []
            for IECPath,data_tuple in self.IECdebug_datas.iteritems():
                WeakCallableDict, data_log, status, fvalue = data_tuple
                if len(WeakCallableDict) == 0:
                    # Callable Dict is empty.
                    # This variable is not needed anymore!
                    IECPathsToPop.append(IECPath)
                elif IECPath != "__tick__":
                    # Convert 
                    Idx, IEC_Type = self._IECPathToIdx.get(IECPath,(None,None))
                    if Idx is not None:
                        if IEC_Type in DebugTypesSize: 
                            Idxs.append((Idx, IEC_Type, fvalue, IECPath))
                        else:
                            self.logger.write_warning(_("Debug: Unsupported type to debug '%s'\n")%IEC_Type)
                    else:
                        self.logger.write_warning(_("Debug: Unknown variable '%s'\n")%IECPath)
            for IECPathToPop in IECPathsToPop:
                self.IECdebug_datas.pop(IECPathToPop)

            if Idxs:
                Idxs.sort()
                self.TracedIECPath = zip(*Idxs)[3]
                self._connector.SetTraceVariablesList(zip(*zip(*Idxs)[0:3]))
            else:
                self.TracedIECPath = []
                self._connector.SetTraceVariablesList([])
            self.IECdebug_lock.release()
    
    def IsPLCStarted(self):
        return self.previous_plcstate == "Started"
     
    def ReArmDebugRegisterTimer(self):
        if self.DebugTimer is not None:
            self.DebugTimer.cancel()
        
        # Prevent to call RegisterDebugVarToConnector when PLC is not started
        # If an output location var is forced it's leads to segmentation fault in runtime
        # Links between PLC located variables and real variables are not ready
        if self.IsPLCStarted():
            # Timer to prevent rapid-fire when registering many variables
            # use wx.CallAfter use keep using same thread. TODO : use wx.Timer instead
            self.DebugTimer=Timer(0.5,wx.CallAfter,args = [self.RegisterDebugVarToConnector])
            # Rearm anti-rapid-fire timer
            self.DebugTimer.start()

    def GetDebugIECVariableType(self, IECPath):
        Idx, IEC_Type = self._IECPathToIdx.get(IECPath,(None,None))
        return IEC_Type
        
    def SubscribeDebugIECVariable(self, IECPath, callableobj, *args, **kwargs):
        """
        Dispatching use a dictionnary linking IEC variable paths
        to a WeakKeyDictionary linking 
        weakly referenced callables to optionnal args
        """
        if IECPath != "__tick__" and not self._IECPathToIdx.has_key(IECPath):
            return None
        
        self.IECdebug_lock.acquire()
        # If no entry exist, create a new one with a fresh WeakKeyDictionary
        IECdebug_data = self.IECdebug_datas.get(IECPath, None)
        if IECdebug_data is None:
            IECdebug_data  = [
                    WeakKeyDictionary(), # Callables
                    [],                  # Data storage [(tick, data),...]
                    "Registered",        # Variable status
                    None]                # Forced value
            self.IECdebug_datas[IECPath] = IECdebug_data
        
        IECdebug_data[0][callableobj]=(args, kwargs)

        self.IECdebug_lock.release()
        
        self.ReArmDebugRegisterTimer()
        
        return IECdebug_data[1]

    def UnsubscribeDebugIECVariable(self, IECPath, callableobj):
        self.IECdebug_lock.acquire()
        IECdebug_data = self.IECdebug_datas.get(IECPath, None)
        if IECdebug_data is not None:
            IECdebug_data[0].pop(callableobj,None)
            if len(IECdebug_data[0]) == 0:
                self.IECdebug_datas.pop(IECPath)
        self.IECdebug_lock.release()

        self.ReArmDebugRegisterTimer()

    def UnsubscribeAllDebugIECVariable(self):
        self.IECdebug_lock.acquire()
        self.IECdebug_datas = {}
        self.IECdebug_lock.release()

        self.ReArmDebugRegisterTimer()

    def ForceDebugIECVariable(self, IECPath, fvalue):
        if not self.IECdebug_datas.has_key(IECPath):
            return
        
        self.IECdebug_lock.acquire()
        
        # If no entry exist, create a new one with a fresh WeakKeyDictionary
        IECdebug_data = self.IECdebug_datas.get(IECPath, None)
        IECdebug_data[2] = "Forced"
        IECdebug_data[3] = fvalue
        
        self.IECdebug_lock.release()
        
        self.ReArmDebugRegisterTimer()
    
    def ReleaseDebugIECVariable(self, IECPath):
        if not self.IECdebug_datas.has_key(IECPath):
            return
        
        self.IECdebug_lock.acquire()
        
        # If no entry exist, create a new one with a fresh WeakKeyDictionary
        IECdebug_data = self.IECdebug_datas.get(IECPath, None)
        IECdebug_data[2] = "Registered"
        IECdebug_data[3] = None
        
        self.IECdebug_lock.release()
        
        self.ReArmDebugRegisterTimer()
    
    def CallWeakcallables(self, IECPath, function_name, *cargs):
        data_tuple = self.IECdebug_datas.get(IECPath, None)
        if data_tuple is not None:
            WeakCallableDict, data_log, status, fvalue = data_tuple
            #data_log.append((debug_tick, value))
            for weakcallable,(args,kwargs) in WeakCallableDict.iteritems():
                function = getattr(weakcallable, function_name, None)
                if function is not None:
                    if status == "Forced" and cargs[1] == fvalue:
                        function(*(cargs + (True,) + args), **kwargs)
                    else:
                        function(*(cargs + args), **kwargs)
                # This will block thread if more than one call is waiting

    def GetTicktime(self):
        return self._Ticktime

    def RemoteExec(self, script, **kwargs):
        if self._connector is None:
            return -1, "No runtime connected!"
        return self._connector.RemoteExec(script, **kwargs)

    def DebugThreadProc(self):
        """
        This thread waid PLC debug data, and dispatch them to subscribers
        """
        self.debug_break = False
        debug_getvar_retry = 0
        while (not self.debug_break) and (self._connector is not None):
            Trace = self._connector.GetTraceVariables()
            if(Trace):
                plc_status, debug_tick, debug_vars = Trace
            else:
                plc_status = None
            debug_getvar_retry += 1
            #print [dict.keys() for IECPath, (dict, log, status, fvalue) in self.IECdebug_datas.items()]
            if plc_status == "Started":
                self.IECdebug_lock.acquire()
                if len(debug_vars) == len(self.TracedIECPath):
                    if debug_getvar_retry > DEBUG_RETRIES_WARN:
                        self.logger.write(_("... debugger recovered\n"))
                    debug_getvar_retry = 0
                    for IECPath,value in zip(self.TracedIECPath, debug_vars):
                        if value is not None:
                            self.CallWeakcallables(IECPath, "NewValue", debug_tick, value)
                    self.CallWeakcallables("__tick__", "NewDataAvailable", debug_tick)
                self.IECdebug_lock.release()
                if debug_getvar_retry == DEBUG_RETRIES_WARN:
                    self.logger.write(_("Waiting debugger to recover...\n"))
                if debug_getvar_retry == DEBUG_RETRIES_REREGISTER:
                    # re-register debug registry to PLC
                    wx.CallAfter(self.RegisterDebugVarToConnector)
                if debug_getvar_retry != 0:
                    # Be patient, tollerate PLC to come up before debugging
                    time.sleep(0.1)
            else:
                self.debug_break = True
        self.logger.write(_("Debugger disabled\n"))
        self.DebugThread = None

    def KillDebugThread(self):
        tmp_debugthread = self.DebugThread
        self.debug_break = True
        if tmp_debugthread is not None:
            self.logger.writeyield(_("Stopping debugger...\n"))
            tmp_debugthread.join(timeout=5)
            if tmp_debugthread.isAlive() and self.logger:
                self.logger.write_warning(_("Couldn't stop debugger.\n"))
            else:
                self.logger.write(_("Debugger stopped.\n"))
        self.DebugThread = None

    def _connect_debug(self): 
        self.previous_plcstate = None
        if self.AppFrame:
            self.AppFrame.ResetGraphicViewers()
        self.RegisterDebugVarToConnector()
        if self.DebugThread is None:
            self.DebugThread = Thread(target=self.DebugThreadProc)
            self.DebugThread.start()
    
    def _Run(self):
        """
        Start PLC
        """
        if self.GetIECProgramsAndVariables():
            self._connector.StartPLC()
            self.logger.write(_("Starting PLC\n"))
            self._connect_debug()
        else:
            self.logger.write_error(_("Couldn't start PLC !\n"))
        wx.CallAfter(self.UpdateMethodsFromPLCStatus)
       
    def _Stop(self):
        """
        Stop PLC
        """
        if self._connector is not None and not self._connector.StopPLC():
            self.logger.write_error(_("Couldn't stop PLC !\n"))

        # debugthread should die on his own
        #self.KillDebugThread()
        
        wx.CallAfter(self.UpdateMethodsFromPLCStatus)

    def _SetConnector(self, connector, update_status=True):
        self._connector = connector
        if self.AppFrame is not None:
            self.AppFrame.LogViewer.SetLogSource(connector)
        if connector is not None:
            # Start the status Timer
            self.StatusTimer.Start(milliseconds=500, oneShot=False)
        else:
            # Stop the status Timer
            self.StatusTimer.Stop()
            if update_status:
                wx.CallAfter(self.UpdateMethodsFromPLCStatus)

    def _Connect(self):
        # don't accept re-connetion if already connected
        if self._connector is not None:
            self.logger.write_error(_("Already connected. Please disconnect\n"))
            return
        
        # Get connector uri
        uri = self.\
              BeremizRoot.\
              getURI_location().\
              strip()

        # if uri is empty launch discovery dialog
        if uri == "":
            try:
                # Launch Service Discovery dialog
                dialog = DiscoveryDialog(self.AppFrame)
                answer = dialog.ShowModal()
                uri = dialog.GetURI()
                dialog.Destroy()
            except:
                self.logger.write_error(_("Local service discovery failed!\n"))
                self.logger.write_error(traceback.format_exc())
                uri = None
            
            # Nothing choosed or cancel button
            if uri is None or answer == wx.ID_CANCEL:
                self.logger.write_error(_("Connection canceled!\n"))
                return
            else:
                self.\
                BeremizRoot.\
                setURI_location(uri)
                self.ChangesToSave = True
                if self._View is not None:
                    self._View.RefreshView()
                if self.AppFrame is not None:
                    self.AppFrame.RefreshTitle()
                    self.AppFrame.RefreshFileMenu()
                    self.AppFrame.RefreshEditMenu()
                    self.AppFrame.RefreshPageTitles()
                           
        # Get connector from uri
        try:
            self._SetConnector(connectors.ConnectorFactory(uri, self))
        except Exception, msg:
            self.logger.write_error(_("Exception while connecting %s!\n")%uri)
            self.logger.write_error(traceback.format_exc())

        # Did connection success ?
        if self._connector is None:
            # Oups.
            self.logger.write_error(_("Connection failed to %s!\n")%uri)
        else:
            self.ShowMethod("_Connect", False)
            self.ShowMethod("_Disconnect", True)
            self.ShowMethod("_Transfer", True)

            self.CompareLocalAndRemotePLC()
            
            # Init with actual PLC status and print it
            self.UpdateMethodsFromPLCStatus()
            if self.previous_plcstate is not None:
                status = _(self.previous_plcstate)
            else:
                status = ""

            #self.logger.write(_("PLC is %s\n")%status)
            
            if self.previous_plcstate in ["Started","Stopped"]:
                if self.DebugAvailable() and self.GetIECProgramsAndVariables():
                    self.logger.write(_("Debugger ready\n"))
                    self._connect_debug()
                else:
                    self.logger.write_warning(_("Debug does not match PLC - stop/transfert/start to re-enable\n"))

    def CompareLocalAndRemotePLC(self):
        if self._connector is None:
            return
        # We are now connected. Update button status
        MD5 = self.GetLastBuildMD5()
        # Check remote target PLC correspondance to that md5
        if MD5 is not None:
            if not self._connector.MatchMD5(MD5):
#                self.logger.write_warning(
#                   _("Latest build does not match with target, please transfer.\n"))
                self.EnableMethod("_Transfer", True)
            else:
#                self.logger.write(
#                   _("Latest build matches target, no transfer needed.\n"))
                self.EnableMethod("_Transfer", True)
                # warns controller that program match
                self.ProgramTransferred()
                #self.EnableMethod("_Transfer", False)
        else:
#            self.logger.write_warning(
#                _("Cannot compare latest build to target. Please build.\n"))
            self.EnableMethod("_Transfer", False)


    def _Disconnect(self):
        self._SetConnector(None)
        
    def _Transfer(self):
        # Get the last build PLC's 
        MD5 = self.GetLastBuildMD5()
        
        # Check if md5 file is empty : ask user to build PLC 
        if MD5 is None :
            self.logger.write_error(_("Failed : Must build before transfer.\n"))
            return False

        # Compare PLC project with PLC on target
        if self._connector.MatchMD5(MD5):
            self.logger.write(
                _("Latest build already matches current target. Transfering anyway...\n"))

        # Get temprary directory path
        extrafiles = []
        for extrafilespath in [self._getExtraFilesPath(),
                               self._getProjectFilesPath()]:
        
            extrafiles.extend(
                     [(name, open(os.path.join(extrafilespath, name), 
                                  'rb').read()) \
                      for name in os.listdir(extrafilespath)])
        
        # Send PLC on target
        builder = self.GetBuilder()
        if builder is not None:
            data = builder.GetBinaryCode()
            if data is not None :
                if self._connector.NewPLC(MD5, data, extrafiles) and self.GetIECProgramsAndVariables():
                    self.UnsubscribeAllDebugIECVariable()
                    self.ProgramTransferred()
                    if self.AppFrame is not None:
                        self.AppFrame.CloseObsoleteDebugTabs()
                        self.AppFrame.RefreshPouInstanceVariablesPanel()
                    self.logger.write(_("Transfer completed successfully.\n"))
                else:
                    self.logger.write_error(_("Transfer failed\n"))
            else:
                self.logger.write_error(_("No PLC to transfer (did build succeed ?)\n"))

        wx.CallAfter(self.UpdateMethodsFromPLCStatus)

    StatusMethods = [
        {"bitmap" : "Build",
         "name" : _("Build"),
         "tooltip" : _("Build project into build folder"),
         "method" : "_Build"},
        {"bitmap" : "Clean",
         "name" : _("Clean"),
         "enabled" : False,
         "tooltip" : _("Clean project build folder"),
         "method" : "_Clean"},
        {"bitmap" : "Run",
         "name" : _("Run"),
         "shown" : False,
         "tooltip" : _("Start PLC"),
         "method" : "_Run"},
        {"bitmap" : "Stop",
         "name" : _("Stop"),
         "shown" : False,
         "tooltip" : _("Stop Running PLC"),
         "method" : "_Stop"},
        {"bitmap" : "Connect",
         "name" : _("Connect"),
         "tooltip" : _("Connect to the target PLC"),
         "method" : "_Connect"},
        {"bitmap" : "Transfer",
         "name" : _("Transfer"),
         "shown" : False,
         "tooltip" : _("Transfer PLC"),
         "method" : "_Transfer"},
        {"bitmap" : "Disconnect",
         "name" : _("Disconnect"),
         "shown" : False,
         "tooltip" : _("Disconnect from PLC"),
         "method" : "_Disconnect"},
        {"bitmap" : "ShowIECcode",
         "name" : _("Show code"),
         "shown" : False,
         "tooltip" : _("Show IEC code generated by PLCGenerator"),
         "method" : "_showIECcode"},
    ]

    ConfNodeMethods = [
        {"bitmap" : "editIECrawcode",
         "name" : _("Raw IEC code"),
         "tooltip" : _("Edit raw IEC code added to code generated by PLCGenerator"),
         "method" : "_editIECrawcode"},
        {"bitmap" : "ManageFolder",
         "name" : _("Project Files"),
         "tooltip" : _("Open a file explorer to manage project files"),
         "method" : "_OpenProjectFiles"},
    ]


    def EnableMethod(self, method, value):
        for d in self.StatusMethods:
            if d["method"]==method:
                d["enabled"]=value
                return True
        return False

    def ShowMethod(self, method, value):
        for d in self.StatusMethods:
            if d["method"]==method:
                d["shown"]=value
                return True
        return False

    def CallMethod(self, method):
        for d in self.StatusMethods:
            if d["method"]==method and d.get("enabled", True) and d.get("shown", True):
                getattr(self, method)()
