import os, sys
base_folder = os.path.split(sys.path[0])[0]
sys.path.append(os.path.join(base_folder, "CanFestival-3", "objdictgen"))

from nodelist import NodeList
from nodemanager import NodeManager
import config_utils, gen_cfile
from networkedit import networkedit

class _NetworkEdit(networkedit):
    " Overload some of CanFestival Network Editor methods "
    def OnCloseFrame(self, event):
        " Do reset _NodeListPlug.View when closed"
        self._onclose()
        event.Skip()

class _NodeListPlug(NodeList):
    XSD = """<?xml version="1.0" encoding="ISO-8859-1" ?>
    <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
      <xsd:element name="CanFestivalNode">
        <xsd:complexType>
          <xsd:attribute name="CAN_Device" type="xsd:string" use="required" />
        </xsd:complexType>
      </xsd:element>
    </xsd:schema>
    """

    def __init__(self):
        manager = NodeManager()
        NodeList.__init__(self, manager)
        self.LoadProject(self.PlugPath())

    _View = None
    def _OpenView(self, logger):
        if not self._View:
            def _onclose():
                self.View = None
            self._View = _NetworkEdit()
            self._View._onclose = _onclose
        return self.View
    PluginMethods = [("NetworkEdit",_OpenView)]

    def OnPlugClose(self):
        if self._View:
            self._View.Close()

    def PlugTestModified(self):
        return self.HasChanged()
        
    def OnPlugSave(self):
        self.SaveProject()
        return True

    def PlugGenerate_C(self, buildpath, current_location, locations, logger):
        """
        Generate C code
        @param current_location: Tupple containing plugin IEC location : %I0.0.4.5 => (0,0,4,5)
        @param locations: List of complete variables locations \
            [{"IEC_TYPE" : the IEC type (i.e. "INT", "STRING", ...)
            "NAME" : name of the variable (generally "__IW0_1_2" style)
            "DIR" : direction "Q","I" or "M"
            "SIZE" : size "X", "B", "W", "D", "L"
            "LOC" : tuple of interger for IEC location (0,1,2,...)
            }, ...]
        @return: [(C_file_name, CFLAGS),...] , LDFLAGS_TO_APPEND
        """
        # define a unique name for the generated C file
        prefix = "_".join(map(lambda x:str(x), current_location))
        Gen_OD_path = os.path.join(buildpath, prefix + "_OD.c" )
        # Create a new copy of the model with DCF loaded with PDO mappings for desired location
        master = config_utils.GenerateConciseDCF(locations, current_location, self)
        res = gen_cfile.GenerateFile(Gen_OD_path, master)
        if res :
            raise Exception, res
        
        return [(Gen_OD_path,CanFestival_OD_CFLAGS)],""
    
class RootClass:
    XSD = """<?xml version="1.0" encoding="ISO-8859-1" ?>
    <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
      <xsd:element name="CanFestivalInstance">
        <xsd:complexType>
          <xsd:attribute name="CAN_Driver" type="xsd:string" use="required" />
        </xsd:complexType>
      </xsd:element>
    </xsd:schema>
    """

    PlugChildsTypes = [("CanOpenNode",_NodeListPlug)]
    
    def PlugGenerate_C(self, buildpath, current_location, locations):
        return [],""


