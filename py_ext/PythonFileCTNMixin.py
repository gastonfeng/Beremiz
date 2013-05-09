import os
from PLCControler import UndoBuffer
from PythonEditor import PythonEditor

from xml.dom import minidom
from xmlclass import *
import cPickle

from CodeFileTreeNode import CodeFile

PythonClasses = GenerateClassesFromXSD(os.path.join(os.path.dirname(__file__), "py_ext_xsd.xsd")) 

class PythonFileCTNMixin(CodeFile):
    
    EditorType = PythonEditor
    
    def __init__(self):
        CodeFile.__init__(self)
        
        filepath = self.PythonFileName()
        
        python_code = PythonClasses["Python"]()
        if os.path.isfile(filepath):
            xmlfile = open(filepath, 'r')
            tree = minidom.parse(xmlfile)
            xmlfile.close()
            
            for child in tree.childNodes:
                if child.nodeType == tree.ELEMENT_NODE and child.nodeName == "Python":
                    python_code.loadXMLTree(child, ["xmlns", "xmlns:xsi", "xsi:schemaLocation"])
                    self.CodeFile.globals.settext(python_code.gettext())
                    os.remove(filepath)
                    self.CreateCodeFileBuffer(False)
                    self.OnCTNSave()
    
    def CodeFileName(self):
        return os.path.join(self.CTNPath(), "pyfile.xml")
    
    def PythonFileName(self):
        return os.path.join(self.CTNPath(), "py_ext.xml")

    def GetPythonCode(self):
        current_location = self.GetCurrentLocation()
        # define a unique name for the generated C file
        location_str = "_".join(map(str, current_location))
        
        text = "## Code generated by Beremiz python mixin confnode\n\n"
        
        # Adding includes
        text += "## User includes\n"
        text += self.CodeFile.includes.gettext()
        text += "\n"
        
        # Adding variables
        text += "## User variables reference\n"
        config = self.GetCTRoot().GetProjectConfigNames()[0]
        for variable in self.CodeFile.variables.variable:
            global_name = "%s_%s" % (config.upper(), variable.getname().upper())
            text += "# global_var:%s python_var:%s type:%s initial:%s\n" % (
                global_name,
                variable.getname(),
                variable.gettype(),
                str(variable.getinitial()))
        text += "\n"
        
        # Adding user global variables and routines
        text += "## User internal user variables and routines\n"
        text += self.CodeFile.globals.gettext()
        text += "\n"
        
        # Adding Beremiz confnode functions
        text += "## Beremiz confnode functions\n"
        for func, args, return_code, code_object in [
            ("__init_", "*args, **kwargs", 
             "return 0", self.CodeFile.initFunction),
            ("__cleanup_", "", "", self.CodeFile.cleanUpFunction),
            ("__retrieve_", "", "", self.CodeFile.retrieveFunction),
            ("__publish_", "", "", self.CodeFile.publishFunction),]:
            text += "def %s%s(%s):\n" % (func, location_str, args)
            lines = code_object.gettext().splitlines()
            if len(lines) > 0 or return_code != "":
                for line in code_object.gettext().splitlines():
                    text += "    " + line
                text += "    " + return_code + "\n\n"
            else:
                text += "    pass\n\n"
        
        return text

