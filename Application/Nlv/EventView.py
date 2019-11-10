#
# Copyright (C) Niel Clausen 2017-2019. All rights reserved.
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

#
# An event analyser presents a view of a logfile based on domain
# specific knowledge. The knowledge is held in user provided Python
# text, referred to as an analyser script. Strictly, the analyser
# script contains an event recogniser *and* a series of metric
# quantifiers. The recogniser scans the log file and generates an
# event table (SQL DB), which in turn, is displayed in the UI via
# the G_EventProjectorNode. The quantifiers scan the event table and
# assemble (i.e. deduce) domain relevent metrics (e.g. a categorisation
# of the events), also stored as SQL DB files. A quantifier can define
# any number of chart designers, which realise the assembled metric
# data, arbitrary user supplied parameters and the current selection
# into a displayable chart. Hence the metrics are projected in both
# tabular and chart form, all via the G_MetricsProjectorNode.
#

# Python imports
import base64
import json
import logging
from pathlib import Path
import pywintypes
import time
from uuid import uuid4
import win32com.client as com
import zlib

# wxWidgets imports
import wx

# Application imports 
from .Document import D_Document
from .EventDisplay import G_MetricsViewCtrl
from .EventDisplay import G_TableViewCtrl
from .EventProjector import G_Analyser
from .EventProjector import G_ScriptGuard
from .Logfile import G_DisplayNode
from .Logfile import G_DisplayChildNode
from .Logfile import G_TabDisplayControl
from .MatchNode import G_MatchItem
from .MatchNode import G_MatchNode
from .Project import G_Const
from .Project import G_Global
from .Project import G_TabContainedNode
from .Project import G_TabContainerNode
from .Project import G_ListContainedNode
from .Project import G_ListContainerNode
from .Project import G_HideableTreeNode
from .Project import G_HideableTreeChildNode
from .Project import G_WindowInfo
from .Project import G_NodeFactory
from .Project import G_Project
from .PythonEditor import G_AnalyserScriptCtrl
from .StyleNode import G_ColourNode
from .StyleNode import G_EnabledColourNode
from .Theme import G_ThemeNode
from .Theme import G_ThemeOverridesNode
from .Theme import G_ThemeGalleryNode
from .Theme import GetThemeSupportFile

# Content provider interface
import Nlog



## G_LogAnalysisChildNode ##################################

class G_LogAnalysisChildNode(G_DisplayChildNode):
    """Mixin class to extend child nodes of G_LogAnalysisNode node with common behaviour"""

    #-------------------------------------------------------
    def GetLogAnalysisNode(self):
        # recursive lookup; find our view node
        return self.GetParentNode(G_Project.NodeID_LogAnalysis)


    #-------------------------------------------------------
    def GetErrorReporter(self):
        return self.GetLogAnalysisNode().GetErrorReporter()



## G_AnalyserScriptNode ####################################

class G_AnalyserScriptNode(G_LogAnalysisChildNode, G_ThemeNode, G_TabContainedNode):

    #-------------------------------------------------------
    def BuildPage(parent):
        # class static function
        me = __class__
        me._Sizer = parent.GetSizer()

        window = parent.GetWindow()

        me.BuildSubtitle(parent, "Description")
        me._Description = wx.TextCtrl(window, size = (-1, 75), style = wx.TE_BESTWRAP | wx.TE_MULTILINE)
        me._Sizer.Add(me._Description, flag = wx.BOTTOM | wx.LEFT | wx.RIGHT | wx.EXPAND, border = G_Const.Sizer_StdBorder, userData = "AnalyserScriptNode-description")

        sizer = me._SizerSave = wx.BoxSizer(wx.VERTICAL)
        pane = G_WindowInfo(sizer, window)

        me.BuildSubtitle(pane, "Currently using the internal editor")

        me._BtnSaveAs = wx.Button(window, label = "Save ...", size = G_Const.ButtonSize)
        me.BuildLabelledRow(pane, "Switch to an external editor", me._BtnSaveAs)

        me._Sizer.Add(sizer, flag = wx.EXPAND)

        sizer = me._SizerLoad = wx.BoxSizer(wx.VERTICAL)
        pane = G_WindowInfo(sizer, window)

        me.BuildSubtitle(pane, "Currently using an external editor")

        me._BtnLoad = wx.Button(window, label = "Load", size = G_Const.ButtonSize)
        me.BuildLabelledRow(pane, "Switch to the built-in editor", me._BtnLoad)

        me._Sizer.Add(sizer, flag = wx.EXPAND)


    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem, name, **kwargs):
        G_TabContainedNode.__init__(self, factory, wproject, witem)
        G_ThemeNode.__init__(self, G_ThemeNode.DomainEvent)

    def PostInitNode(self):
        self._Field = D_Document(self.GetDocument(), self)

        # initialise here for backwards compatibility
        self._Field.Add("", "ActiveScript", replace_existing = False)
        self._Field.Add(True, "UseInternalEditor", replace_existing = False)
        self._Field.Add("", "ExternalPath", replace_existing = False)

    def PostInitLoad(self):
        # themed document fields not available until theme node setup
        self.UpdateScriptCtrl()


    #-------------------------------------------------------
    @staticmethod
    def DataToText(data):
        # decompress document data into Python text
        if len(data) == 0:
            return ""
        else:
            data = G_Global.UnmarkString(data)
            b64_bytes = base64.standard_b64decode(data)
            decompressed_bytes = zlib.decompress(b64_bytes)
            return decompressed_bytes.decode()

    @staticmethod
    def TextToData(text):
        # compress Python text ready to store in the document
        if len(text) == 0:
            return ""
        else:
            compressed_bytes = zlib.compress(bytes(text, "utf-8"))
            b64_bytes = base64.standard_b64encode(compressed_bytes)
            return G_Global.MarkString(b64_bytes.decode())


    #-------------------------------------------------------
    @staticmethod
    def ReadScriptFile(path):
        if path is None or not path.exists():
            return ""
        else:
            with open(str(path), "r") as file:
                return file.read().replace("\r", "")

    @staticmethod
    def SaveScriptFile(filename, text):
        with open(filename, "w", newline ="") as file:
            file.write(text)


    #-------------------------------------------------------
    def Activate(self):
        self.ActivateCommon()

        self.Rebind(self._Description, wx.EVT_TEXT, self.OnDescription)
        self.Rebind(self._BtnLoad, wx.EVT_BUTTON, self.OnCmdLoad)
        self.Rebind(self._BtnSaveAs, wx.EVT_BUTTON, self.OnCmdSaveAs)

        self._Description.SetValue(self._Field.Description.Value)

        # setup visibility of the "switch" buttons
        self.UpdateSwitchCtrls()
        self.SetNodeHelp("Event Recogniser", "events.html", "eventrecogniser")


    #-------------------------------------------------------
    def GetScriptCtrl(self):
        return self.GetLogAnalysisNode().GetScriptCtrl()


    #-------------------------------------------------------
    def GetActiveScriptText(self, update):
        if update:
            self.SetActiveScriptText(self.GetEditedScriptText())
        return self.DataToText(self._Field.ActiveScript.Value)

    def SetActiveScriptText(self, text):
        self._Field.ActiveScript.Value = self.TextToData(text.replace("\r", ""))

    def GetEditedScriptText(self):
        # once off initialisation: if the theme has stored the Python
        # source text in a separate file, then find and load that
        if self._Field.ReferenceScript.Value != "":
            path = GetThemeSupportFile(self._Field.ReferenceScript.Value)
            self._Field.ReferenceScript.Value = ""
            self.SetEditedScriptText(self.ReadScriptFile(path), False)

        if not self._Field.UseInternalEditor.Value:
            self.SetEditedScriptText(self.ReadScriptFile(Path(self._Field.ExternalPath.Value)))

        return self.DataToText(self._Field.EditedScript.Value)

    def SetEditedScriptText(self, text, invalidate_event_view = True):
        self._Field.EditedScript.Value = self.TextToData(text.replace("\r", ""))
        if invalidate_event_view:
            self.GetLogAnalysisNode().OnScriptChange()


    #-------------------------------------------------------
    def OnDescription(self, event):
        """The description text has altered; keep a copy of it"""
        text = self._Description.GetValue()
        if text != self._Field.Description.Value:
            self._Field.Description.Value = text


    #-------------------------------------------------------
    def OnScriptChange(self, evt):
        # the (Python) script has been edited
        self.SetEditedScriptText(self.GetScriptCtrl().GetPythonText())


    #-------------------------------------------------------
    def UpdateEditorMode(self):
        self.GetScriptCtrl().SetMode(self._Field.UseInternalEditor.Value, self._Field.ExternalPath.Value)


    def OnCmdLoad(self, evt):
        self._Field.UseInternalEditor.Value = True

        self.SetEditedScriptText(self.ReadScriptFile(Path(self._Field.ExternalPath.Value)))
        self._Field.ExternalPath.Value = ""

        self.UpdateScriptCtrl()
        self.UpdateSwitchCtrls()


    def OnCmdSaveAs(self, evt):
        dlg = wx.FileDialog(
            self.GetRootNode().GetFrame(),
            message = "Save analyser script",
            defaultDir = str(Path.cwd()),
            wildcard = "Python files (*.py)|*.py",
            style = wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
        )

        path = None
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()

        dlg.Destroy()

        if path is None:
            return

        self.SaveScriptFile(path, self.GetEditedScriptText())
        self._Field.UseInternalEditor.Value = False
        self._Field.ExternalPath.Value = path
        self.UpdateSwitchCtrls()


    #-------------------------------------------------------
    def UpdateSwitchCtrls(self):
        sizer = self._Sizer
        internal = self._Field.UseInternalEditor.Value

        sizer.Show(self._SizerSave, internal)
        sizer.Show(self._SizerLoad, not internal)

        self.UpdateEditorMode()
        sizer.Layout()


    #-------------------------------------------------------
    def UpdateScriptCtrl(self):
        # refresh script text from document
        self.UpdateEditorMode()
        if self._Field.UseInternalEditor.Value:
            script_ctrl = self.GetScriptCtrl()
            script_ctrl.Unbind(wx.stc.EVT_STC_CHANGE)
            script_ctrl.SetPythonText(self.GetEditedScriptText())
            script_ctrl.Bind(wx.stc.EVT_STC_CHANGE, self.OnScriptChange)


    #-------------------------------------------------------
    def OnThemeChange(self, theme_cls, theme_id):
        if self.IsThemeApplicable(theme_cls, theme_id, G_Const.EventThemeCls):
            self._Field.UseInternalEditor.Value = True
            self.UpdateScriptCtrl()
            self.GetLogAnalysisNode().UpdateValidity(False)



## G_EventAnalyseNode ######################################

class G_EventAnalyseNode(G_LogAnalysisChildNode, G_ThemeNode, G_TabContainedNode):

    #-------------------------------------------------------
    def BuildPage(parent):
        # class static function
        me = __class__
        me._Sizer = parent.GetSizer()

        window = parent.GetWindow()

        me._BtnAnalyse = wx.Button(window, label = "Analyse", size = G_Const.ButtonSize)
        me.BuildLabelledRow(parent, "Analyse logfile and extract events", me._BtnAnalyse)

        me._BtnExcel = wx.Button(window, label = "Open", size = G_Const.ButtonSize)
        me.BuildLabelledRow(parent, "Open event data in Excel", me._BtnExcel)
        me._BtnExcel.Enable(False)

        # makepy.py -i
        # Microsoft Excel 15.0 Object Library
        # {00020813-0000-0000-C000-000000000046}, lcid=0, major=1, minor=8
        try:
            module = com.gencache.EnsureModule('{00020813-0000-0000-C000-000000000046}', 0, 1, 8)
            me._BtnExcel.Enable(module is not None)
        except pywintypes.com_error as ex:
            logging.info("Excel not found; Excel integration will be disabled")


    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem, name, **kwargs):
        G_TabContainedNode.__init__(self, factory, wproject, witem)
        G_ThemeNode.__init__(self, G_ThemeNode.DomainEvent)

    def PostInitNode(self):
        self._Field = D_Document(self.GetDocument(), self)


    #-------------------------------------------------------
    def Activate(self):
        self.ActivateCommon()
        self.Rebind(self._BtnAnalyse, wx.EVT_BUTTON, self.OnCmdAnalyse)
        self.Rebind(self._BtnExcel, wx.EVT_BUTTON, self.OnCmdExcel)
        self.SetNodeHelp("Analyser", "events.html", "eventanalyser")


    #-------------------------------------------------------
    @G_Global.ProgressMeter
    def OnCmdAnalyse(self, event):
        self.GetLogAnalysisNode().UpdateAnalysis()


    #-------------------------------------------------------
    def OnCmdExcel(self, event):
        filename = self.GetLogAnalysisNode().MakeTemporaryFilename(".csv")
        excel = com.Dispatch("Excel.Application")
        if excel is not None:
            excel.Workbooks.Open( Filename = filename)
            excel.Visible = 1



## G_LogAnalysisLocalThemeGalleryNode ######################

class G_LogAnalysisLocalThemeGalleryNode(G_LogAnalysisChildNode, G_ThemeGalleryNode, G_ListContainedNode):
    """LogAnalysis theme gallery"""

    #-------------------------------------------------------
    def BuildPage(parent):
        # class static function
        me = __class__
        me._Sizer = parent.GetSizer()

        G_ThemeGalleryNode.BuildGallery(me, parent, "events")


    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem, name, **kwargs):
        G_ListContainedNode.__init__(self, factory, wproject, witem)
        G_ThemeGalleryNode.__init__(self, G_Const.EventThemeCls)

        self._InitThemeId = None
        if "theme_id" in kwargs:
            self._InitThemeId = kwargs["theme_id"]

    def PostInitNode(self):
        # make document fields accessible
        self._Field = D_Document(self.GetDocument(), self)

        # ensure the current theme is setup
        self.PostInitThemeGallery(self._InitThemeId)


    #-------------------------------------------------------
    def Activate(self):
        self.SetNodeHelp("Event Pattern Themes", "events.html", "eventpatterns")
        self.ActivateThemeGallery()



## G_LogAnalysisThemeContainerNode #########################

class G_LogAnalysisThemeContainerNode(G_LogAnalysisChildNode, G_ListContainerNode):
    """Container node for hosting LogAnalysis theme controls"""

    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem, name, **kwargs):
        super().__init__(factory, wproject, witem)


    #-------------------------------------------------------
    def Activate(self):
        G_ListContainerNode.ActivateContainer(self)



## G_LogAnalysisLocalThemeOverridesNode ####################

class G_LogAnalysisLocalThemeOverridesNode(G_LogAnalysisChildNode, G_ThemeOverridesNode, G_ListContainedNode):
    """LogAnalysis local theme overrides saving/restoring"""

    #-------------------------------------------------------
    def BuildPage(parent):
        # class static function
        me = __class__
        me._Sizer = parent.GetSizer()

        G_ThemeOverridesNode.BuildControl(me, parent)


    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem, name, **kwargs):
        G_ListContainedNode.__init__(self, factory, wproject, witem)
        G_ThemeOverridesNode.__init__(self, G_Const.EventThemeCls, G_ThemeNode.DomainEvent)


    #-------------------------------------------------------
    def Activate(self):
        self.SetNodeHelp("Events Pattern Themes", "events.html", "eventpatterns")
        self.ActivateControl()



## G_LogAnalysisNode #######################################

class G_LogAnalysisNode(G_DisplayNode, G_HideableTreeNode, G_TabContainerNode):
    """Master node for all logfile analysis and results viewing"""

    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem, name, **kwargs):
        # track our position in the project tree
        G_DisplayNode.__init__(self)
        G_TabContainerNode.__init__(self, factory, wproject, witem)

        self._AnalysisRun = False

        self._InitAnalysis = False
        if "do_analysis" in kwargs:
            self._InitAnalysis = kwargs["do_analysis"]


    def PostInitNode(self):
        # make document fields accessible
        self._Field = D_Document(self.GetDocument(), self)

        # ensure non-template fields exist and are initialised
        self._Field.Add(str(uuid4()), "Guid", replace_existing = False)
        self._Field.Add(True, "AnalysisIsValid", replace_existing = False)

        # setup UI
        display_notebook = self._DisplayNotebook = G_TabDisplayControl(self.GetAuiNotebook())
        script_ctrl = self._ScriptCtrl = G_AnalyserScriptCtrl(display_notebook)
        display_notebook.AddPage(script_ctrl, "Script")

        self.SetDisplayCtrl(display_notebook, script_ctrl)
        self.InterceptSetFocus(script_ctrl.GetEditor())


    @G_Global.TimeFunction
    def PostInitChildren(self):
        # apply the themed default node name to the tree
        node_name = self._Field.DefaultNodeName.Value
        self.SetTreeLabel(node_name)
        G_Global.GetCurrentTimer().AddArgument(node_name)

        # and add the viewer to the main notebook, without altering focus
        def Work():
            self.GetAuiNotebook().AddPage(self._DisplayNotebook, node_name, True)
            if self._InitAnalysis:

                # make sure hideable is setup before child is made
                self.PostInitHideableTreeNode()
                self.AnalyseForAll()

                if self._AnalysisResults is not None:
                    for projector in self._AnalysisResults.Projectors.values():
                        self.BuildNodeFromDefaults(G_Project.NodeID_EventProjector, projector.ProjectionName, do_analysis = self._InitAnalysis)

                self.PostAnalyse()

            self.UpdateEventContent()

        self.WithFocusLock(Work)


    def PostInitLayout(self):
        self.PostInitHideableTreeNode()


    #-------------------------------------------------------
    def GetDisplayNoteBook(self):
        return self._DisplayNotebook


    #-------------------------------------------------------
    def DoClose(self, delete):
        if delete:
            self.RemoveTemporaryFiles()
        super().DoClose(delete)


    #-------------------------------------------------------
    def MakeTemporaryFilename(self, ext):
        cachedir = self.GetLogNode().MakeSessionDir()
        return str((cachedir / self._Field.Guid.Value).with_suffix(ext))

    def RemoveTemporaryFiles(self):
        guid = self._Field.Guid.Value
        for file in self.GetLogNode().MakeSessionDir().iterdir():
            if str(file).find(guid) >= 0:
                try:
                    file.unlink()
                except Exception as ex:
                    logging.info("Unable to remove temporary: file=[{}] info=[{}]".format(str(file), str(ex)))


    #-------------------------------------------------------
    def Activate(self):
        self.ActivateContainer()


    #-------------------------------------------------------
    def CreatePopupMenu(self, handlers):
        menu = None

        if self.IsParentNodeDisplayed():
            menu = wx.Menu("Event")
            self.AppendPopupShowHide(menu, handlers)
            self.AppendPopupDeleteNode(menu, handlers, True)

        return menu


    #-------------------------------------------------------
    def GetActiveScriptText(self, update):
        node = self.FindChildNode(G_Project.NodeID_AnalyserScript, recursive = True)
        return node.GetActiveScriptText(update)

    def GetScriptCtrl(self):
        return self._ScriptCtrl


    #-------------------------------------------------------
    def SetErrorText(self, new_text, is_error_msg = False):
        self._ScriptCtrl.SetErrorText(new_text, is_error_msg)

    def OnAnalyserError(self, new_text):
        """An error occurred during analysis; display it in the UI"""
        self.SetErrorText(new_text, True)
        self.ActivateSubTab(self._ScriptCtrl)


    #-------------------------------------------------------
    def OnBeginLabelEdit(self):
        """Node names for the analysis are taken from the theme, and are not user editable"""
        return False


    #-------------------------------------------------------
    @G_Global.TimeFunction
    def CompileAnalyser(self, src):
        self.SetErrorText("Compiling ...\n")

        # with a backing file, the debugger can step through the script code
        try:
            backing_file = self.MakeTemporaryFilename(".py")
            open(backing_file, 'w').write(src)

        except OSError as ex:
            error_reporter("Unable to create backing file\n{}".format(str(ex)))

        try:
            code = compile(src, backing_file, "exec")
            self.SetErrorText("Compiled OK\n")
            return code

        except SyntaxError as ex:
            self.OnAnalyserError("Syntax error compiling analyser script\nline:{}\noffset:{}\n{}".format(ex.lineno, ex.offset, ex.text))

        except ValueError as ex:
            self.OnAnalyserError("Value error compiling analyser script")

        return None


    #-------------------------------------------------------
    @G_Global.TimeFunction
    def RunAnalyser(self, code, log_schema, meta_only):
        self._AnalysisResults = None
        self._AnalysisRun = True

        self.SetErrorText("Analysing ...\n")
        with G_ScriptGuard("Analysis", self.OnAnalyserError):
            event_id = self.GetSessionNode().GetEventId()
            analyser = G_Analyser(self.MakeTemporaryFilename(".db"), event_id)
            globals = analyser.SetEntryPoints(meta_only, log_schema, self.GetLogfile(), self.GetLogNode())

            exec(code, globals)

            self.SetErrorText("Analysed OK\n")
            self._Field.AnalysisIsValid.Value = True

            self._AnalysisResults = analyser.Close()
            self.GetSessionNode().UpdateEventId(self._AnalysisResults.EventId)


    #-------------------------------------------------------
    @G_Global.TimeFunction
    def Analyse(self, source, meta_only = False):

        code = self.CompileAnalyser(source)
        if code is None:
            return None

        log_schema = self.GetLogNode().GetLogSchema()
        self.RunAnalyser(code, log_schema, meta_only)

    def AnalyseForMeta(self):
        self.Analyse(self.GetActiveScriptText(False), True)

    def AnalyseForAll(self):
        self.ReleaseFiles()
        self.Analyse(self.GetActiveScriptText(True))


    #-------------------------------------------------------
    def GetAnalysisResults(self):
        if not self._AnalysisRun:
            self.AnalyseForMeta()

        is_valid = self._Field.AnalysisIsValid.Value
        return self._AnalysisResults, is_valid


    def GetErrorReporter(self):
        return self.OnAnalyserError


    #-------------------------------------------------------
    def _ForallProjectors(self, func, event, metrics):
        if event:
            self.VisitSubNodes(func, factory_id = G_Project.NodeID_EventProjector, recursive = True)

        if metrics:
            self.VisitSubNodes(func, factory_id = G_Project.NodeID_MetricsProjector, recursive = True)


    def PostAnalyse(self):
        def Work(node):
            node.PostAnalyse(self._AnalysisResults)

        self._ForallProjectors(Work, event = True, metrics = False)


    def ReleaseFiles(self):
        self._AnalysisResults = None
        self._AnalysisRun = False
        
        def Work(node):
            node.ReleaseFiles()

        self._ForallProjectors(Work, event = True, metrics = True)


    @G_Global.TimeFunction
    def UpdateEventContent(self):
        analysis, is_valid = self.GetAnalysisResults()
        if analysis is None:
            return

        def Work(node):
            node.UpdateEventContent()

        self._ForallProjectors(Work, event = True, metrics = False)


    def UpdateValidity(self, valid):
        def Work(node):
            node.UpdateValidity(valid)
        self._ForallProjectors(Work, event = True, metrics = True)


    #-------------------------------------------------------
    @G_Global.ProgressMeter
    @G_Global.TimeFunction
    def UpdateAnalysis(self):
        """Analysis requested by user"""
        def Work():
            self.AnalyseForAll()
            self.UpdateEventContent()
            self.PostAnalyse()

        self.WithFrameLocked(Work)


    #-------------------------------------------------------
    def OnScriptChange(self):
        # the (Python) analyser script has been edited
        self._Field.AnalysisIsValid.Value = False
        self.UpdateValidity(False)



## G_ProjectorChildNode ####################################

class G_ProjectorChildNode(G_LogAnalysisChildNode):
    """
    Mixin class to extend projector child nodes (event or metrics)
    with common behaviour
    """

    #-------------------------------------------------------
    def GetProjectorNode(self):
        # recursive lookup; find our projector node (event or metrics)
        return self.GetDisplayNode()

    def GetTableViewCtrl(self):
        # fetch the table viewer control; this hosts the data view model
        return self.GetProjectorNode().GetTableViewCtrl()



## G_TableSearchNode #######################################

class G_TableSearchNode(G_ProjectorChildNode, G_ThemeNode, G_MatchNode, G_ColourNode, G_ListContainedNode):

    #-------------------------------------------------------
    def BuildPage(parent):
        # class static function
        me = __class__
        me._Sizer = parent.GetSizer()

        # add child controls
        G_MatchNode.BuildMatch(me, parent, "Search", filter = True, search_buttons = True)
        G_ColourNode.BuildColour(me, parent)


    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem, name, **kwargs):
        G_ListContainedNode.__init__(self, factory, wproject, witem)
        G_MatchNode.__init__(self, G_Const.EventThemeCls, "Search")
        G_ThemeNode.__init__(self, G_ThemeNode.DomainEvent)


    #-------------------------------------------------------
    def PostInitNode(self):
        self._Field = D_Document(self.GetDocument(), self)

    def PostInitLoad(self):
        # themes are setup now
        self.PostInitColour()
        self.PostInitMatch()


    #-------------------------------------------------------
    def Activate(self):
        focus_window = self.ActivateMatch()
        self.ActivateColour()
        self.ActivateCommon(focus_window)


    #-------------------------------------------------------
    def OnMatch(self, match_item, refocus = None):
        if self.GetTableViewCtrl().UpdateHiliterMatch(self.GetIndex(), match_item):
            self.SendFocusToDisplayCtrl(refocus)
            return True
        else:
            return False


    #-------------------------------------------------------
    def OnColour(self, refocus):
        self.GetTableViewCtrl().UpdateHiliterColour(self.GetIndex(), self.GetColour())
        self.SendFocusToDisplayCtrl(refocus)


    #-------------------------------------------------------
    def OnThemeChange(self, theme_cls, theme_id):
        if theme_cls == G_Const.GlobalThemeCls:
            self.SetColourTheme()
            self.SetStyleTheme()
        else:
            G_MatchNode.OnThemeChange(self, theme_cls, theme_id)


    #-------------------------------------------------------
    def OnSearch(self, forward = None, modifiers = None):
        """A forward or reverse search has been requested"""
        self.GetTableViewCtrl().GotoNextItem("hilite", forward, modifiers, self.GetIndex())
        if modifiers is None:
            self.SendFocusToDisplayCtrl()


    #-------------------------------------------------------
    def OnDisplayKey(self, key_code, modifiers, view_node):
        """Intercept key presses sent to the DataView control"""
        if key_code < ord("1") or key_code > ord("3"):
            return False

        index = key_code - ord("1")
        if index != self.GetIndex():
            return False

        self.OnSearch(modifiers = modifiers)
        return True



## G_TableSearchContainerNode ##############################

class G_TableSearchContainerNode(G_ProjectorChildNode, G_ListContainerNode):

    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem, name, **kwargs):
        super().__init__(factory, wproject, witem)

    def PostInitChildren(self):
        # have to know how many children there are in order to initialise the view ...
        self.GetTableViewCtrl().SetNumHiliter(self.GetHrItem().GetChildrenCount())


    #-------------------------------------------------------
    def Activate(self):
        self.ActivateCommon()
        G_ListContainerNode.ActivateContainer(self)
        self.SetNodeHelp("Event Searching & Hiliting", "events.html", "eventhiliters")



## G_TableFilterNode #######################################

class G_TableFilterNode(G_ProjectorChildNode, G_ThemeNode, G_MatchNode, G_TabContainedNode):
    """A filter control"""

    #-------------------------------------------------------
    def BuildPage(parent):
        # class static function
        me = __class__
        me._Sizer = parent.GetSizer()

        # add match controls
        G_MatchNode.BuildMatch(me, parent, "Filter", height = 75, filter = True)

        # view metrics information
        me.LblItemCount = wx.StaticText(parent.GetWindow(), label = "#")
        me.BuildLabelledRow(parent, "Item count", me.LblItemCount)


    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem, name, **kwargs):
        G_MatchNode.__init__(self, G_Const.EventThemeCls, "Filter")
        G_TabContainedNode.__init__(self, factory, wproject, witem)
        G_ThemeNode.__init__(self, G_ThemeNode.DomainEvent)


    #-------------------------------------------------------
    def PostInitNode(self):
        self._Field = D_Document(self.GetDocument(), self)

    def PostInitLoad(self):
        # themes are setup now
        self.PostInitMatch()


    #-------------------------------------------------------
    def Activate(self):
        focus_window = self.ActivateMatch()
        self.ActivateCommon(focus_window)
        self.SetMetrics()
        self.SetNodeHelp("Event Filtering", "events.html", "eventfilters")


    #-------------------------------------------------------
    def SetMetrics(self):
        num_items = self.GetTableViewCtrl().GetNumItems()
        self.LblItemCount.SetLabelText("{0:,}".format(num_items))


    #-------------------------------------------------------
    def OnMatch(self, match, refocus = None):
        if self.GetProjectorNode().OnFilterMatch(match):
            self.SetMetrics()
            self.SendFocusToDisplayCtrl(refocus)
            return True
        else:
            return False


    #-------------------------------------------------------
    def OnThemeChange(self, theme_cls, theme_id):
        """The match has altered; refresh match control"""
        G_MatchNode.OnThemeChange(self, theme_cls, theme_id)



## G_TrackInfo ############################################

class G_TrackInfo(D_Document.D_Value):
    """Store for an event's tracking behaviour"""

    _Initialised = False
    _MarkerNames = ["None"]
    _GlobalSourceNames = ["None"]

    def SetupNames(marker_names):
        """(Static) Setup the global list of tracker names"""

        me = __class__
        if me._Initialised:
            return
        me._Initialised = True

        me._MarkerNames.extend([n for n in marker_names if n.find("(B)") < 0])

        # i.e. None and global tracker names
        gnames = G_Const.GlobalTrackerNames
        for i in range(int(len(gnames)/2)):
            me._GlobalSourceNames.append("{} - {}".format(gnames[2*i], gnames[2*i + 1]))


    #-------------------------------------------------------
    def __init__(self, src = None):
        if src is None:
            self.idxUpdateMarker = 0
            self.idxUpdateGlobal = 0
        else:
            self.idxUpdateMarker = src.idxUpdateMarker
            self.idxUpdateGlobal = src.idxUpdateGlobal


    #-------------------------------------------------------
    def UpdateMarkerIdx(self):
        """Return index of marker to update, or < 0 if none"""
        return self.idxUpdateMarker - 1

    def UpdateGlobalIdx(self):
        """Return index of global tracker pair to update, or < 0 if none"""
        return 2 * (self.idxUpdateGlobal - 1)



## G_EventTrackingNode #####################################

class G_EventTrackingNode(G_ProjectorChildNode, G_ThemeNode, G_TabContainedNode):
    """Define the event views's tracking behaviour"""

    #-------------------------------------------------------
    def BuildPage(parent):
        # class static function
        me = __class__
        me._Sizer = parent.GetSizer()

        window = parent.GetWindow()
        me._CheckBoxes = []

        # combo: view should update one of the parent logfile's markers
        me._UpdateMarkerCtl = wx.Choice(window)
        me.BuildLabelledRow(parent, "Set marker from event", me._UpdateMarkerCtl)

        # combo: view should update one of the global trackers from cursor
        me._UpdateGlobalCtl = wx.Choice(window)
        me.BuildLabelledRow(parent, "Set ranges from\nevent", me._UpdateGlobalCtl)


    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem, name, **kwargs):
        G_TabContainedNode.__init__(self, factory, wproject, witem)
        G_ThemeNode.__init__(self, G_ThemeNode.DomainEvent)

    def PostInitNode(self):
        self._Field = D_Document(self.GetDocument(), self)
        self.ResetTrackInfo()

    def PostInitLoad(self):
        # setup marker names now they're known
        marker_names = self.GetLogNodeChildNode(G_Project.NodeID_MarkerContainer).GetMarkerNames()
        G_TrackInfo.SetupNames(marker_names)


    #-------------------------------------------------------
    def Activate(self):
        self.ActivateCommon()

        # once off initialisation of combos, now that the tracker names are known
        if self._UpdateGlobalCtl.GetCount() == 0:
            self._UpdateMarkerCtl.Set(G_TrackInfo._MarkerNames)
            self._UpdateGlobalCtl.Set(G_TrackInfo._GlobalSourceNames)

        track_info = self.GetTrackInfo()

        self.Rebind(self._UpdateMarkerCtl, wx.EVT_CHOICE, self.OnUpdateMarker)
        self._UpdateMarkerCtl.SetSelection(track_info.idxUpdateMarker)

        self.Rebind(self._UpdateGlobalCtl, wx.EVT_CHOICE, self.OnUpdateGlobal)
        self._UpdateGlobalCtl.SetSelection(track_info.idxUpdateGlobal)

        self.SetNodeHelp("Event Tracking", "events.html", "eventtracking")


    #-------------------------------------------------------
    def ResetTrackInfo(self):
        self._TrackInfo = None

    def GetTrackInfo(self):
        if self._TrackInfo is None:
            self._TrackInfo = G_TrackInfo(self._Field.TrackInfo.Value)
        return self._TrackInfo


    #-------------------------------------------------------
    def OnThemeChange(self, theme_cls, theme_id):
        if self.IsThemeApplicable(theme_cls, theme_id, G_Const.EventThemeCls):
            self.ResetTrackInfo()

    def OnUpdateMarker(self, event):
        self._Field.TrackInfo.idxUpdateMarker.Value = self._UpdateMarkerCtl.GetSelection()
        self.ResetTrackInfo()
        self.SendFocusToDisplayCtrl()

    def OnUpdateGlobal(self, event):
        self._Field.TrackInfo.idxUpdateGlobal.Value = self._UpdateGlobalCtl.GetSelection()
        self.ResetTrackInfo()
        self.SendFocusToDisplayCtrl()



## G_EventFieldNode #############################################

class G_EventFieldNode(G_ProjectorChildNode, G_ThemeNode, G_EnabledColourNode, G_TabContainedNode):
    """A field visibility control"""

    #-------------------------------------------------------
    def BuildPage(parent):
        # class static function
        me = __class__
        me._Sizer = parent.GetSizer()

        # an array of enabled colour combos
        G_EnabledColourNode.BuildEnabledColour(me, parent)


    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem, name, **kwargs):
        G_TabContainedNode.__init__(self, factory, wproject, witem)
        G_ThemeNode.__init__(self, G_ThemeNode.DomainEvent)


    #-------------------------------------------------------
    def PostInitNode(self):
        self._Field = D_Document(self.GetDocument(), self)

    def PostInitLoad(self):
        self.PostInitColour()


    #-------------------------------------------------------
    def Activate(self):
        self.ActivateCommon()
        self.ActivateEnabledColour(self.GetFieldNames())
        self.SetNodeHelp("Event Field Visibility", "events.html", "eventfields")


    #-------------------------------------------------------
    def GetFieldNames(self):
        event_schema = self.GetTableViewCtrl().GetTableSchema()
        if event_schema is None:
            return []
        else:
            return event_schema.GetFieldNames()


    #-------------------------------------------------------
    def OnColour(self, field_id):
        """A colour has altered; refresh the display"""
        self.GetTableViewCtrl().UpdateFieldColour(field_id, self.GetColour(field_id))

    def OnEnable(self):
        """An enable checkbox has changed state; update view"""
        field_mask = self.GetEnabledAsMask()
        self.GetTableViewCtrl().SetFieldMask(field_mask)


    #-------------------------------------------------------
    def OnThemeChange(self, theme_cls, theme_id):
        if self.IsThemeApplicable(theme_cls, theme_id, G_Const.EventThemeCls):
            self.SetEnabledColourTheme(self.GetFieldNames())



## G_EventProjectorOptionsNode #############################

class G_EventProjectorOptionsNode(G_ProjectorChildNode, G_ThemeNode, G_TabContainedNode):

    #-------------------------------------------------------
    def BuildPage(parent):
        # class static function
        me = __class__
        me._Sizer = parent.GetSizer()

        window = parent.GetWindow()

        me._ChkNesting = wx.CheckBox(window)
        me.BuildLabelledRow(parent, "Display nested events as indented", me._ChkNesting)


    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem, name, **kwargs):
        G_TabContainedNode.__init__(self, factory, wproject, witem)
        G_ThemeNode.__init__(self, G_ThemeNode.DomainEvent)

    def PostInitNode(self):
        self._Field = D_Document(self.GetDocument(), self)


    #-------------------------------------------------------
    def Activate(self):
        self.ActivateCommon()

        permit_nesting = self.GetProjectorNode().PermitNesting()
        display_nesting = False
        if permit_nesting:
            display_nesting = self._Field.DisplayNesting.Value

        self._ChkNesting.Unbind(wx.EVT_CHECKBOX)
        self._ChkNesting.SetValue(display_nesting)
        self._ChkNesting.Bind(wx.EVT_CHECKBOX, self.OnChkNesting)
        self._ChkNesting.Enable(permit_nesting)


    #-------------------------------------------------------
    def OnChkNesting(self, event):
        nesting = self._Field.DisplayNesting.Value = self._ChkNesting.GetValue()
        self.GetProjectorNode().UpdateNesting(nesting)


    #-------------------------------------------------------
    def OnThemeChange(self, theme_cls, theme_id):
        if self.IsThemeApplicable(theme_cls, theme_id, G_Const.EventThemeCls):
            nesting = self._Field.DisplayNesting.Value
            self.GetProjectorNode().UpdateNesting(nesting)


    #-------------------------------------------------------
    def GetNesting(self):
        return self._Field.DisplayNesting.Value



## G_LogAnalysisChildProjectorNode #########################

class G_LogAnalysisChildProjectorNode(G_DisplayNode, G_LogAnalysisChildNode, G_HideableTreeChildNode):
    """
    Mixin class to extend child *projector* nodes of an analysis node
    with common behaviour (i.e. G_EventProjectorNode and G_MetricsProjectorNode.
    """

    #-------------------------------------------------------
    def __init__(self):
        G_DisplayNode.__init__(self)


    #-------------------------------------------------------
    def PostInitLayout(self):
        self.PostInitHideableTreeNode()


    #-------------------------------------------------------
    def GetDisplayNoteBook(self):
        return self.GetLogAnalysisNode().GetDisplayNoteBook()


    #-------------------------------------------------------
    def OnBeginLabelEdit(self):
        """
        Node names for tables/charts are taken from the analyser script,
        and are not user editable
        """
        return False


    #-------------------------------------------------------
    def SetupTableViewIntercepts(self):
        table_control = self.GetTableViewCtrl()
        inner_ctrl = table_control.GetChildCtrl()
        if inner_ctrl is not None:
            self.InterceptKeys(inner_ctrl)            
            self.InterceptSetFocus(inner_ctrl)            

        # trying to include the table header control seems to
        # destabilise the focus transfers, so leaving out for now
        #for window in table_control.GetChildren():
        #    self.InterceptSetFocus(window)            



## G_EventProjectorNode ####################################

class G_EventProjectorNode(G_LogAnalysisChildProjectorNode, G_TabContainerNode):
    """Class that implements a list of events"""

    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem, name, **kwargs):
        G_LogAnalysisChildProjectorNode.__init__(self)
        G_TabContainerNode.__init__(self, factory, wproject, witem)
        self._Name = name

        self._InitAnalysis = False
        if "do_analysis" in kwargs:
            self._InitAnalysis = kwargs["do_analysis"]


    def PostInitNode(self):
        # make document fields accessible
        self._Field = D_Document(self.GetDocument(), self)

        # setup UI
        display_notebook = self.GetDisplayNoteBook()
        doc_url = self.GetLogNode().MakeDataUrl()
        table_ctrl = self._TableViewCtrl = G_TableViewCtrl(display_notebook, self.OnTableSelectionChanged, doc_url = doc_url)
        display_notebook.AddPage(table_ctrl, self._Name)
        self.SetDisplayCtrl(display_notebook, table_ctrl, owns_display_ctrl = False)
        self.SetupTableViewIntercepts()
        self.SetupDataExplorer(table_ctrl.GetModel(), table_ctrl)


    def PostInitChildren(self):
        if self._InitAnalysis:
            projector_info, valid = self.GetProjectorInfo()
            for quantifier in projector_info.Quantifiers.values():
                self.BuildNodeFromDefaults(G_Project.NodeID_MetricsProjector, quantifier.Name)


    #-------------------------------------------------------
    def Activate(self):
        self.ActivateContainer()


    #-------------------------------------------------------
    def ReleaseFiles(self):
        """Release all resources owned by the view"""
        self.GetTableViewCtrl().ResetModel()

    def DoClose(self, delete):
        self.ReleaseFiles()
        super().DoClose(delete)


    #-------------------------------------------------------
    def GetProjectorInfo(self):
        analysis_results, is_valid = self.GetLogAnalysisNode().GetAnalysisResults()
        return analysis_results.GetProjectorInfo(self._Name), is_valid

    def GetNesting(self):
        node = self.FindChildNode(G_Project.NodeID_EventProjectorOptions, recursive = True)
        return node.GetNesting()

    def GetTableViewCtrl(self):
        return self._TableViewCtrl


    #-------------------------------------------------------
    def GetTrackInfo(self):
        return self.FindChildNode(G_Project.NodeID_EventTracking).GetTrackInfo()

    def GetTimecodeBase(self):
        return self.GetLogfile().GetTimecodeBase()


    #-------------------------------------------------------
    def OnDisplayKey(self, key_code, modifiers, view_node):
        handled = False
        return handled


    #-------------------------------------------------------
    def TimecodeText(self, timecode):
        # not entirely clear this will work for all locales
        timecode.Normalise()
        date = time.strftime("%x %X", time.gmtime(timecode.GetUtcDatum()))
        return "{}.{:0>9}".format(date, timecode.GetOffsetNs())


    def OnTableSelectionChanged(self, item):
        if item is None or item.GetID() is None:
            # ignore de-selection events
            return

        # tell the data explorer
        self.GetDataExplorer().Update(self.MakeDataUrl(self.GetTableViewCtrl().GetLocation(item)))

        # identify tracking options
        info = self.GetTrackInfo()
        update_marker_idx = info.UpdateMarkerIdx()
        update_global_idx = info.UpdateGlobalIdx()
        update_marker = update_marker_idx >= 0
        update_global = update_global_idx >= 0
        update = update_marker or update_global

        if not update:
            return

        # convert range to timecodes
        (start_timecode, finish_timecode) = self.GetTableViewCtrl().GetEventRange(item)
        if start_timecode is None:
            return

        if update_marker:
            # convert range to LFV compatible dates
            start_text = self.TimecodeText(start_timecode)
            finish_text = self.TimecodeText(finish_timecode)

            # build LFV expression to match the range
            # hmm, makes assumption about field names
            filter_text = "date >= {} and date <= {}".format(start_text, finish_text);
            match = G_MatchItem("LogView Filter", filter_text)

            markers = self.GetLogNodeChildNode(G_Project.NodeID_MarkerContainer)
            marker = markers.GetChildNode(update_marker_idx)
            marker.SetMatch(match, make_active = False, update_history = False, refocus = False)

        if update_global:
            # capture new tracker data
            self.UpdateTrackers(False, update_global_idx, [start_timecode, finish_timecode])

            # flush any changes through to the GUI
            self.RefreshTrackers(False, True, None)



    #-------------------------------------------------------
    def OnFilterMatch(self, match):
        """The filter has changed"""
        ok = self.GetTableViewCtrl().UpdateFilter(match)

        # propagate new event list to all metrics
        if ok and not self._Initialising:
            self.UpdateMetricContent()

        return ok


    #-------------------------------------------------------
    def PostAnalyse(self, analysis_results):
        if analysis_results is not None:
            event_schema = analysis_results.GetProjectorInfo(self._Name).ProjectionSchema
            settings = [(field.InitialVisibility, field.InitialColour) for field in event_schema if field.Available]
            self.FindChildNode(G_Project.NodeID_EventField).OverrideSettings(settings)


    #-------------------------------------------------------
    def UpdateMetricContent(self):
        def Work(node):
            node.UpdateMetricContent()

        self.VisitSubNodes(Work, factory_id = G_Project.NodeID_MetricsProjector, recursive = True)


    @G_Global.TimeFunction
    def UpdateEventContent(self):
        """Load event/feature data into the viewer"""

        # load events into event viewer data control
        events_view = self.GetTableViewCtrl()
        projector_info, is_valid = self.GetProjectorInfo()
        event_schema = projector_info.ProjectionSchema
        events_db_path = projector_info.ProjectionDbPath
        events_view.UpdateContent(self.GetNesting(), event_schema, events_db_path, is_valid)
        
        self.GetLogAnalysisNode().ActivateSubTab(events_view)

        # forward to child metrics views
        self.UpdateMetricContent()


    #-------------------------------------------------------
    def PermitNesting(self):
        projector_info, is_valid = self.GetProjectorInfo()
        return projector_info.ProjectionSchema.PermitNesting

    def UpdateNesting(self, nesting):
        self.GetTableViewCtrl().UpdateDisplay(nesting = nesting)

    def UpdateValidity(self, valid):
        self.GetTableViewCtrl().UpdateDisplay(valid = valid)



## G_ParameterValues #######################################

class G_ParameterValues:
    """Accessor for the parameter values dictionary"""

    #-------------------------------------------------------
    def __init__(self, param_values_str):
        try:
            self._Values = json.loads(param_values_str)
        except json.decoder.JSONDecodeError as ex:
            self._Values = dict()

    def GetAsString(self):
        return json.dumps(self._Values)


    #-------------------------------------------------------
    def GetValues(self, chart_no):
        # for JSON compatibility, dictionary key has to be string
        return self._Values.setdefault(str(chart_no), dict())


    #-------------------------------------------------------
    def GetValue(self, chart_no, param_name):
        return self.GetValues(chart_no).get(param_name)

    def SetValue(self, chart_no, param_name, value):
        self.GetValues(str(chart_no))[param_name] = value


    
## G_MetricsProjectorOptionsNode ###########################

class G_MetricsProjectorOptionsNode(G_ProjectorChildNode, G_TabContainedNode):

    #-------------------------------------------------------
    def BuildPage(parent):
        # class static function
        me = __class__
        me._Sizer = parent.GetSizer()

        window = parent.GetWindow()

        me._SelectChartCtl = wx.Choice(window)
        me._SelectChartSizer = me.BuildLabelledRow(parent, "Select chart", me._SelectChartCtl)

        pane = me.DynamicPane = wx.Panel(window)
        pane.SetSizer(wx.BoxSizer(wx.VERTICAL))
        me._Sizer.Add(pane, flag = wx.EXPAND)


    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem, name, **kwargs):
        G_TabContainedNode.__init__(self, factory, wproject, witem)
        G_ThemeNode.__init__(self, G_ThemeNode.DomainEvent)


    def PostInitNode(self):
        self._Field = D_Document(self.GetDocument(), self)
        self._ParameterValues = G_ParameterValues(self._Field.ParameterValues.Value)
        self._QuantifierName = self.GetParentNode().GetQuantifierName()



    #-------------------------------------------------------
    def ActivateSelectChart(self):
        error_reporter = self.GetProjectorNode().GetErrorReporter()
        with G_ScriptGuard("ActivateSelectChart", error_reporter):
            quantifier_info, is_valid = self.GetProjectorNode().GetQuantifierInfo()
            num_charts = 0

            if quantifier_info is not None:
                chart_names = [c.Name for c in quantifier_info.Charts]
                num_charts = len(chart_names)
                self._SelectChartCtl.Set(chart_names)

                self.Rebind(self._SelectChartCtl, wx.EVT_CHOICE, self.OnSelectChart)

                chart_no = self._Field.idxSelectChart.Value
                if chart_no >= num_charts:
                    chart_no = self._Field.idxSelectChart.Value = 0
                self._SelectChartCtl.SetSelection(chart_no)

            else:
                self._SelectChartCtl.Clear()
                self._SelectChartCtl.Unbind(wx.EVT_CHOICE)

            self._Sizer.Show(self._SelectChartSizer, num_charts > 1, True)


    #-------------------------------------------------------
    def ActivateDynamicPane(self):
        parameters = self._Parameters = self.GetChartViewCtrl(activate = False).DefineParameters()
        pane = self.DynamicPane
        sizer = pane.GetSizer()
        sizer.Clear(delete_windows = True)

        # build UI controls for the parameters
        if parameters is not None:
            info = G_WindowInfo(sizer, pane)
            chart_no = self._Field.idxSelectChart.Value

            for param in parameters:
                value = self._ParameterValues.GetValue(chart_no, param.Name)
                ctrl = param.MakeControl(pane, value, self.OnDynamicCtrl)
                self.BuildLabelledRow(info, param.Title, ctrl)


    #-------------------------------------------------------
    def Activate(self):
        self.ActivateCommon()
        self.ActivateSelectChart()
        self.ActivateDynamicPane()


    #-------------------------------------------------------
    def GetChartViewCtrl(self, activate):
        chart_no = self._Field.idxSelectChart.Value
        return self.GetParentNode().GetMetricsViewCtrl().GetChartViewCtrl(chart_no, activate)


    #-------------------------------------------------------
    def OnSelectChart(self, event):
        self._Field.idxSelectChart.Value = self._SelectChartCtl.GetSelection()

        pane = self.DynamicPane
        pane.Freeze()
        self.ActivateDynamicPane()
        pane.GetSizer().Layout()
        pane.Thaw()

        self.PushParameterValues(activate_chart = True)


    #-------------------------------------------------------
    def PushParameterValues(self, activate_chart):
        chart_ctrl = self.GetChartViewCtrl(activate = activate_chart)
        values = self._ParameterValues.GetValues(self._Field.idxSelectChart.Value)
        chart_ctrl.Update(parameters = values)


    def OnDynamicCtrl(self, event = None):
        chart_no = self._Field.idxSelectChart.Value
        for param in self._Parameters:
            self._ParameterValues.SetValue(chart_no, param.Name, param.GetValue())

        self._Field.ParameterValues.Value = self._ParameterValues.GetAsString()
        self.PushParameterValues(activate_chart = False)



## G_MetricsProjectorNode ##################################

class G_MetricsProjectorNode(G_LogAnalysisChildProjectorNode, G_TabContainerNode):

    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem, name, **kwargs):
        G_LogAnalysisChildProjectorNode.__init__(self)
        G_TabContainerNode.__init__(self, factory, wproject, witem)
        self._Name = name

    def PostInitNode(self):
        # make document fields accessible
        self._Field = D_Document(self.GetDocument(), self)

        # setup UI
        display_notebook = self.GetDisplayNoteBook()
        metrics_viewer = self._MetricsViewer = G_MetricsViewCtrl(display_notebook, self.OnTableSelectionChanged, self._Name)
        display_notebook.AddPage(metrics_viewer, self._Name)
        self.SetDisplayCtrl(display_notebook, metrics_viewer, owns_display_ctrl = False)
        self.SetupTableViewIntercepts()
        table_ctrl = metrics_viewer.GetTableViewCtrl()
        self.SetupDataExplorer(table_ctrl.GetModel(), table_ctrl)


    #-------------------------------------------------------
    def Activate(self):
        self.ActivateContainer()


    #-------------------------------------------------------
    def ReleaseFiles(self):
        """Release all resources owned by the view"""
        self.GetMetricsViewCtrl().ResetModel()

    def DoClose(self, delete):
        self.ReleaseFiles()
        super().DoClose(delete)


    #-------------------------------------------------------
    def GetEventProjectorNode(self):
        return self.GetParentNode(G_Project.NodeID_EventProjector)

    def GetQuantifierInfo(self):
        projector_info, is_valid = self.GetEventProjectorNode().GetProjectorInfo()
        return projector_info.GetQuantifierInfo(self._Name), is_valid

    def GetMetricsViewCtrl(self):
        return self._MetricsViewer

    def GetTableViewCtrl(self):
        return self.GetMetricsViewCtrl().GetTableViewCtrl()


    #-------------------------------------------------------
    def GetQuantifierName(self):
        return self._Name


    #-------------------------------------------------------
    def OnTableSelectionChanged(self, item):
        if item is None:
            # ignore de-selection events
            return

        # tell the data explorer
        self.GetDataExplorer().Update(self.MakeDataUrl(self.GetMetricsViewCtrl().GetTableViewCtrl().GetLocation(item)))


    #-------------------------------------------------------
    def OnDisplayKey(self, key_code, modifiers, view_node):
        handled = False
        return handled


    #-------------------------------------------------------
    def OnFilterMatch(self, match):
        """The filter has changed"""
        if self.GetTableViewCtrl().UpdateFilter(match):
            self.GetMetricsViewCtrl().UpdateMetrics()
            return True
        else:
            return False


    #-------------------------------------------------------
    @G_Global.TimeFunction
    def UpdateMetricContent(self):
        quantifier_info, is_valid = self.GetQuantifierInfo()
        error_reporter = self.GetErrorReporter()
        self.GetMetricsViewCtrl().Quantify(self, quantifier_info, is_valid, error_reporter)
        self.FindChildNode(G_Project.NodeID_MetricsProjectorOptions).PushParameterValues(activate_chart = True)

    def UpdateValidity(self, valid):
        self.GetTableViewCtrl().UpdateDisplay(valid = valid)



## MODULE ##################################################

G_Project.RegisterNodeFactory(
    G_NodeFactory(G_Project.NodeID_AnalyserScript, G_Project.ArtCtrlId_Script, G_AnalyserScriptNode)
)

G_Project.RegisterNodeFactory(
    G_NodeFactory(G_Project.NodeID_EventAnalyse, G_Project.ArtCtrlId_Analyse, G_EventAnalyseNode)
)

G_Project.RegisterNodeFactory(
    G_NodeFactory(G_Project.NodeID_LogAnalysisLocalThemeGallery, G_Project.ArtCtrlId_None, G_LogAnalysisLocalThemeGalleryNode)
)

G_Project.RegisterNodeFactory(
    G_NodeFactory(G_Project.NodeID_LogAnalysisLocalThemeOverrides, G_Project.ArtCtrlId_None, G_LogAnalysisLocalThemeOverridesNode)
)

G_Project.RegisterNodeFactory(
    G_NodeFactory(G_Project.NodeID_LogAnalysisThemeContainer, G_Project.ArtCtrlId_Theme, G_LogAnalysisThemeContainerNode)
)

G_Project.RegisterNodeFactory(
    G_NodeFactory(G_Project.NodeID_LogAnalysis, G_Project.ArtDocID_Folder, G_LogAnalysisNode)
)

G_Project.RegisterNodeFactory(
    G_NodeFactory(G_Project.NodeID_EventProjectorOptions, G_Project.ArtCtrlId_Options, G_EventProjectorOptionsNode)
)

G_Project.RegisterNodeFactory(
    G_NodeFactory(G_Project.NodeID_TableSearch, G_Project.ArtCtrlId_None, G_TableSearchNode)
)

G_Project.RegisterNodeFactory(
    G_NodeFactory(G_Project.NodeID_TableSearchContainer, G_Project.ArtCtrlId_Search, G_TableSearchContainerNode)
)

G_Project.RegisterNodeFactory(
    G_NodeFactory(G_Project.NodeID_TableFilter, G_Project.ArtCtrlId_Filter, G_TableFilterNode)
)

G_Project.RegisterNodeFactory(
    G_NodeFactory(G_Project.NodeID_EventTracking, G_Project.ArtCtrlId_Tracker, G_EventTrackingNode)
)

G_Project.RegisterNodeFactory(
    G_NodeFactory(G_Project.NodeID_EventField, G_Project.ArtCtrlId_Fields, G_EventFieldNode)
)

G_Project.RegisterNodeFactory(
    G_NodeFactory(G_Project.NodeID_EventProjector, G_Project.ArtDocID_EventProjector, G_EventProjectorNode)
)

G_Project.RegisterNodeFactory(
    G_NodeFactory(G_Project.NodeID_MetricsProjectorOptions, G_Project.ArtCtrlId_Options, G_MetricsProjectorOptionsNode)
)

G_Project.RegisterNodeFactory(
    G_NodeFactory(G_Project.NodeID_MetricsProjector, G_Project.ArtDocID_MetricsProjector, G_MetricsProjectorNode)
)
