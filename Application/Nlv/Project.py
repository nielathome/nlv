#
# Copyright (C) Niel Clausen 2017-2018. All rights reserved.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# 

# Python imports
import glob
import logging
import os
from pathlib import Path
import subprocess
import sys
import traceback
import time
from weakref import ref as MakeWeakRef
import xml.etree.ElementTree as et

# wxWidgets imports
import wx
import wx.stc
import wx.lib.agw.customtreectrl as ctt
import wx.lib.agw.hyperlink as hl

# Content provider interface
import Nlog

# Application imports
from Nlv.Channel import Channel
from .Shell import G_Shell



## PRIVATE #################################################

#-----------------------------------------------------------
class LogForwarder:
    """Forward log/trace messages from Nlog to the Python log system"""

    def debug(self, message):
        logging.debug(message)

    def info(self, message):
        logging.info(message)

    def error(self, message):
        logging.error(message)


#-----------------------------------------------------------
def _Item2Node(item):
    """Fetch a node (item data) from a tree item"""

    node = None
    if item:
        node = item.GetData()
    return node



## G_ProgressMeter #########################################

class G_ProgressMeter:
    """Helper class to display progress information for long running activities"""

    Meter = None
    Count = 0


    #-------------------------------------------------------
    def __init__(self, title):
        if G_ProgressMeter.Count == 0:
            G_ProgressMeter.Meter = self
            G_ProgressMeter.Count = 1
        else:
            G_ProgressMeter.Count += 1

        self._StartTime = time.perf_counter()
        self._Title = title
        self._Dlg = None

    @staticmethod
    def Close():
        G_ProgressMeter.Count -= 1
        if G_ProgressMeter.Count == 0:
            G_ProgressMeter.Meter = None


    #-------------------------------------------------------
    def DoPulse(self, message):
        """After half a second, display meter and start showing progress"""

        if self._Dlg is None:
            now = time.perf_counter()
            if now - self._StartTime > 0.5:
                self._Dlg = wx.ProgressDialog(self._Title, message,
                    style = wx.PD_APP_MODAL | wx.PD_AUTO_HIDE | wx.PD_ELAPSED_TIME
                )

        else:
            self._Dlg.Pulse(message)

    @classmethod
    def Pulse(cls, message):
        instance = cls.Meter
        if instance is not None:
            instance.DoPulse(message)



## G_ProgressMeterScope ####################################

class G_ProgressMeterScope:
    """Context manager (use with "with")."""

    #-------------------------------------------------------
    def __init__(self, title):
        self._Title = title


    #-------------------------------------------------------
    def __enter__(self):
        self._Meter = G_ProgressMeter(self._Title)
        return self


    #-------------------------------------------------------
    def __exit__(self, exc_type, exc_value, exc_traceback):
        self._Meter.Close()




## G_PerfTimer #############################################
           
class G_PerfTimer:
    """Support performance timing of call hierarchies"""

    _Last = None


    #-------------------------------------------------------
    @classmethod
    def GetCurrent(cls):
        return cls._Last


    #-------------------------------------------------------
    def __init__(self, description = "", item_count = 0):
        self._Description = description
        self._Arguments = []
        self._ItemCount = item_count
        self._Timer = Nlog.PerfTimer()
        self._Parent = __class__._Last
        self._Children = []
        self._Closed = False

        if self._Parent is not None:
            self._Parent._AddChild(self)

        __class__._Last = self

        G_ProgressMeter.Pulse(description)


    #-------------------------------------------------------
    def _AddChild(self, child):
        self._Children.append(child)


    #-------------------------------------------------------
    def _Report(self, indent = 0):
        if not self._Closed:
            raise RuntimeError("TimeFunction failed")

        args = ", ".join(self._Arguments)

        inclusive = self._Elapsed
        exclusive = inclusive - sum([timer._Elapsed for timer in self._Children])

        if indent == 0:
            logging.info("{}({}) took {:.2f}s".format(self._Description, args, inclusive))

        per_item_text = ""
        if self._PerItem != 0:
            per_item_text = "per_item:{:.3f}us ".format(self._PerItem)

        if exclusive != inclusive:
            dur_text = "elapsed(inclusive):{:.2f}s elapsed(exclusive):{:.2f}s".format(inclusive, exclusive)
        else:
            dur_text = "elapsed:{:.2f}s".format(inclusive)

        logging.debug("G_PerfTimer: {}{}({}): {} {}".format("|--" * indent, self._Description, args, dur_text, per_item_text))

        for child in self._Children:
            child._Report(indent + 1)


    #-------------------------------------------------------
    def SetItemCount(self, item_count):
        self._ItemCount = item_count


    #-------------------------------------------------------
    def AddArgument(self, arg):
        self._Arguments.append(arg)


    #-------------------------------------------------------
    def Close(self, item_count = 0):
        if not self._Closed:
            self._Closed = True

            if item_count == 0:
                item_count = self._ItemCount

            self._Elapsed = self._Timer.Overall()
            self._PerItem = self._Timer.PerItem(item_count)
            __class__._Last = self._Parent

            if self._Parent is None:
                self._Report()



## G_PerfTimerScope ########################################

class G_PerfTimerScope:
    """
    Context manager (use with "with").
    Time the execution of something
    """

    #-------------------------------------------------------
    def __init__(self, name, item_count = 0):
        self._Name = name
        self._ItemCount = item_count


    #-------------------------------------------------------
    def __enter__(self):
        self._Timer = G_PerfTimer(self._Name)
        return self


    #-------------------------------------------------------
    def __exit__(self, exc_type, exc_value, exc_traceback):
        self._Timer.Close(self._ItemCount)


    #-------------------------------------------------------
    def SetItemCount(self, item_count):
        self._ItemCount = item_count



## G_Const #################################################

class G_Const:
    """GUI constants and defaults"""

    #-------------------------------------------------------

    GlobalThemeCls = "global"
    LogThemeCls = "log"
    ViewThemeCls = "view"
    EventThemeCls = "event"


    #-------------------------------------------------------

    # tracker names are hard coded - they were once read from
    # the first logfile in the session; but that makes little sense
    LocalTrackerName = "(L) Local"

    GlobalTrackerNames = [
        "(G) Global/1",
        "(H) Global/2",
        "(J) Global/3",
        "(K) Global/4",
    ]

    # maximum number of global trackers to persist
    NumGlobalTrackers = len(GlobalTrackerNames)


    #-------------------------------------------------------

    # standard border size for items inside a static box sizer
    Sizer_StdBorder = 4

    # border size for a static box sizer in its parent panel
    Sizer_BoxBorder = 5

    # button size
    ButtonSize = (75, -1)
    ButtonSizeSmall = (60, -1)
    ButtonSizeLarge = (110, -1)
    ButtonSpacer = 5

    # default position for the project panel splitter location
    ProjectInitialSplit = 250
    ProjectMinSplit = 150

    # default container node listbox selector control height
    ListBoxH = 110

    # preferred combo box row height
    ComboRowHeight = 24


    #-------------------------------------------------------

    # application commands
    ID_LOGFILE_NEW_VIEW = wx.ID_HIGHEST + 10
    ID_LOGFILE_NEW_EVENTS = wx.ID_HIGHEST + 11

    ID_NODE_DELETE = wx.ID_HIGHEST + 20
    ID_NODE_SHOWHIDE = wx.ID_HIGHEST + 21

    ID_SESSION_SAVE = wx.ID_HIGHEST + 30
    ID_SESSION_SAVE_AS = wx.ID_HIGHEST + 31

    ID_THEME_ACTIVATE = wx.ID_HIGHEST + 42
    ID_THEME_COPY = wx.ID_HIGHEST + 3
    ID_THEME_DELETE = wx.ID_HIGHEST + 44
    ID_THEME_RENAME = wx.ID_HIGHEST + 45



## G_Global ################################################

class G_Global:

    #-------------------------------------------------------
    def GetConfigDir():
        return wx.ConfigBase.Get().Read("/NLV/DataDir")


    #-------------------------------------------------------
    def MakeCacheDir(base_path, subdir = None):
        if not isinstance(base_path, Path):
            base_path = Path(base_path)

        if not base_path.is_dir():
            base_path = base_path.parent

        cachedir = base_path / ".nlvc"
        if subdir is not None:
            cachedir = cachedir / subdir

        if not cachedir.exists():
            cachedir.mkdir(parents = True)

        return cachedir


    #-------------------------------------------------------
    # hack to stamp strings with metadata
    _MarkMagic = "#<->#"
    _MarkNoDisplay = "nodisplay"

    def MakeMarkPrefix(mark):
        return "{}{}{}".format(G_Global._MarkMagic, mark, G_Global._MarkMagic)

    def MarkString(str, mark = _MarkNoDisplay):
        pfx = G_Global.MakeMarkPrefix(mark)
        return pfx + str

    def IsMarked(str, mark = _MarkNoDisplay):
        # zero = "not marked"
        pfx = G_Global.MakeMarkPrefix(mark)
        sz = len(pfx)
        if str[0:sz] == pfx:
            return sz
        else:
            return 0

    def UnmarkString(str, mark = _MarkNoDisplay):
        return str[G_Global.IsMarked(str):]


    #-------------------------------------------------------
    def FormatTraceback(exc_type, exc_value, exc_traceback):
        message = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        return message

    def FormatLastTraceback():
        return __class__.FormatTraceback(*sys.exc_info())


    #-------------------------------------------------------
    def GetCurrentTimer():
        return G_PerfTimer.GetCurrent()

    def TimeFunction(func):
        """
        Decorator to allow function/method execution times to
        be recorded and logged.
        """
        def TimeFunctionWrapper(*args, **kwargs):
            with G_PerfTimerScope(func.__qualname__):
                return func(*args, **kwargs)

        return TimeFunctionWrapper


    #-------------------------------------------------------
    def PulseProgressMeter(message):
        G_ProgressMeter.Pulse(message)

    def ProgressMeter(func):
        """
        Decorator to allow permit a progress meter to be
        displayed if teh function runs for more than 0.5s
        """
        def ProgressMeterWrapper(*args, **kwargs):
            with G_ProgressMeterScope("NLV is busy ..."):
                return func(*args, **kwargs)

        return ProgressMeterWrapper


    #-------------------------------------------------------
    def RelPath(path, start = os.curdir):
        # pathlib.relative_to is surprisingly limited; this
        # workaround taken from https://stackoverflow.com/questions/38083555/using-pathlibs-relative-to-for-directories-on-the-same-level
        return Path(os.path.relpath(path, start))



## G_FileDropTarget ########################################

class G_FileDropTarget(wx.FileDropTarget):

    #-------------------------------------------------------
    def __init__(self, handler):
        wx.FileDropTarget.__init__(self)
        self._Handler = handler


    #-------------------------------------------------------
    def OnDropFiles(self, x, y, files):
        return self._Handler(files)



## G_WindowInfo ############################################

class G_WindowInfo:
    """
    Basic information about a window
    """

    #-------------------------------------------------------
    def MakePane(window):
        """(Static) Common routine to create a simple, sized, child pane of 'window'"""
        panel = wx.Panel(window)
        panel.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE))
        sizer = wx.BoxSizer(wx.VERTICAL)
        panel.SetSizer(sizer)
        return G_WindowInfo(sizer, panel)


    #-------------------------------------------------------
    def __init__(self, sizer, window):
        self._Sizer = sizer
        self._Window = window


    #-------------------------------------------------------
    def GetSizer(self):
        return self._Sizer

    def GetWindow(self):
        return self._Window



#-----------------------------------------------------------
def _MakeStaticBoxedPane(parent, label = ""):
    """Common routine to create a static-box sizer"""

    sizer = wx.StaticBoxSizer(wx.VERTICAL, parent.GetWindow(), label = label)

    # set the title font to be bold
    window = sizer.GetStaticBox()
    font = window.GetFont().MakeBold()
    window.SetOwnFont(font)

    return G_WindowInfo(sizer, window)



## G_NodeFactory ###########################################

class G_NodeFactory:
    """
    Generic node factory for interfacing new G_Node instances
    to the G_Project.
    """

    #-------------------------------------------------------
    def __init__(self, factory_id, art_id, class_object):
        self._FactoryID = factory_id
        self._ArtID = art_id
        self._Class = class_object


    #-------------------------------------------------------
    def GetArtID(self):
        return self._ArtID;

    def GetFactoryID(self):
        return self._FactoryID;

    def GetClass(self):
        return self._Class;


    #-------------------------------------------------------
    def MakeNode(self, wproject, witem, name, **kwargs):
        return self.GetClass()(self, wproject, witem, name, **kwargs)


    #-------------------------------------------------------
    def InitPage(self, parent):
        # tell class to build its static page
        self.GetClass().BuildPage(parent)



## G_Node ##################################################

class G_Node:
    """Base class for application data held in the project"""

    _GetThemeId = None


    #-------------------------------------------------------
    @staticmethod
    def BuildSubtitle(parent, text, hilite = False):
        """Helper to add a text title to a node"""
        label = wx.StaticText(parent.GetWindow(), label = text)
        parent.GetSizer().Add(label, flag = wx.TOP | wx.LEFT | wx.RIGHT | wx.EXPAND, border = G_Const.Sizer_StdBorder, userData = "subtitle-{}".format(text))

        if hilite:
            f = label.GetFont()
            label.SetFont(f.Italic())

        return label


    #-------------------------------------------------------
    @staticmethod
    def BuildRow(parent, left, right, name, align = 0, flag = wx.ALL):
        """Helper to build a pair of controls as a resizeable row"""
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        parent.GetSizer().Add(hsizer, flag = flag | wx.EXPAND, border = G_Const.Sizer_StdBorder, userData = "row-{}".format(name))

        ul = "row-left-{}".format(name)
        ur = "row-right-{}".format(name)
        if align == 0:
            # spacer in centre
            hsizer.Add(left, flag = wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, userData = ul)
            hsizer.AddStretchSpacer(1)
            hsizer.Add(right, flag = wx.ALIGN_CENTER_VERTICAL, userData = ur)

        elif align < 0:
            # overall, right align
            hsizer.AddStretchSpacer(1)
            hsizer.Add(left, flag = wx.ALIGN_CENTER_VERTICAL, userData = ul)
            hsizer.AddSpacer(G_Const.ButtonSpacer)
            hsizer.Add(right, flag = wx.ALIGN_CENTER_VERTICAL, userData = ur)

        else:
            # overall, left align
            hsizer.Add(left, flag = wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, userData = ul)
            hsizer.AddSpacer(G_Const.ButtonSpacer)
            hsizer.Add(right, flag = wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, userData = ur)
            hsizer.AddStretchSpacer(1)

        return hsizer


    @staticmethod
    def BuildLabelledRow(parent, name, control, flag = wx.ALL):
        """Helper to build a labelled control as a resizeable row"""
        label = wx.StaticText(parent.GetWindow(), label = name)
        return __class__.BuildRow(parent, label, control, name, flag = flag)


    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem):
        self._Factory = factory
        self._WProject = wproject
        self._WItem = witem
        self._Document = None
        self._Initialising = True

    def PostInitNode(self):
        """
        Second stage initialisation; project tree is now setup and document
        data is available. Child nodes not yet created.
        """
        pass

    def PostInitChildren(self):
        """
        Third stage initialisation; project tree under this node is now
        setup and document data is available. Child nodes have been created.
        """
        pass

    def PostInitLoad(self):
        """
        Fourth stage initialisation; project tree is now setup and document
        data is available. All nodes have been created.
        """
        pass

    def PostInitLayout(self):
        """
        All node displays have been created and the AUI perspective activated.
        """
        pass


    #-------------------------------------------------------
    def DoClose(self, delete):
        """Release external resources for this node; overridden where needed"""
        self.DetachDocument()

    def Close(self, delete = False):
        """Close node in the project"""

        for node in self.ListSubNodes(recursive = True, include_self = True):
            node.DoClose(delete)


    #-------------------------------------------------------
    def NotifyPreSave(self):
        """A save has been requested; perform any tasks that must be completed before the save takes place"""
        pass


    #-------------------------------------------------------
    def GetArtID(self):
        return self._Factory.GetArtID()

    def GetAuiManager(self):
        return self.GetProject().GetAuiManager()

    def GetCurrentThemeId(self, theme_cls):
        if G_Node._GetThemeId is None:
            from .Document import GetThemeId
            G_Node._GetThemeId = GetThemeId

        return G_Node._GetThemeId(self, theme_cls)

    def GetDocument(self):
        return self._Document

    def GetTrItem(self):
        """Fetch the GUI Tree control item; guaranteed to be a GenericTreeItem"""
        item = self._WItem()
        if isinstance(item, ctt.GenericTreeItem):
            return item
        else:
            return None

    def GetHrItem(self):
        """Fetch the hierarchy item; may be a GenericTreeItem, else something similar"""
        return self._WItem()

    def GetFrame(self):
        return self.GetProject().GetFrame()

    def GetFactoryID(self):
        return self._Factory.GetFactoryID()

    def GetIndex(self):
        """Return the index of this child within the parent container"""
        return self.GetParentNode().GetHrItem().GetChildIndex(self)

    def GetNodeName(self):
        return self.GetHrItem().GetText()

    def GetAuiNotebook(self):
        return self.GetProject().GetAuiNotebook()

    def GetProject(self):
        return self._WProject()

    def GetRootNode(self):
        return self.GetProject().GetRootNode()

    def GetSizer(self):
        """Fetch the sizer that contains the node's GUI elements"""
        # class variable
        return self._Sizer

    def SetNodeHelp(self, title, relative_url, section = ""):
        self.GetProject().SetNodeHelp(title, relative_url, section)


    #-------------------------------------------------------
    def Activate(self):
        """
        Null implementation for node activation. Derived classes
        should update their GUI page controls with the correct data
        """
        pass


    #-------------------------------------------------------
    def _CopyDocument(self, template, document):
        """
        Recursively copy field and object XML elements from the
        template to the document
        """
        for field in template.iterfind("field"):
            et.SubElement(document, field.tag, field.attrib).text = field.text

        for object in template.iterfind("object"):
            subdoc = et.SubElement(document, object.tag, object.attrib)
            subdoc.text = object.text
            self._CopyDocument(object, subdoc)

    def _BuildDocument(self, template, name):
        """Build and attach a new document element, copied from template"""

        # deep copy of field values from the template
        document = et.Element("node", factory = template.get("factory"), name = name)
        self._CopyDocument(template, document)

        # attach document to this node
        self._Document = document

        # add new document element to parent, to build up document tree
        self.GetParentNode()._Document.append(document)

    def DetachDocument(self):
        """Remove this node's document element from the tree"""
        # special handling the root node
        parent = self.GetParentNode()
        if parent is not None:
            parent._Document.remove(self._Document)
        self._Document = None


    #-------------------------------------------------------
    def RecoverFromBuildNodeError(self, node):
        """Perform error recovery when node building fails"""
        pass

    def BuildChildNode(self, document, copy_defaults, name = None, **kwargs):
        """
        Build a new child node (tree) by loading content from 'document'.
        If 'document' is the default template, then also set 'copy_defaults'
        to True to copy the template data into the user document.
        """
        # determine the node's name
        if name is None:
            name = document.get("name")

        node = None
        try:
            # create and add the new child into the GUI ...
            # ... except annotation nodes - they are no longer implemented
            factory_id = document.get("factory")
            if factory_id == G_Project.NodeID_Annotation:
                return None

            node = self.AttachNode(factory_id, self, name, copy_defaults = copy_defaults, **kwargs)

            # if building a new document tree (from a template), do so now
            if copy_defaults:
                node._BuildDocument(document, name)
            else:
                node._Document = document

            # offer second stage initialisation to the node
            node.PostInitNode()

            # where defined, add children as well
            for child in document.iterfind("node"):
                node.BuildChildNode(child, copy_defaults, **kwargs)

            # offer third stage initialisation to the node
            node.PostInitChildren()

        except BaseException as ex:
            logging.error("Unable to build node '{}'\n{}".format(name, G_Global.FormatLastTraceback()))
            self.RecoverFromBuildNodeError(node)
            node = None

        return node

    @G_Global.TimeFunction
    def DoBuildNode(self, document, copy_defaults, name, **kwargs ):
        """Common node building implementation; GUI is frozen"""
        new_node = self.BuildChildNode(document, copy_defaults, name, **kwargs)

        # final offers of initialisation to document nodes; the
        # whole tree is now built
        if new_node is not None:
            for node in new_node.ListSubNodes(recursive = True, include_self = True):
                node.PostInitLoad()
                node._Initialising = False

            # again, but parents are called before their children (breadth-first)
            for node in new_node.ListSubNodes(recursive = True, depth_first = False, include_self = True):
                node.PostInitLayout()

        return new_node

    def BuildNode(self, document, copy_defaults, name, **kwargs ):
        """Common node building implementation"""

        # freeze frame to avoid GUI flicker
        return self.WithFrameLocked(self.DoBuildNode, document, copy_defaults, name, **kwargs )

    def BuildNodeFromDefaults(self, factory_id, name, **kwargs):
        """
        Recusively create UI child nodes, using the structural and
        other data from _defaults.xml.
        """

        # find template entry
        xpath = "./node[@factory='{}']".format(factory_id)
        template = self.GetProject().GetDefaults().find(xpath)
        return self.BuildNode(template, True, name, **kwargs)

    def BuildNodeFromDocument(self, document, name, **kwargs):
        """
        Recusively create UI child nodes, using the structural and
        other data from the user provided `document`.
        """
        return self.BuildNode(document, False, name, **kwargs)


    #-------------------------------------------------------
    def VisitSubNodes(self, call_back, factory_id = None, recursive = False, depth_first = True, include_self = False):
        """
        Call the callback for each child node.

        :param function `call_back`: function to be called. The argument
            passed to this function is the child node.

        :param `factory_id`: only matched children are considered. Set to
            None (default) to match & call all children

        :param `recursive`: Recurse through the child/grandchild tree. Set
            to False to consider direct children only.

        :param `depth_first`: Recursion is depth-first; children are
            processed before their parents. Set to False for breadth-first;
            parents are processed before their children.

        :param `include_self`: include this node in the walk.
        """

        if depth_first:
            for child_item in self.GetHrItem().GetChildren():
                child_node = _Item2Node(child_item)
                if child_node is None:
                    return
    
                # depth first - descend into grand-children first
                if recursive:
                    child_node.VisitSubNodes(call_back, factory_id, recursive, depth_first)

                # then action the child
                if factory_id is None or child_node.GetFactoryID() == factory_id:
                    call_back(child_node)

            # and finally, this node
            if include_self:
                call_back(self)

        else:
            if include_self:
                call_back(self)

            for child_item in self.GetHrItem().GetChildren():
                child_node = _Item2Node(child_item)
                if child_node is None:
                    return
    
                # action the child first
                if factory_id is None or child_node.GetFactoryID() == factory_id:
                    call_back(child_node)

                # breadth first - descend into grand-children last
                if recursive:
                    child_node.VisitSubNodes(call_back, factory_id, recursive, depth_first)


    #-------------------------------------------------------
    def ListSubNodes(self, factory_id = None, recursive = False, depth_first = True, include_self = False):
        """
        Return a list of child nodes.

        :param `factory_id`: only matched children are considered. Set to
        None (default) to match all children

        :param `recursive`: depth first recusrion through the child/grandchild tree.

        :param `include_self`: include this node in the walk.
        """

        ret = []

        def Work(node):
            ret.append(node)
        self.VisitSubNodes(Work, factory_id, recursive, depth_first, include_self)

        return ret


    #-------------------------------------------------------
    def GetChildNode(self, index):
        """
        Find a child node by index.

        :return: The `index`'th child node, or `None` if `index` is out of range.
        """

        item = self.GetHrItem()
        if index >= item.GetChildrenCount():
            return None
        else:
            return _Item2Node(item.GetChildren()[index])


    #-------------------------------------------------------
    def FindChildNode(self, factory_id, recursive = False):
        """Find a (single) child node by its factory ID."""

        nodes = self.ListSubNodes(factory_id, recursive)
        if len(nodes) == 1:
            return nodes[0]
        else:
            return None


    #-------------------------------------------------------
    def GetParentNode(self, factory_id_or_class = None):
        """
        Fetch our parent node. If factory_id_or_class is provided,
        then recurse until the identified parent/grandparent is found.
        """

        # implement as recursive algorithm, in case GetParentNode
        # is ever over-ridden
        parent = _Item2Node(self.GetHrItem().GetParent())
        if parent is None or factory_id_or_class is None:
            return parent
        else:
            if isinstance(factory_id_or_class, str):
                # -> factory_id
                if parent.GetFactoryID() == factory_id_or_class:
                    return parent

            elif isinstance(parent, factory_id_or_class):
                # -> _or_class
                return parent

            # no takers, recurse
            return parent.GetParentNode(factory_id_or_class)


    #-------------------------------------------------------
    def CreatePopupMenu(self, handlers):
        """The tree node has been clicked, create a popup menu"""
        return None


    #-------------------------------------------------------
    def OnThemeChange(self, theme_cls, theme_id):
        """
        The theme has changed. The node should respond by updating
        its UI to reflect the new themed field values. The event is
        sent to relevent nodes when a theme is activated, or to all
        nodes when a theme is saved.
        """
        pass

    def IsThemeApplicable(self, theme_cls, theme_id, applicable_theme_cls):
        """
        Compare the theme_cls/theme_id to applicable_theme_cls. Return
        True only when there is an exact match, and False otherwise.
        The node's current theme ID for the given theme class is looked
        up by the document. Use this to filter out expensive OnThemeChange()
        events.
        """
        if theme_cls != applicable_theme_cls:
            return False
        elif theme_id is None:
            return True
        else:
            return self.GetCurrentThemeId(theme_cls) == theme_id


    def GetThemeOverrides(self, theme_cls, domain):
        """Identify field values which override the current theme"""
        return []

    def SaveOverridesToTheme(self, theme_cls, domain):
        pass

    def ClearThemeOverrides(self, theme_cls, domain, notify):
        pass


    #-------------------------------------------------------
    def NotifyThemeChange(self, theme_cls, theme_id):
        """
        The theme has changed; notify all theme participants.
        Recommended that the caller hold a frame lock to prevent
        UI flicker.
        """
        for node in self.ListSubNodes(recursive = True):
            node.OnThemeChange(theme_cls, theme_id)


    #-------------------------------------------------------
    def Rebind(self, control, event, handler):
        """Helper to rebind a control's event handler"""
        control.Unbind(event)
        control.Bind(event, handler)


    #-------------------------------------------------------
    def WithFrameLocked(self, func, *args, **kwargs):
        frame = self.GetFrame()
        frame.Freeze()

        try:
            res = func(*args, **kwargs)
        finally:
            frame.Thaw()

        return res


    #-------------------------------------------------------
    def AppError(self, message):
        """A 'significant' error has occurred; make sure the user is aware of it"""
        logging.error(message)
        wx.MessageBox(message, "NLV Error", style= wx.OK | wx.CENTRE | wx.ICON_ERROR | wx.STAY_ON_TOP)



## G_TreeNode ##############################################

class G_TreeNode(G_Node):
    """Base class for application data held in the project tree control"""

    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem):
        super().__init__(factory, wproject, witem)


    #-------------------------------------------------------
    def GetTree(self):
        return self.GetProject().GetTree()


    #-------------------------------------------------------
    def AttachNode(self, factory_id, parent_node, name, **kwargs):
        return self.GetProject().AttachNode(factory_id, parent_node, name, **kwargs)


    #-------------------------------------------------------
    def MakeActive(self):
        """Ensure that this node is the tree's active node"""
        return G_TreeNode.ActivateChild(self)


    def ActivateChild(self, child = None):
        """Ensure the named child is active in the tree; return True if no change made"""
        selected = self.GetTrItem().IsSelected()
        if not selected:
            self.Select()
        return selected 


    #-------------------------------------------------------
    def EnableTree(self, enable):
        self.GetTree().EnableItem(self.GetTrItem(), enable)

    def ExpandTree(self):
        self.GetTree().Expand(self.GetTrItem())

    def CollapseTree(self):
        self.GetTree().Collapse(self.GetTrItem())


    #-------------------------------------------------------
    def GetTreeLabel(self):
        return self.GetTree().GetItemText(self.GetTrItem())

    def SetTreeLabel(self, text):
        self.GetTree().SetItemText(self.GetTrItem(), text)


    #-------------------------------------------------------
    def Select(self):
        self.GetTree().SelectItem(self.GetTrItem())

    #-------------------------------------------------------
    def OnBeginLabelEdit(self):
        return False

    def OnEndLabelEdit(self, label):
        return False



## G_DeletableTreeNode #####################################

class G_DeletableTreeNode(G_TreeNode):
    """Extend standard tree node with ability to remove itself from the tree"""

    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem):
        super().__init__(factory, wproject, witem)


    #-------------------------------------------------------
    def AppendPopupDeleteNode(self, menu, handlers, separator = False):
        if separator:
            menu.AppendSeparator()

        menu.Append(G_Const.ID_NODE_DELETE, "Remove '{}'".format(self.GetNodeName()))
        handlers[G_Const.ID_NODE_DELETE] = self.OnCmdDelete


    #-------------------------------------------------------
    def _DeleteNode(self):
        # ensure GUI stays clean
        self.GetParentNode().Select()

        # perform orderly closedown of resources
        self.Close(True)

        # remove tree item from tree
        tritem = self.GetTrItem()
        hritem = self.GetParentNode().GetHrItem()
        self.GetProject().DeleteNode(tritem)

        # if parent is a container, remove tree item from container as well
        # hritem will be a GenericTreeItem if our parent node is the root node
        if isinstance(hritem, G_Item):
            if hritem is not tritem:
                hritem.RemoveItem(tritem)

    def RecoverFromBuildNodeError(self, node):
        """Perform error recovery when node building fails"""
        node._DeleteNode()

    def OnCmdDelete(self, event = None):
        self._DeleteNode()



## G_HideableTreeNode ######################################

class G_HideableTreeNode:
    """Extend standard tree node with ability to hide its display(s)"""

    #-------------------------------------------------------
    def PostInitHideableTreeNode(self):
        self._Field.Add(True, "ShowThisNodeDisplay", replace_existing = False)
        self.UpdateNodeDisplay()
        self.UpdateTreeDisplay()


    #-------------------------------------------------------
    def AppendPopupShowHide(self, menu, handlers, separator = False):
        if separator:
            menu.AppendSeparator()

        action = "Show"
        if self._Field.ShowThisNodeDisplay.Value:
            action = "Hide"

        menu.Append(G_Const.ID_NODE_SHOWHIDE, "{} '{}'".format(action, self.GetNodeName()))
        handlers[G_Const.ID_NODE_SHOWHIDE] = self.OnShowHideCommand


    def OnShowHideCommand(self):
        show = not self._Field.ShowThisNodeDisplay.Value

        # if hiding, clear any pending display window refocus events
        # as they arrive after the AUI tab is hidden, causing it to re-display
        if not show:
            self.ClearSendFocusToCtrl()

        # show/hide the display tab for this node
        self.SetThisNodeDisplay(show)

        # show/hide the display tab for all child nodes
        for node in self.ListSubNodes(recursive = True, include_self = False):
            if isinstance(node, G_HideableTreeNode):
                node.SetParentNodeDisplay(show)
            elif isinstance(node, G_HideableTreeChildNode):
                node.UpdateTreeDisplay()

        # show/hide the panel controls
        self.ShowHideChildNodes(show)

        return True


    #-------------------------------------------------------
    def UpdateNodeDisplay(self):
        pass


    def UpdateTreeDisplay(self):
        enabled = self.IsParentNodeDisplayed()

        # determine whether the node responds in the UI
        self.EnableTree(enabled)

        # expand/collapse our children
        if enabled:
            self.ExpandTree()
        else:
            self.CollapseTree()


    #-------------------------------------------------------
    def IsNodeDisplayed(self):
        return self._Field.ShowThisNodeDisplay.Value and self.IsParentNodeDisplayed()

    def IsParentNodeDisplayed(self):
        # parent's aren't guaranteed to be fully initialised when
        # creating new nodes; so safe to assume the parent node is
        # visible in such cases
        try:
            parent = self.GetParentNode(G_HideableTreeNode)
            if parent is None:
                return True
            else:
                return parent._Field.ShowThisNodeDisplay.Value

        except:
            return True

    def SetThisNodeDisplay(self, show):
        self._Field.ShowThisNodeDisplay.Value = show
        self.UpdateNodeDisplay()
        self.UpdateTreeDisplay()

    def SetParentNodeDisplay(self, show):
        self.UpdateNodeDisplay()
        self.UpdateTreeDisplay()



## G_HideableTreeChildNode #################################

class G_HideableTreeChildNode():
    """Default behaviour for child nodes of a G_HideableTreeNode"""

    #-------------------------------------------------------
    def IsNodeDisplayed(self):
        return self.GetParentNode(G_HideableTreeNode).IsNodeDisplayed()


    #-------------------------------------------------------
    def PostInitHideableTreeNode(self):
        self.UpdateTreeDisplay()


    #-------------------------------------------------------
    def UpdateTreeDisplay(self):
        enabled = self.IsNodeDisplayed()

        # determine whether the node responds in the UI
        self.EnableTree(enabled)

        # expand/collapse our children
        if enabled:
            self.ExpandTree()
        else:
            self.CollapseTree()



## G_RootNode ##############################################

class G_RootNode(G_TreeNode):
    """Root node for the tree; primarily, an invisible container node"""

    #-------------------------------------------------------
    def BuildPage(parent):
        me = __class__
        me._Sizer = parent.GetSizer()
        me._Page = parent


    #-------------------------------------------------------
    def __init__(self, factory_id, wproject, witem, name):
        super().__init__(factory_id, wproject, witem)
        __class__._Page.GetWindow().SetLabel(name)


    #-------------------------------------------------------
    def _IsKnownDocumentVersion(self):
        return self.GetDocument().get("version", 0) == str(G_Shell.NlvDocumentVersion)


    #-------------------------------------------------------
    def LoadNode(self, node_name, document_path = None):
        node = None

        # no document implies create empty tree from template
        if document_path is None:
            self._Document = et.Element("root")
            node = self.BuildNodeFromDefaults(self.GetProject().NodeID_Session, node_name)

        else:
            self._Document = et.parse(document_path).getroot()
            if self._IsKnownDocumentVersion():
                node = self.BuildNodeFromDocument(self._Document.find("node"), node_name)
            else:
                self.AppError("Unable to load this version of NLV document:\n'{}'".format(document_path))

        return node


    #-------------------------------------------------------
    def SaveNode(self, document_path):
        # tell children a Save is about to be performed; gives them the opportunity to
        # update the internal XML document with last minute changes
        for node in self.ListSubNodes(recursive = True, include_self = True):
            node.NotifyPreSave()

        if self._IsKnownDocumentVersion():
            # save the document tree to disk
            et.ElementTree(self.GetDocument()).write(document_path)
        else:
            self.AppError("Unable to save this version of NLV document")


    def NotifyPreSave(self):
        # ensure newly created documents have the right version
        self.GetDocument().set("version", str(G_Shell.NlvDocumentVersion))



## G_ContainedNode #########################################

class G_ContainedNode(G_Node):
    """
    A child node of a G_ContainerNode.
    """

    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem):
        super().__init__(factory, wproject, witem)


    #-------------------------------------------------------
    def MakeActive(self):
        """Ensure that this node is the tree's 'active' node"""
        return self.GetParentNode().ActivateChild(self)



## G_TabContainedNode ######################################

class G_TabContainedNode(G_ContainedNode):
    """
    A child node of a G_TabContainerNode.
    """

    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem):
        super().__init__(factory, wproject, witem)



## G_ListContainedNode #####################################

class G_ListContainedNode(G_ContainedNode):
    """
    A child node of a G_ListContainerNode.
    """

    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem):
        super().__init__(factory, wproject, witem)



## G_ContainerMenu #########################################

class G_ContainerMenu:
    """
    Common popup menu behaviour for windows which contain nodes
    """

    #-------------------------------------------------------
    def OnDisplayPopupMenu(self, window, node):
        """Show, and act on, a right-click 'context sensitive', popup menu"""
        handlers = dict()
        menu = node.CreatePopupMenu(handlers)
        if menu is None:
            return

        # get request from user
        id = window.GetPopupMenuSelectionFromUser(menu)

        # perform the request
        handler = handlers.get(id)
        if handler is not None:
            handler()



## G_ContainerNode #########################################

class G_ContainerNode(G_ContainerMenu):
    """
    Common behaviour for a node which manages its own children, rather than relying
    on a toolkit mechanism.
    """

    #-------------------------------------------------------
    def __init__(self, witem):
        self._HrItem = G_ContainerItem(witem)
        self._CurSelectionIdx = 0


    #-------------------------------------------------------
    def GetHrItem(self):
        """Override G_Node GetHrItem"""
        return self._HrItem


    #-------------------------------------------------------
    def AttachNode(self, factory_id, parent_node, name, **kwargs):
        """Create and attach a new node to the container"""

        # will the new item be a tree, or a container, item
        is_treenode = issubclass(self.GetProject().GetFactory(factory_id).GetClass(), G_TreeNode)

        hritem = self.GetHrItem()
        if is_treenode:
            node = self.GetProject().AttachNode(factory_id, parent_node, name, **kwargs)

            # record the new tree item in our tree node item wrapper as well (double accounting)
            hritem.AppendItem(node.GetTrItem())

        else:
            # create an item to host the child node
            item = G_ContainedItem(self._WItem, name)

            # create the node
            node = self.GetProject().MakeNode(factory_id, item, name, **kwargs)

            # and record the new contained item in our tree node item wrapper
            hritem.AppendItem(item)

        return node


    #-------------------------------------------------------
    def SwitchSubpage(self, new_idx, page):
        page_window = page.GetWindow()
        page_sizer = page.GetSizer()
        page_window.Freeze()

        node_sizer = None
        if new_idx >= 0:
            self._CurSelectionIdx = new_idx

            new_node = self.GetChildNode(new_idx)
            if new_node:
                node_sizer = new_node.GetSizer()
                page_sizer.Show(node_sizer, True)
                new_node.Activate()

        # it seems that since the sub-page sizers are specified with "EXPAND" that
        # whenever one of them is hidden, the others are expanded to fill the void;
        # so hide all unwanted sub-page sizers in one pass, which is after the wanted
        # sub-page sizer is known to be visible
        for sizer_item in page_sizer.GetChildren():
            child_sizer = sizer_item.GetSizer()
            if child_sizer and child_sizer is not node_sizer:
                page_sizer.Show(child_sizer, False)

        page_sizer.Layout()
        page_window.Thaw()


    #-------------------------------------------------------
    def OnSelectorRightClick(self, event):
        """A subpage has been right clicked in the list"""
        self.OnDisplayPopupMenu(self._SubpageSelector, self.GetChildNode(self._CurSelectionIdx))



## G_TabContainerNode ######################################

class G_TabContainerNode(G_ContainerNode, G_DeletableTreeNode):
    """
    A tree node whose children are attached to a child tab/toolbar control,
    rather than being direct children of this tree node.
    """

    #-------------------------------------------------------
    def BuildPage(parent):
        # class static function
        me = __class__
        me._Sizer = parent.GetSizer()
        me._Page = parent

        # the toolbar control does strange things to postition itself within its
        # parent window; isolate it from the box window by placing it in its own
        # panel
        toolbar_pane = G_WindowInfo.MakePane(me._Page.GetWindow())
        me._Page.GetSizer().Add(toolbar_pane.GetWindow(), flag = wx.ALL | wx.EXPAND, border = G_Const.Sizer_StdBorder, userData = "TabContainerNode-toolbar-pane" )

        # create toolbar control which will select sub-pages
        gui = me._SubpageSelector = wx.ToolBar(toolbar_pane.GetWindow(), style = wx.TB_FLAT
            | wx.TB_HORIZONTAL
            | wx.TB_NODIVIDER
            | wx.TB_TEXT
            | wx.TB_NO_TOOLTIPS
        )
        toolbar_pane.GetSizer().Add(gui, flag = wx.EXPAND, userData = "TabContainerNode-toolbar")

        me._ButtonSize = (16, 16)
        gui.SetToolBitmapSize(me._ButtonSize)

        return me._Page


    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem):
        G_ContainerNode.__init__(self, witem)
        G_DeletableTreeNode.__init__(self, factory, wproject, witem)


    #-------------------------------------------------------
    def IsNodeDisplayed(self):
        return True

    def IsParentNodeDisplayed(self):
        return True

    def ActivateContainer(self):
        gui = self._SubpageSelector
        gui.Unbind(wx.EVT_TOOL_RANGE)
        gui.Unbind(wx.EVT_TOOL_RCLICKED_RANGE)

        # add children as toolbar buttons on the toolbar
        gui.ClearTools()

        if self.IsNodeDisplayed():
            id = 0
            for node in self.ListSubNodes():
                if isinstance(node, G_ContainedNode):
                    art_id = node.GetArtID()
                    bitmap =  wx.ArtProvider.GetBitmap(art_id, wx.ART_TOOLBAR, self._ButtonSize)
                    gui.AddTool(id, node.GetNodeName(), bitmap, kind = wx.ITEM_RADIO)
                    id += 1

            gui.Realize()
            gui.Bind(wx.EVT_TOOL_RANGE, self.OnSubpageSelect, id = 0, id2 = id - 1)
            gui.Bind(wx.EVT_TOOL_RCLICKED_RANGE, self.OnSelectorRightClick, id = 0, id2 = id - 1)

            self._SubpageSelector.ToggleTool(self._CurSelectionIdx, True)
            self.SwitchSubpage(self._CurSelectionIdx, self._Page)

        else:
            gui.Realize()
            self.SwitchSubpage(-1, self._Page)


    #-------------------------------------------------------
    def OnSubpageSelect(self, event):
        self.SwitchSubpage(event.GetId(), self._Page)


    #-------------------------------------------------------
    def ShowHideChildNodes(self, show):
        self.ActivateContainer()



## G_ListContainerNode #####################################

class G_ListContainerNode(G_ContainerNode, G_TabContainedNode):
    """
    A tree node whose children are attached to a child combo/listbox control,
    rather than being direct children of this tree node.
    """

    #-------------------------------------------------------
    def BuildPage(parent):
        # class static function
        me = __class__
        me._Sizer = parent.GetSizer()
        me._Page = parent

        # create control which will select sub-pages; could be combo or list
        me._SubpageSelector = wx.ListBox(parent.GetWindow(), size = (-1, G_Const.ListBoxH), style = wx.LB_SINGLE)
        me._Sizer.Add(me._SubpageSelector, flag = wx.ALL | wx.EXPAND, border = G_Const.Sizer_StdBorder, userData = "ListContainerNode-list")

        return parent


    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem):
        G_ContainerNode.__init__(self, witem)
        G_TabContainedNode.__init__(self, factory, wproject, witem)


    #-------------------------------------------------------
    def ActivateContainer(self):
        gui = self._SubpageSelector
        gui.Unbind(wx.EVT_LISTBOX)

        gui.Clear()
        for node in self.ListSubNodes():
            gui.Append(node.GetNodeName())

        self.Rebind(gui, wx.EVT_RIGHT_DOWN, self.OnSelectorRightClick)
        gui.Bind(wx.EVT_LISTBOX, self.OnSubpageSelect)

        self.SetSelection(self._CurSelectionIdx)

        s = gui.GetCharHeight()
        s = s * gui.GetCount() + 5
        gui.SetInitialSize( (-1, s) )


    #-------------------------------------------------------
    def MakeActive(self):
        """Ensure the this node is the tree's active node"""
        return self.GetParentNode().ActivateChild(self)


    #-------------------------------------------------------
    def ActivateChild(self, child):
        """Ensure the named child is active in the tree"""
        subpage_idx = self.GetHrItem().GetChildIndex(child)
        selected = subpage_idx == self._CurSelectionIdx
        if not selected:
            self._CurSelectionIdx = subpage_idx
            if self.MakeActive():
                self.SetSelection(subpage_idx)
        else:
            self.MakeActive()

        return selected


    #-------------------------------------------------------
    def SetSelection(self, new_idx):
        """Set selection in selector control and force through sub-page switch"""
        self._SubpageSelector.SetSelection(new_idx)
        self.SwitchSubpage(new_idx, self._Page)

    #-------------------------------------------------------
    def OnSubpageSelect(self, event):
        self.SwitchSubpage(event.GetInt(), self._Page)



## G_Item ##################################################

class G_Item:
    """
    Common behaviour for tree items which are not supplied by
    the GUI. Part of bridging/integrating wx.lib.agw.customtreectrl
    with "non-tree" nodes
    """

    #-------------------------------------------------------
    def __init__(self):
        self._Children = []


    #-------------------------------------------------------
    def AppendItem(self, item):
        self._Children.append(item)

    def RemoveItem(self, item):
        self._Children.remove(item)
        

    #-------------------------------------------------------
    def GetChildren(self):
        return self._Children

    def GetChildrenCount(self):
        return len(self._Children)


    #-------------------------------------------------------
    def GetChildIndex(self, child):
        """Return the index of this child within the parent container"""

        # essentially a search through our children; due to the mixed item
        # types in a given tree, identification is performed by node comparison
        idx = 0
        for item in self.GetChildren():
            if child is _Item2Node(item):
                return idx
            else:
                idx += 1

        return None



## G_ContainerItem #########################################

class G_ContainerItem(G_Item):
    """
    A wrapper to extend a wx.lib.agw.customtreectrl.GenericTreeItem
    with extra behaviour - to bridge children from the subpage
    """

    #-------------------------------------------------------
    def __init__(self, witem):
        super().__init__()
        self._WItem = witem


    #-------------------------------------------------------
    def GetData(self):
        return self._WItem().GetData()

    def GetParent(self):
        return self._WItem().GetParent()

    def GetText(self):
        return self._WItem().GetText()

    def SetData(self, data):
        self._WItem().SetData(data)



## G_ContainedItem #########################################

class G_ContainedItem(G_Item):
    """
    A leaf item providing a wx.lib.agw.customtreectrl.GenericTreeItem
    compatible interface for use with G_ContainedNode/G_ContainerNode.
    """

    #-------------------------------------------------------
    def __init__(self, wparent, text):
        super().__init__()
        self._WParent = wparent
        self._Text = text


    #-------------------------------------------------------
    def GetData(self):
        return self._Data

    def GetParent(self):
        return self._WParent()

    def GetText(self):
        return self._Text

    def SetData(self, data):
        self._Data = data



## G_Project ###############################################

class G_Project(wx.SplitterWindow, G_ContainerMenu):
    """Class that implements the project control panel"""

    #-------------------------------------------------------

    # static constants, define the node IDs
    NodeID_Root = "-1"

    NodeID_Session = "54509DB4-0B33-4C2E-AC17-B027581823E5"
    NodeID_SessionManager = "FE21291F-572A-483B-8CF3-48D8B90F0173"
    NodeID_OpenLog = "48A56F4F-CD92-4302-A33E-90222A30F994"
    NodeID_SessionTrackerOptions = "AD2DCFB5-0433-44DB-9942-CC0CB5F89984"
    NodeID_GlobalThemeGallery = "2EF2160F-7BE1-4194-8C4A-D5415AD1985E"
    NodeID_Annotation = "795850FA-628A-47CC-8EDB-B7340CBC7573"

    NodeID_Log = "27813739-0E75-4140-B34B-97EE2BE003EE"
    NodeID_OpenView = "CF97CE28-0773-431D-960D-E249B818C636"
    NodeID_MarkerContainer = "2057A308-7C8C-4208-852E-0F598BF748F0"
    NodeID_Marker = "9BB5F8EC-41E4-4C43-8B3F-0A48EDCF7350"
    NodeID_TrackerContainer = "5D604D98-10F8-4877-8A0B-F8BDBAFDE982"
    NodeID_Tracker = "90495B34-5BDB-45AF-93B7-2BF104B6B953"
    NodeID_LogInfo = "680427E7-93EE-4B23-9157-289E87F14B4D"
    NodeID_LogGlobalThemeOverrides = "E918B7F2-DF2A-4C55-AD84-BE96B29CF6D5"
    NodeID_LogLocalThemeGallery = "50DF4F78-2819-4B02-BE9F-0C423812FB64"
    NodeID_LogLocalThemeOverrides = "F35A20DF-F009-4EE2-8207-532F65F712CA"
    NodeID_LogThemeContainer = "87C9B29A-DF06-4EC1-8966-45D51D827AAD"

    NodeID_View = "B6903A1F-2DE6-436C-BC35-B2B03AF78203"
    NodeID_ViewSearchContainer = "17D31FC0-7E8F-42A3-BF5E-532831C50832"
    NodeID_ViewSearch = "0465EF17-347D-4719-91C4-F8494B9C7DE6"
    NodeID_ViewFilter = "6968149A-D9DA-47AF-A742-2C75A1D16720"
    NodeID_ViewTracking = "8481271C-B31B-4C29-AEE5-2AED0905DFF5"
    NodeID_ViewField = "6F3C11E5-3148-41C0-83C8-329BB94C6C0F"
    NodeID_ViewOptions = "DA314384-660D-4B6C-8CBE-40196A30DA08"
    NodeID_ViewGlobalThemeOverrides = "B6326018-3AF5-4E41-9BE3-1193811AF439"
    NodeID_ViewLocalThemeGallery = "6494365B-350F-4718-87AC-7DEB80F34340"
    NodeID_ViewLocalThemeOverrides = "9DD0FF9F-7BC5-4DD7-BAA4-4E9F76682795"
    NodeID_ViewThemeContainer = "06BD4FE4-F2C9-47A4-8329-EE0604B9CD8B"

    NodeID_LogAnalysis = "BED0DF17-1A62-4123-8097-0A41E9E23D1C"
    NodeID_AnalyserScript = "F418311C-9449-46DB-A8C5-B6B4F324D3F0"
    NodeID_EventAnalyse = "4AAD05E5-493C-45D9-AD2D-D96D9324E4B5"
    NodeID_LogAnalysisLocalThemeGallery = "DE983334-8D66-42E8-917E-05D5C464DFB4"
    NodeID_LogAnalysisLocalThemeOverrides = "C0F7D466-B02C-4F85-92E1-DA5E7F77CAFE"
    NodeID_LogAnalysisThemeContainer = "AD58B879-F278-476E-9C52-DA886DB2415B"

    NodeID_EventProjector = "90FCCB21-8484-451A-8EB5-DBED816DFE17"
    NodeID_TableSearch = "40C0412B-8AE8-4576-8519-D71BC6DB3C50"
    NodeID_TableSearchContainer = "187B89FD-8E79-4F6C-B513-2211B82B6029"
    NodeID_TableFilter = "9913F5A0-C726-4A4C-974A-B5A92E71ECEB"
    NodeID_EventTracking = "53AD7641-989C-4561-8F56-401DC378BAB6"
    NodeID_EventField = "3DDAF4B3-8B58-496B-888A-855CB78C59ED"
    NodeID_EventProjectorOptions = "85615529-637B-4AD3-BE6D-FDA3C5E6B9DC"

    NodeID_MetricsProjector = "F1BA137E-41B1-4066-95FE-AA5689310209"
    NodeID_MetricsProjectorOptions = "7F164B4B-7276-4F52-89A3-6D90A6C2557E"

    ArtCtrlId_None = -1
    ArtCtrlId_Session = wx.ART_GO_HOME
    ArtCtrlId_Open = wx.ART_FILE_OPEN
    ArtCtrlId_Theme = wx.ART_PASTE
    ArtCtrlId_Markers = wx.ART_HELP_SIDE_PANEL
    ArtCtrlId_Tracker = wx.ART_GO_FORWARD
    ArtCtrlId_Info = wx.ART_INFORMATION
    ArtCtrlId_Search = wx.ART_FIND
    ArtCtrlId_Filter = wx.ART_EXECUTABLE_FILE
    ArtCtrlId_Fields = wx.ART_NEW_DIR
    ArtCtrlId_Script = wx.ART_FIND_AND_REPLACE
    ArtCtrlId_Analyse = wx.ART_REDO
    ArtCtrlId_Options = wx.ART_FILE_SAVE

    ArtDocID_Home = 0
    ArtDocID_Annotation = 1
    ArtDocID_Log = 2
    ArtDocID_View = 3
    ArtDocID_Folder = 4
    ArtDocID_EventProjector = 5
    ArtDocID_MetricsProjector = 6

    # tree item images, order must match ArtID_*
    _ArtIds = [
        wx.ART_GO_HOME,
        wx.ART_HELP_SETTINGS,
        wx.ART_HELP_BOOK,
        wx.ART_NORMAL_FILE,
        wx.ART_FOLDER_OPEN,
        wx.ART_COPY,
        wx.ART_NEW
    ]


    #-------------------------------------------------------

    # the project is a singleton; class and class instance variables
    # are both employed

    # dictionary of G_Nodes registered with the project tree
    _NodeFactories = {}


    #-------------------------------------------------------
    def RegisterNodeFactory(factory):
        """(Static) Register a G_Node provider with the Project"""

        factory_id = factory.GetFactoryID()
        G_Project._NodeFactories[factory_id] = factory


    #-------------------------------------------------------
    @G_Global.TimeFunction
    def __init__(self, parent, frame):
        "Initialise the instance"

        super().__init__(parent, style = wx.SP_LIVE_UPDATE)
        self._Frame = frame
        self._BrowserPath = None

        # integrate Python/C++ performance timing systems
        def PerfTimerFactory(description, item_count):
            return G_PerfTimer(description, item_count)

        # feed Nlog logging back to the application
        _LogForwarder = LogForwarder()
        Nlog.Setup(_LogForwarder, PerfTimerFactory)

        # create a "public" list of the notfication channels for use by receivers
        root = et.Element("root")
        from .Logmeta import GetLogSchemataNames
        from .Logmeta import GetLogSchema
        for (schema_name, schema_guid) in GetLogSchemataNames():
            channel_guid = GetLogSchema(schema_guid).GetChannelGuid()
            if channel_guid is not None:
                et.SubElement(root, "channel", name = schema_name).text = channel_guid
        et.ElementTree(root).write(str(Path(G_Global.GetConfigDir()) / "Channels.xml"))

        # notification channels are created on-demand
        self._Channels = dict()

        # load defaults
        inst_dir = Path(__file__).parent
        self._Defaults = et.parse(inst_dir / "_defaults.xml").getroot()

        # setup themes
        from shutil import copy
        config_dir = Path(G_Global.GetConfigDir())
        for src in glob.glob(str(inst_dir / "theme*.xml")):
            dest = config_dir / Path(src).name
            if not dest.is_file() or (dest.stat().st_mtime < Path(src).stat().st_mtime):
                copy(src, dest)

        # create child controls; general hierarchy for each child window (panel) of
        # the splitter is: panel; panel sizer (provides border surrounding the static
        # box sizer); static box sizer (lays out all controls), and; the controls(s)

        # lower panel: initialise GUI pages for all registered node types and add help box
        self._Panel = self._InitNodePages()

        # frame integration
        self._InitHelp()

        # upper panel: boxed tree control
        tree_pane = G_WindowInfo.MakePane(self)
        (self._Tree, self._RootNode) = self._InitProjectTree(tree_pane)
        tree_pane.GetSizer().Add(self._Tree, flag = wx.ALL | wx.EXPAND, border = G_Const.Sizer_StdBorder, proportion = 1, userData = "Project-tree")

        # make the split
        self.SplitHorizontally(tree_pane.GetWindow(), self._Panel.GetWindow(), G_Const.ProjectInitialSplit)


    #-------------------------------------------------------
    def _InitProjectTree(self, parent):
        # build the image list
        image_list = wx.ImageList(16, 16)
        for icon in self._ArtIds:
            image_list.Add(wx.ArtProvider.GetBitmap(icon, wx.ART_TOOLBAR, (16, 16)))

        # create the tree control
        tree = ctt.CustomTreeCtrl(
            parent.GetWindow(),
            style = wx.BORDER_SIMPLE,
            agwStyle = ctt.TR_HAS_BUTTONS | ctt.TR_HIDE_ROOT | ctt.TR_EDIT_LABELS
        )
        tree.AssignImageList(image_list)
        tree.SetBackgroundColour(wx.WHITE)

        # event handling
        tree.Bind(ctt.EVT_TREE_BEGIN_LABEL_EDIT, self.OnBeginLabelEdit)
        tree.Bind(ctt.EVT_TREE_END_LABEL_EDIT, self.OnEndLabelEdit)
        tree.Bind(ctt.EVT_TREE_SEL_CHANGED, self.OnSelChanged)
        tree.Bind(ctt.EVT_TREE_ITEM_RIGHT_CLICK, self.OnRightClick)

        # create the root item
        name = "Project"
        root = tree.AddRoot(name)
        root_node = self.MakeNode(self.NodeID_Root, root, name)

        # create drop handler
        from .Session import GetSessionManager
        tree.SetDropTarget(G_FileDropTarget(GetSessionManager().OnDropFiles))
        return (tree, root_node)


    #-------------------------------------------------------
    @G_Global.TimeFunction
    def _InitNodePages(self):
        """Ensure G_Nodes are notified to build their GUI pages"""

        # the (mostly invisible) outer panel
        page = G_WindowInfo.MakePane(self)
        sizer = page.GetSizer()

        idx_root = 0
        hierarchy = []
        hierarchy.append(page)
        
        # node container classes initialised once, as container GUI elements
        # managed via common base class static members

        def AddContainerPage(parent, page_builder, userData):
            page_sizer = wx.BoxSizer(wx.VERTICAL)
            parent.GetSizer().Add(page_sizer, flag = wx.EXPAND, proportion = 1, userData = userData)
            pane = G_WindowInfo(page_sizer, parent.GetWindow())
            hierarchy.append(page_builder(pane))
            parent.GetSizer().Show(page_sizer, False)

        idx_tab = 1
        AddContainerPage(page, G_TabContainerNode.BuildPage, "Project-tab-container")

        idx_list = 2
        AddContainerPage(hierarchy[idx_tab], G_ListContainerNode.BuildPage, "Project-list-container")

        # non-container nodes

        def AddLeafPage(hierarchy_idx, factory):
            parent = hierarchy[hierarchy_idx]
            page_sizer = wx.BoxSizer(wx.VERTICAL)

            parent.GetSizer().Add(page_sizer, flag = wx.EXPAND, proportion = 1, userData = "Project-factory-{}".format(factory.GetFactoryID()))
            factory.InitPage(G_WindowInfo(page_sizer, parent.GetWindow()))
            parent.GetSizer().Show(page_sizer, False)

        for factory_id in self._NodeFactories.keys():
            factory = self._NodeFactories[factory_id]
            cls = factory.GetClass()

            if issubclass(cls, G_ContainerNode):
                pass
            elif issubclass(cls, G_TabContainedNode):
                AddLeafPage(idx_tab, factory)
            elif issubclass(cls, G_ListContainedNode):
                AddLeafPage(idx_list, factory)
            else:
                AddLeafPage(idx_root, factory)

        return page


    #-------------------------------------------------------
    def _GetURL(self, relative_url, section = ""):
        """Convert relative URL to absolute URL"""

        # allow documentation to live in a couple of "well known" places
        file_path = Path( __file__ ).parent.joinpath("Sphinx", "html")
        if not file_path.exists():
            file_path = Path( __file__ ).parent.parent.parent.joinpath("_Work", "Stage", "Nlv", "Sphinx", "html")
        if not file_path.exists():
            file_path = Path("missing_doc")

        url = file_path.joinpath(relative_url).as_uri()
        if section != "":
            url = "{0}#{1}".format(url, section)

        return url

    def _OnURL(self, event):
        #
        # Although the anchor is appended to the URL, there is a feature in the Windows
        # Shell API that effectively ignores it. From https://stackoverflow.com/questions/6374761/python-webrowser-open-url-with-bookmarks-like-www-something-com-file-htmltop:
        #
        #    "... On Windows, when trying to use the default browser, it uses os.startfile()
        #    which in turn uses the win32 ShellExecute api. ShellExecute can be used to perform
        #    certain actions on a file, folder or URL, like "open", "edit" or "print" with its
        #    default application. In this case, ShellExecute is asked to "open" the URL.
        #   
        #    It seems however, that ShellExecute ignores the fragment identifier (the part
        #    after #) when opening file: urls. Strangely enough, this is not the case with
        #    http:urls. Presumably, a file: url is just converted to a plain filename first."
        #
        # To workaround this, where possible, run the browser directly
        #

        help = event.EventObject
        url = help.GetURL()
        if self._BrowserPath is not None:
            cmd = self._BrowserPath.replace("%1", url)
            subprocess.Popen(cmd)
        else:
            help.GotoURL(url)

    def _AddHelpLink(self, title, relative_url, section = ""):
        """Add a documentation link to the documentation container"""

        help = hl.HyperLinkCtrl(self._HelpPanel.GetWindow(), wx.ID_ANY,
            label = title,
            URL = self._GetURL(relative_url, section)
        )

        # set properties
        help.EnableRollover(True)
        help.SetUnderlines(False, False, True)
        help.SetColours("BLUE", "BLUE", "RED")
        help.OpenInSameWindow(True)
        self._HelpPanel.GetSizer().Add(help, flag = wx.ALL, border = G_Const.Sizer_StdBorder, userData = "help-{}".format(relative_url))

        # set callback
        help.AutoBrowse(False)
        help.Bind(hl.EVT_HYPERLINK_LEFT, self._OnURL)

        return help

    def _InitHelp(self):
        """Initialise a container for documentation links related to a node"""

        # try to identify the default browser
        try:
            import winreg
            rkey = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "HTTP\\shell\\open\\command")
            self._BrowserPath = winreg.QueryValue(rkey, "")
            rkey.Close()

        except OSError:
            pass

        # setup UI
        info_panel = self.GetFrame().GetInfoPanel()
        help_panel = self._HelpPanel = G_WindowInfo.MakePane(info_panel)
        info_panel.InsertPage(0, help_panel.GetWindow(), "Help")

        self._AddHelpLink("NLV", "index.html")
        self._ContextHelp = self._AddHelpLink("Title", "Placeholder", "placeholder.html")


    def SetNodeHelp(self, title, relative_url, section):
        """Set the node 'context sensitive' help link"""
        url = self._GetURL(relative_url, section)
        help = self._ContextHelp
        help.SetURL(url)
        help.SetLabel(title)

        # there's a bug in the hyperlink control that doesn't update the tooltip
        # when the URL is changed; fix that here
        help.SetToolTip(wx.ToolTip(url))


    #-------------------------------------------------------
    def OpenSession(self, program_args):
        from .Session import GetSessionManager
        GetSessionManager().SessionSetup(self.GetRootNode(), program_args)


    #-------------------------------------------------------
    def MakeNode(self, factory_id, item, name, **kwargs):
        """Create a new G_Node for use in the Project tree control"""

        # run the factory
        node = self.GetFactory(factory_id).MakeNode(MakeWeakRef(self), MakeWeakRef(item), name, **kwargs)

        # link the node to the item
        item.SetData(node)
        return node


    #-------------------------------------------------------
    def GetAuiManager(self):
        return self.GetFrame().GetAuiManager()

    def GetChannel(self, name, guid):
        if guid not in self._Channels:
            self._Channels[guid] = Channel(name, guid)
        return self._Channels[guid]

    def GetDefaults(self):
        return self._Defaults

    def GetFactory(self, factory_id):
        return self._NodeFactories[factory_id]

    def GetFrame(self):
        return self._Frame

    def GetTree(self):
        return self._Tree

    def GetAuiNotebook(self):
        return self.GetFrame().GetAuiNotebook()

    def GetRootNode(self):
        return self._RootNode


    #-------------------------------------------------------
    def AttachNode(self, factory_id, parent_node, name, **kwargs):
        """Create and attach a new node to the tree control"""

        # add a tree item to the control, to host the node
        tree = self.GetTree()
        parent_item = parent_node.GetTrItem()
        item = tree.AppendItem(parent_item, name)
        item.SetImage(self.GetFactory(factory_id).GetArtID(), ctt.TreeItemIcon_Normal)

        # create the node
        node = self.MakeNode(factory_id, item, name, **kwargs)

        # ensure parent item is expanded, to make the new child visible
        if not parent_node is self.GetRootNode():
            tree.Expand(parent_item)
        return node


    #-------------------------------------------------------
    def DeleteNode(self, item):
        """Delete the item from the control"""
        self.GetTree().Delete(item)


    #-------------------------------------------------------
    def Close(self):
        """Release all external resources in the project"""
        from .Session import GetSessionManager
        GetSessionManager().OnCmdSessionSave()

        from .MatchNode import GetHistoryManager
        GetHistoryManager().Close()

        root = self.GetRootNode()
        root.Close()
        Nlog.Setup(None, None)

        # kill any notification channels
        for channel in self._Channels.values():
            channel.ShutDown()


    #-------------------------------------------------------
    def LoadPerspective(self, layout):
        sashpos = int(layout)
        if sashpos < G_Const.ProjectMinSplit:
            sashpos = G_Const.ProjectMinSplit
        self.SetSashPosition(sashpos)

    def SavePerspective(self):
        return str(self.GetSashPosition())

    def DefaultPerspective(self):
        self.SetSashPosition(G_Const.ProjectInitialSplit)


    #-------------------------------------------------------
    def OnBeginLabelEdit(self, event):
        allow = _Item2Node(event.GetItem()).OnBeginLabelEdit()
        if not allow:
            event.Veto()

    def OnEndLabelEdit(self, event):
        allow = _Item2Node(event.GetItem()).OnEndLabelEdit(event.GetLabel())
        if not allow:
            event.Veto()


    #-------------------------------------------------------
    def OnSelChanged(self, event):
        """Handle selection of an item in the tree"""

        window = self._Panel.GetWindow()
        sizer = self._Panel.GetSizer()

        # the Freeze is important, as it prevents flicker and unwanted drawing
        # artifacts left on the screen (which can happen when a control's label
        # is set, but before the control has been correctly positioned by the
        # layout system)
        window.Freeze()
        old_node = _Item2Node(event.GetOldItem())
        if old_node:
            sizer.Show(old_node.GetSizer(), False)

        new_node = _Item2Node(event.GetItem())
        if new_node:
            # order is important: the Show() behaves as if its "recursive" argument
            # is forced to True, so the Activate has to follow afterwards, in order
            # to have final control over visibility of sub-sizers
            sizer.Show(new_node.GetSizer(), True)
            new_node.Activate()

        sizer.Layout()
        window.Thaw()
        event.Skip()


    #-------------------------------------------------------
    def OnRightClick(self, event):
        """A tree node has been right clicked"""
        self.OnDisplayPopupMenu(self._Tree, _Item2Node(event.GetItem()))



## MODULE ##################################################

G_Project.RegisterNodeFactory(
    G_NodeFactory(G_Project.NodeID_Root, G_Project.ArtDocID_Home, G_RootNode)
)

