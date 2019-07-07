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

# wxWidgets imports
import wx
import wx.stc

# Application imports 
from .Document import D_Document
from .Logfile import G_DisplayNode
from .Logfile import G_DisplayChildNode
from .MatchNode import G_MatchItem
from .MatchNode import G_MatchNode
from .Project import G_Const
from .Project import G_TabContainedNode
from .Project import G_TabContainerNode
from .Project import G_ListContainedNode
from .Project import G_ListContainerNode
from .Project import G_HideableTreeNode
from .Project import G_NodeFactory
from .Project import G_Project
from .StyleNode import G_ColourNode
from .StyleNode import G_EnabledColourNode
from .StyleNode import G_HiliteStyleNode
from .Theme import G_ThemeNode
from .Theme import G_ThemeOverridesNode
from .Theme import G_ThemeGalleryNode

# Content provider interface
import Nlog


## G_ViewChildNode #########################################

class G_ViewChildNode(G_DisplayChildNode):
    """Mixin class to extend child nodes of a view node with common behaviour"""

    #-------------------------------------------------------
    def GetViewNode(self):
        # recursive lookup; find our view node
        return self.GetParentNode(G_Project.NodeID_View)


    #-------------------------------------------------------
    def GetView(self):
        """Fetch the Nlog view object associated with the view node"""
        return self.GetViewNode().GetView()



## G_ViewSearchNode ########################################

class G_ViewSearchNode(G_ViewChildNode, G_ThemeNode, G_MatchNode, G_ColourNode, G_HiliteStyleNode, G_ListContainedNode):
    """A hiliter/search control"""

    #-------------------------------------------------------
    def BuildPage(parent):
        # class static function
        me = __class__
        me._Sizer = parent.GetSizer()

        # add child controls
        G_MatchNode.BuildMatch(me, parent, "Search", search = True, search_buttons = True)
        G_ColourNode.BuildColour(me, parent)
        G_HiliteStyleNode.BuildStyle(me, parent)


    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem, name, **kwargs):
        G_ListContainedNode.__init__(self, factory, wproject, witem)
        G_MatchNode.__init__(self, G_Const.ViewThemeCls, "Search")
        G_HiliteStyleNode.__init__(self)
        G_ThemeNode.__init__(self, G_ThemeNode.DomainView)


    #-------------------------------------------------------
    def PostInitNode(self):
        self._Field = D_Document(self.GetDocument(), self)

    def PostInitLoad(self):
        # themes are setup now
        self.PostInitColour()
        self.PostInitStyle()
        self.PostInitMatch()


    #-------------------------------------------------------
    def Activate(self):
        focus_window = self.ActivateMatch()
        self.ActivateColour()
        self.ActivateStyle()
        self.ActivateCommon(focus_window)


    #-------------------------------------------------------
    def OnMatch(self, match_item, refocus = None):
        """The match text has altered; refresh the Scintilla control"""
        if self.GetViewNode().UpdateHiliterMatch(self.GetIndex(), match_item):
            self.SendFocusToDisplayCtrl(refocus)
            return True
        else:
            return False


    #-------------------------------------------------------
    def OnColour(self, refocus):
        """The colour has altered; refresh the Scintilla control"""
        self.GetViewNode().UpdateHiliterColour(self.GetIndex(), self.GetColour())
        self.SendFocusToDisplayCtrl(refocus)


    #-------------------------------------------------------
    def OnStyle(self, refocus):
        """The style has altered; refresh the Scintilla control"""
        self.GetViewNode().UpdateHiliterStyle(self.GetIndex(), self.GetStyle())
        self.SendFocusToDisplayCtrl(refocus)


    #-------------------------------------------------------
    def OnThemeChange(self, theme_cls, theme_id):
        """The colour and/or style has altered; refresh the the associated editors"""
        if theme_cls == G_Const.GlobalThemeCls:
            self.SetColourTheme()
            self.SetStyleTheme()
        else:
            G_MatchNode.OnThemeChange(self, theme_cls, theme_id)


    #-------------------------------------------------------
    def OnSearch(self, forward = None, modifiers = None):
        """A forward or reverse search has been requested"""
        self.GetViewNode().GotoNextLine("hilite", forward, modifiers, self.GetIndex())
        if modifiers is None:
            self.SendFocusToDisplayCtrl()


    #-------------------------------------------------------
    def OnDisplayKey(self, key_code, modifiers, view_node):
        """Intercept key presses sent to the Scintilla control"""
        if key_code < ord("1") or key_code > ord("6"):
            return False

        index = key_code - ord("0")
        if index != self.GetIndex():
            return False

        if modifiers & wx.MOD_CONTROL != 0:
            modifiers = modifiers & ~wx.MOD_CONTROL
            text = view_node.GetSelectedText()

            if len(text) == 0:
                return True
            else:
                # clear the "selection" hiliter
                self.GetParentNode().GetChildNode(0).SetMatch(G_MatchItem("Literal", ""), make_active = False, refocus = False)

                # copy selection into this hiliter, then continue with fwd/rev search
                self.SetMatch(G_MatchItem("Literal", text))

        self.OnSearch(modifiers = modifiers)

        return True



## G_ViewSearchContainerNode ###############################

class G_ViewSearchContainerNode(G_ViewChildNode, G_ListContainerNode):
    """Container node for hosting hiliters"""

    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem, name, **kwargs):
        super().__init__(factory, wproject, witem)

    def PostInitChildren(self):
        # have to know how many children there are in order to initialise the view ...
        self.GetView().SetNumHiliter(self.GetHrItem().GetChildrenCount())


    #-------------------------------------------------------
    def Activate(self):
        self.ActivateCommon()
        G_ListContainerNode.ActivateContainer(self)
        self.SetNodeHelp("View Searching & Hiliting", "views.html", "viewhiliters")



## G_ViewFieldNode #########################################

class G_ViewFieldNode(G_ViewChildNode, G_ThemeNode, G_EnabledColourNode, G_TabContainedNode):
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
        G_ThemeNode.__init__(self, G_ThemeNode.DomainView)


    #-------------------------------------------------------
    def PostInitNode(self):
        self._Field = D_Document(self.GetDocument(), self)

    def PostInitLoad(self):
        self.PostInitColour()


    #-------------------------------------------------------
    def Activate(self):
        self.ActivateCommon()
        self.ActivateEnabledColour(self.GetFieldNames())
        self.SetNodeHelp("View Field Visibility", "views.html", "viewfields")


    #-------------------------------------------------------
    def GetLogSchema(self):
        return self.GetLogNode().GetLogSchema()

    def GetFieldNames(self):
        return self.GetLogSchema().GetFieldNames()


    #-------------------------------------------------------
    def OnColour(self, field_id):
        """A colour has altered; refresh the Scintilla control"""
        self.GetViewNode().UpdateFieldColour(field_id, self.GetColour(field_id))

    def OnEnable(self):
        """An enable checkbox has changed state; update view"""
        field_mask = self.GetEnabledAsMask()
        self.GetViewNode().SetFieldMask(field_mask)


    #-------------------------------------------------------
    def OnThemeChange(self, theme_cls, theme_id):
        if self.IsThemeApplicable(theme_cls, theme_id, G_Const.ViewThemeCls):
            self.SetEnabledColourTheme(self.GetFieldNames())



## G_ViewFilterNode ########################################

class G_ViewFilterNode(G_ViewChildNode, G_ThemeNode, G_MatchNode, G_TabContainedNode):
    """A filter control"""

    #-------------------------------------------------------
    def BuildPage(parent):
        # class static function
        me = __class__
        me._Sizer = parent.GetSizer()

        # add match controls
        G_MatchNode.BuildMatch(me, parent, "Filter", height = 75, filter = True)

        # view metrics information
        me.LblLineCount = wx.StaticText(parent.GetWindow(), label = "#")
        me.BuildLabelledRow(parent, "Line count", me.LblLineCount)
        me.LblSize = wx.StaticText(parent.GetWindow(), label = "#")
        me.BuildLabelledRow(parent, "Size", me.LblSize)


    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem, name, **kwargs):
        G_MatchNode.__init__(self, G_Const.ViewThemeCls, "Filter")
        G_TabContainedNode.__init__(self, factory, wproject, witem)
        G_ThemeNode.__init__(self, G_ThemeNode.DomainView)

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
        self.SetNodeHelp("View Filtering", "views.html", "viewfilters")


    #-------------------------------------------------------
    def SetMetrics(self):
        editor = self.GetViewNode().GetEditor()
        self.LblLineCount.SetLabelText("{0:,}".format(editor.GetLineCount()))
        self.LblSize.SetLabelText("{0:,}".format(editor.GetTextLength()))


    #-------------------------------------------------------
    def OnMatch(self, match, refocus = None):
        if self.GetViewNode().UpdateFilter(match):
            self.SetMetrics()
            self.SendFocusToDisplayCtrl(refocus)
            return True
        else:
            return False


    #-------------------------------------------------------
    def OnThemeChange(self, theme_cls, theme_id):
        """The match has altered; refresh match controls and the associated editors"""
        G_MatchNode.OnThemeChange(self, theme_cls, theme_id)



## G_TrackInfo ############################################

class G_TrackInfo(D_Document.D_Value):
    """Store for a view's tracking behaviour"""

    _GlobalSourceNames = ["None"]
    _SynchroniseNames = ["None"]

    @staticmethod
    def SetupNames():
        """Setup the global list of tracker names"""

        me = __class__

        # i.e. None and global tracker names
        me._GlobalSourceNames.extend(G_Const.GlobalTrackerNames)

        # i.e. None and all tracker names; first name is the local tracker
        me._SynchroniseNames.append(G_Const.LocalTrackerName)
        me._SynchroniseNames.extend(G_Const.GlobalTrackerNames)


    #-------------------------------------------------------
    def __init__(self, src = None):
        if src is None:
            self.bUpdateLocal = True
            self.idxUpdateGlobal = 0
            self.idxSyncSource = 0
        else:
            self.bUpdateLocal = src.bUpdateLocal
            self.idxUpdateGlobal = src.idxUpdateGlobal
            self.idxSyncSource = src.idxSyncSource


    #-------------------------------------------------------
    def UpdateLocal(self):
        """Return True if the local tracker should be updated by the owning view"""
        return self.bUpdateLocal

    def UpdateGlobalIdx(self):
        """Return index of global tracker to update, or < 0 if none"""
        return self.idxUpdateGlobal - 1


    #-------------------------------------------------------
    def SyncLocal(self):
        """Return True if the view should synchronise with the local tracker"""
        return self.idxSyncSource == 1

    def SyncGlobalIdx(self):
        """Return index of global tracker to synchronise with, or < 0 if none"""
        return self.idxSyncSource - 2



## G_ViewTrackingNode ######################################

class G_ViewTrackingNode(G_ViewChildNode, G_ThemeNode, G_TabContainedNode):
    """Define the view's tracking behaviour"""

    #-------------------------------------------------------
    def BuildPage(parent):
        # class static function
        me = __class__
        me._Sizer = parent.GetSizer()

        window = parent.GetWindow()
        me._CheckBoxes = []

        # check: view should update local tracker from cursor
        me._UpdateLocalCtl = wx.CheckBox(window)
        me.BuildLabelledRow(parent, "Set local tracker from cursor", me._UpdateLocalCtl)

        # combo: view should update one of the global trackers from cursor
        me._UpdateGlobalCtl = wx.Choice(window)
        me._UpdateGlobalCtl.Set(G_TrackInfo._GlobalSourceNames)
        me.BuildLabelledRow(parent, "Set global tracker from cursor", me._UpdateGlobalCtl)

        # combo: view should keep the named tracker visible on the screen (scroll)
        me._SynchroniseCtl = wx.Choice(window)
        me._SynchroniseCtl.Set(G_TrackInfo._SynchroniseNames)
        me.BuildLabelledRow(parent, "Synchronise view to tracker", me._SynchroniseCtl)


    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem, name, **kwargs):
        G_TabContainedNode.__init__(self, factory, wproject, witem)
        G_ThemeNode.__init__(self, G_ThemeNode.DomainView)

    def PostInitNode(self):
        self._Field = D_Document(self.GetDocument(), self)
        self.ResetTrackInfo()


    #-------------------------------------------------------
    def Activate(self):
        self.ActivateCommon()

        track_info = self.GetTrackInfo()

        self._UpdateLocalCtl.Unbind(wx.EVT_CHECKBOX)
        self._UpdateLocalCtl.SetValue(track_info.bUpdateLocal)
        self._UpdateLocalCtl.Bind(wx.EVT_CHECKBOX, self.OnUpdateLocal)

        self.Rebind(self._UpdateGlobalCtl, wx.EVT_CHOICE, self.OnUpdateGlobal)
        self._UpdateGlobalCtl.SetSelection(track_info.idxUpdateGlobal)

        self.Rebind(self._SynchroniseCtl, wx.EVT_CHOICE, self.OnUpdateSync)
        self._SynchroniseCtl.SetSelection(track_info.idxSyncSource)

        self.SetNodeHelp("View Tracking", "views.html", "viewtracking")


    #-------------------------------------------------------
    def ResetTrackInfo(self):
        self._TrackInfo = None

    def GetTrackInfo(self):
        if self._TrackInfo is None:
            self._TrackInfo = G_TrackInfo(self._Field.TrackInfo.Value)
        return self._TrackInfo


    #-------------------------------------------------------
    def OnThemeChange(self, theme_cls, theme_id):
        if self.IsThemeApplicable(theme_cls, theme_id, G_Const.ViewThemeCls):
            self.ResetTrackInfo()

    def OnUpdateLocal(self, event):
        self._Field.TrackInfo.bUpdateLocal.Value = self._UpdateLocalCtl.GetValue()
        self.ResetTrackInfo()
        self.SendFocusToDisplayCtrl()

    def OnUpdateGlobal(self, event):
        self._Field.TrackInfo.idxUpdateGlobal.Value = self._UpdateGlobalCtl.GetSelection()
        self.ResetTrackInfo()
        self.SendFocusToDisplayCtrl()

    def OnUpdateSync(self, event):
        self._Field.TrackInfo.idxSyncSource.Value = self._SynchroniseCtl.GetSelection()
        self.ResetTrackInfo()
        self.SendFocusToDisplayCtrl()



## G_ViewGlobalThemeOverrideNode ###########################

class G_ViewGlobalThemeOverrideNode(G_ViewChildNode, G_ThemeOverridesNode, G_ListContainedNode):
    """View theme overrides saving/restoring"""

    #-------------------------------------------------------
    def BuildPage(parent):
        # class static function
        me = __class__
        me._Sizer = parent.GetSizer()

        G_ThemeOverridesNode.BuildControl(me, parent)


    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem, name, **kwargs):
        G_ListContainedNode.__init__(self, factory, wproject, witem)
        G_ThemeOverridesNode.__init__(self, G_Const.GlobalThemeCls, G_ThemeNode.DomainView)


    #-------------------------------------------------------
    def Activate(self):
        self.SetNodeHelp("Navigation Themes", "views.html", "viewnavigation")
        self.ActivateControl()



## G_ViewLocalThemeGalleryNode #############################

class G_ViewLocalThemeGalleryNode(G_ViewChildNode, G_ThemeGalleryNode, G_ListContainedNode):
    """View theme gallery"""

    #-------------------------------------------------------
    def BuildPage(parent):
        # class static function
        me = __class__
        me._Sizer = parent.GetSizer()

        G_ThemeGalleryNode.BuildGallery(me, parent, "view")


    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem, name, **kwargs):
        G_ListContainedNode.__init__(self, factory, wproject, witem)
        G_ThemeGalleryNode.__init__(self, G_Const.ViewThemeCls)

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
        self.SetNodeHelp("View Pattern Themes", "views.html", "viewpatterns")
        self.ActivateThemeGallery()



## G_ViewLocalThemeOverridesNode ##########################

class G_ViewLocalThemeOverridesNode(G_ViewChildNode, G_ThemeOverridesNode, G_ListContainedNode):
    """View local theme overrides saving/restoring"""

    #-------------------------------------------------------
    def BuildPage(parent):
        # class static function
        me = __class__
        me._Sizer = parent.GetSizer()

        G_ThemeOverridesNode.BuildControl(me, parent)


    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem, name, **kwargs):
        G_ListContainedNode.__init__(self, factory, wproject, witem)
        G_ThemeOverridesNode.__init__(self, G_Const.ViewThemeCls, G_ThemeNode.DomainView)


    #-------------------------------------------------------
    def Activate(self):
        self.SetNodeHelp("View Pattern Themes", "views.html", "viewpatterns")
        self.ActivateControl()



## G_ViewThemeContainerNode ###############################

class G_ViewThemeContainerNode(G_ViewChildNode, G_ListContainerNode):
    """Container node for hosting theme controls"""

    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem, name, **kwargs):
        super().__init__(factory, wproject, witem)


    #-------------------------------------------------------
    def Activate(self):
        G_ListContainerNode.ActivateContainer(self)



## G_ViewNode ##############################################

class G_ViewNode(G_DisplayNode, G_HideableTreeNode, G_TabContainerNode):
    """Class that implements a view onto a logfile"""

    # global tracker key binding map to tracker index
    _GlobalTrackerKeys = {
        ord("G"): 0,
        ord("H"): 1,
        ord("J"): 2, 
        ord("K"): 3
    }

    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem, name, **kwargs):
        # track our position in the project tree
        G_DisplayNode.__init__(self)
        G_TabContainerNode.__init__(self, factory, wproject, witem)
        self._CursorLine = -1
        self._AutoHiliteText = ""
        self._OrigNameId = name.split("/")[-1]


    def PostInitNode(self):
        # make document fields accessible
        self._Field = D_Document(self.GetDocument(), self)

        # apply any user override to the node's label
        self.SetTreeLabel(self.GetNodeLabel())

        # ensure non-template fields exist and are initialised
        self._Field.Add(0, "FirstVisibleLine", replace_existing = False)
        self._Field.Add(0, "CursorLine", replace_existing = False)

        # make a Scintilla editor and a Nlog logfile view
        notebook = self.GetNotebook()
        editor = self.SetDisplayCtrl(wx.stc.StyledTextCtrl(notebook, -1))
        self.InterceptKeys(editor)
        editor.Bind(wx.stc.EVT_STC_UPDATEUI, self.OnUpdateUI)

        self._N_View = self.GetLogfile().CreateView()

        # make a Scintilla document to display the view, and
        # add it to the Scintilla editor
        self._S_Document = editor.CreateDocument(self._N_View.GetContent())
        editor.SetDocPointer(self._S_Document)

        # setup default text style
        editor.StyleSetFont(wx.stc.STC_STYLE_DEFAULT, wx.Font(wx.FontInfo(9).FaceName("Segoe UI")))
        editor.StyleClearAll()

        # setup formatter styles
        styleset = None
        formatter = self.GetLogNode().GetLogSchema().GetFormatter()
        if formatter is not None:
            styleset = formatter.GetStyleSet()
        if styleset is not None:
            for style in styleset.GetStyles():
                style_no = style.GetStyleNumber()
                editor.StyleSetBold(style_no, style.IsBold())
                editor.StyleSetItalic(style_no, style.IsItalic())
                editor.StyleSetUnderline(style_no, style.IsUnderline())
                editor.StyleSetForeground(style_no, style.ForeColour())

        # setup Scintilla indicators - used for highlighting
        editor.IndicatorSetStyle(0, wx.stc.STC_INDIC_ROUNDBOX)

        # setup Scintilla editor margins
        marker_mask = (2 ** Nlog.EnumConstants.StyleBaseTracker) - 1
        editor.SetMarginType(1, wx.stc.STC_MARGIN_SYMBOL)
        editor.SetMarginWidth(1, 14)
        editor.SetMarginMask(1, marker_mask)

        tracker_mask = 0xffffffff & ~marker_mask
        editor.SetMarginType(2, wx.stc.STC_MARGIN_SYMBOL)
        editor.SetMarginWidth(2, 14)
        editor.SetMarginMask(2, tracker_mask)

        # setup cursor unwanted zone (UZ); keeps GotoLine away from the top/bottom
        # of the screen
        editor.SetYCaretPolicy(wx.stc.STC_CARET_SLOP | wx.stc.STC_CARET_EVEN, 10)

        # setup caret line hiliting
        from .StyleNode import G_ColourTraits
        editor.SetCaretLineBackground(G_ColourTraits.GetColour("GOLDENROD"))
        editor.SetCaretLineBackAlpha(50)
        editor.SetCaretLineVisible(True)

        # setup annotation styles
        editor.AnnotationSetVisible(wx.stc.STC_ANNOTATION_BOXED)
        from .StyleNode import G_AnnotationTraits
        for a in G_AnnotationTraits.Get():
            style_no = a[1]
            editor.StyleSetItalic(style_no, True)
            editor.StyleSetForeground(style_no, a[2])
            editor.StyleSetBackground(style_no, a[3])

        # editor must be set to read-only; switches off behaviour that Nlog
        # does not implement
        editor.SetReadOnly( True );

        # and add the Scintilla editor to the main notebook, without altering focus
        def Work():
            notebook.AddPage(editor, self.GetNodeLabel(), True)
        self.WithFocusLock(Work)

        # ensure markers are set correctly
        self.GetLogNode().SetMarkersForView(self)


    def PostInitChildren(self):
        # set the cursor to its last-known line; ideally, we would set this to the
        # last known position, but we are not in control of window size at this point,
        # and in practice the window is small, so when a position is set, Scintilla
        # applies a horizontal scroll, which looks strange after the window is restored
        # to its full size
        self.SetScreenState( (self._Field.FirstVisibleLine.Value, self._Field.CursorLine.Value) )


    def PostInitLayout(self):
        self.PostInitHideableTreeNode()


    #-------------------------------------------------------
    def Activate(self):
        self.ActivateContainer()


    #-------------------------------------------------------
    def CreatePopupMenu(self, handlers):
        menu = None

        if self.IsParentNodeDisplayed():
            menu = wx.Menu("View")
            self.AppendPopupShowHide(menu, handlers)
            self.AppendPopupDeleteNode(menu, handlers, True)

        return menu


    #-------------------------------------------------------
    def DoClose(self, delete):
        """Release all resources owned by the view"""

        if self._S_Document is not None:
    	    # detach and release Scintilla document from the edit control
            editor = self.GetEditor()
            editor.SetDocPointer( 0 )
            editor.ReleaseDocument(self._S_Document)

            # force release references to Nlog objects
            self._S_Document = None
            self._N_View = None

        super().DoClose(delete)


    #-------------------------------------------------------
    def GetAnnotationNode(self):
        return self.GetRootNode().FindChildNode(G_Project.NodeID_Annotation, recursive = True)

    def UpdateAnnotation(self, line = None):
        self.GetAnnotationNode().UpdateAnnotation(view_node = self, line = line)

    def OnDisplayFocus(self):
        # keep the annotation display synchronised with the active view
        self.UpdateAnnotation()


    #-------------------------------------------------------
    def GetEditor(self):
        return self.GetDisplayCtrl()

    def GetSelectedText(self):
        """Fetch the selected text in the editor"""
        return self.GetEditor().GetSelectedText()

    def GetView(self):
        return self._N_View

    def GetDefaultNodeLabel(self):
        return "{}/{}".format(self.GetLogNode().GetNodeLabel(), self._OrigNameId)


    #-------------------------------------------------------
    def GetTrackInfo(self):
        return self.FindChildNode(G_Project.NodeID_ViewTracking).GetTrackInfo()

    def GetUtcTimecode(self, line_no):
        return self._N_View.GetUtcTimecode(line_no)


    #-------------------------------------------------------
    def GetScreenState(self):
        editor = self.GetEditor()
        return (editor.GetFirstVisibleLine(), editor.LineFromPosition(editor.GetCurrentPos()))

    def SetScreenState(self, state_tuple):
        # note: order is important
        (first_line, cursor_line) = state_tuple
        editor = self.GetEditor()
        editor.GotoLine(cursor_line)
        editor.SetFirstVisibleLine(first_line)


    #-------------------------------------------------------
    def GotoNextLine(self, what, forward = None, modifiers = None, index = 0):
        # call should pass either forward or modifiers
        if modifiers is not None:
            if modifiers == 0:
                forward = True
            elif modifiers == wx.MOD_SHIFT:
                forward = False
            else:
                # invalid key combination, so nothing to do
                return

        editor = self.GetEditor()
        cur_line = editor.LineFromPosition(editor.GetCurrentPos())

        if what == "bookmark":
            next_line = self._N_View.GetNextBookmark(cur_line, forward)
        elif what == "annotation":
            next_line = self._N_View.GetNextAnnotation(cur_line, forward)
        elif what == "hilite":
            next_line = self._N_View.GetHiliter(index).Search(cur_line, forward)

        if next_line >= 0:
            editor.GotoLine(next_line)


    #-------------------------------------------------------
    def NotifyLine(self, line_number):
        """Notify the log line to the current channel listener(s)"""

        schema = self.GetLogNode().GetLogSchema()
        emitter_id = schema.GetEmitterId()
        if emitter_id < 0:
            return

        emitter_text = self._N_View.GetFieldText(line_number, emitter_id)
        if emitter_text != "":
            log_line = self.GetEditor().GetLine(line_number).rstrip("\n")
            message = schema.CreateLineNotificationMessage(log_line, emitter_text)
            channel = self.GetProject().GetChannel(schema.GetName(), schema.GetEffectiveChannelGuid())
            channel.Notify(message)


    #-------------------------------------------------------
    def NotifyPreSave(self):
        """A save has been requested; update view state"""
        (self._Field.FirstVisibleLine.Value, self._Field.CursorLine.Value) = self.GetScreenState()


    #-------------------------------------------------------
    def OnUpdateUI(self, event):
        """Dispatcher for changes made in the Scintilla control"""

        if event.Updated & wx.stc.STC_UPDATE_SELECTION:
            self.OnSelectionChange()


    def OnSelectionChange(self):
        """Use indicator zero to auto-hilite all occurances of the selected text in the view"""

        # set hiliter matching first
        text = self.GetSelectedText()
        if len(text) != 0 and text != self._AutoHiliteText:
            self._AutoHiliteText = text
            self.UpdateHiliterMatch(0, G_MatchItem("Literal", text))

        # everything else only meaningful when line changes
        editor = self.GetEditor()
        cur_line = editor.LineFromPosition(editor.GetSelectionEnd())
        if cur_line == self._CursorLine:
            return
        self._CursorLine = cur_line

        # identify tracking options
        info = self.GetTrackInfo()
        update_local = info.UpdateLocal()
        update_global_idx = info.UpdateGlobalIdx()
        update_global = update_global_idx >= 0
        update = update_local or update_global

        # update trackers
        if update:
            if update_local:
                self._N_View.SetLocalTrackerLine(cur_line)

            # capture new tracker data
            timecode = self.GetUtcTimecode(cur_line)
            self.UpdateTrackers(update_local, update_global_idx, [timecode])

            # flush any changes through to the GUI
            self.RefreshTrackers(update_local, update_global, self)

        # ensure annotation text is updated
        self.UpdateAnnotation(line = cur_line)

        # and tell the world
        self.NotifyLine(cur_line)

        # maintanance note - do not add any more random stuff to this function,
        # implement a proper notification system


    #-------------------------------------------------------
    def OnDisplayKey(self, key_code, modifiers, view_node):
        handled = False

        editor = self.GetEditor()
        cur_line = editor.LineFromPosition(editor.GetSelectionStart())
        if key_code == ord("B"):
            handled = True
            if modifiers ==  wx.MOD_CONTROL:
                # set a user bookmark on the current line(s)
                to_line = editor.LineFromPosition(editor.GetSelectionEnd())
                self._N_View.ToggleBookmarks(cur_line, to_line)
                self.GetLogNode().RefreshViews()

            else:
                self.GotoNextLine("bookmark", modifiers = modifiers)

        elif key_code == ord("C") and modifiers == 0:
            handled = True
            self.ScrollToLine(cur_line)

        elif key_code == ord("L"):
            if modifiers == 0:
                handled = True
                self.ScrollToLine(self._N_View.GetLocalTrackerLine())
            elif modifiers == wx.MOD_CONTROL:
                handled = True
                self._N_View.SetLocalTrackerLine(cur_line)
                self.RefreshTrackers(True, False, self)
                timecode = self.GetUtcTimecode(cur_line)
                self.UpdateTrackers(True, -1, [timecode])

        elif key_code in self._GlobalTrackerKeys:
            tracker_idx = self._GlobalTrackerKeys[key_code]
            if modifiers == 0:
                handled = True
                self.ScrollToLine(self._N_View.GetGlobalTrackerLine(tracker_idx))
            elif modifiers == wx.MOD_CONTROL:
                handled = True
                timecode = self.GetUtcTimecode(cur_line)
                Nlog.SetGlobalTracker(tracker_idx, timecode)
                self.RefreshTrackers(False, True, self)
                self.UpdateTrackers(False, tracker_idx, [timecode])

        # special check with the annotation node
        if not handled:
            handled = self.GetAnnotationNode().OnDisplayKey(key_code, modifiers, self)

        return handled


    #-------------------------------------------------------
    def ScrollToLine(self, line):
        editor = self.GetEditor()
        start = editor.PositionFromLine(line)
        end = editor.PositionFromLine(line + 1)
        editor.ScrollRange(start, end)


    #-------------------------------------------------------
    def SetFieldMask(self, field_mask):
        """Set the list of visible fields for this view"""

        # the update abuses Scintilla's internal notification system, so
        # manually preserve the screen state
        state = self.GetScreenState()
        self._N_View.SetFieldMask(field_mask)
        self.SetScreenState(state)
        self.GetEditor().Refresh()

    def UpdateFieldColour(self, field_id, colour):
        self.GetEditor().StyleSetForeground(field_id + 1, colour)


    #-------------------------------------------------------
    def RefreshView(self):
        self.GetEditor().Refresh()


    #-------------------------------------------------------
    def UpdateHiliterMatch(self, index, match):
        """A hiliter GUI page match field has been edited; update editor"""

        try:
            self._N_View.GetHiliter(index).SetSelector(match.MakeSelector(empty_selects_all = False))
            self.RefreshView()
            return True

        except RuntimeError:
            return False


    #-------------------------------------------------------
    def UpdateHiliterColour(self, index, colour):
        """A hiliter GUI page colour has been edited; update editor"""

        # set the selection indicator to draw on top of the text with alpha,
        # and the others underneath it (fully opaque)
        alpha = 128; under = False
        if index != 0:
            alpha = 255; under = True

        editor = self.GetEditor()
        editor.IndicatorSetAlpha(index, alpha)
        editor.IndicatorSetOutlineAlpha(index, 255)
        editor.IndicatorSetUnder(index, under)
        editor.IndicatorSetForeground(index, colour)


    #-------------------------------------------------------
    def UpdateHiliterStyle(self, index, style):
        """A hiliter GUI page style has been edited; update editor"""

        self.GetEditor().IndicatorSetStyle(index, style)


    #-------------------------------------------------------
    def UpdateFilter(self, match):
        """The filter GUI page has been altered; re-filter the logfile view"""

        selector = match.MakeSelector(self.GetLogfile())
        if selector is None:
            return False

        self._N_View.Filter(selector)
        return True



## MODULE ##################################################

G_TrackInfo.SetupNames()

G_Project.RegisterNodeFactory(
    G_NodeFactory(G_Project.NodeID_ViewSearch, G_Project.ArtCtrlId_None, G_ViewSearchNode)
)

G_Project.RegisterNodeFactory(
    G_NodeFactory(G_Project.NodeID_ViewSearchContainer, G_Project.ArtCtrlId_Search, G_ViewSearchContainerNode)
)

G_Project.RegisterNodeFactory(
    G_NodeFactory(G_Project.NodeID_ViewFilter, G_Project.ArtCtrlId_Filter, G_ViewFilterNode)
)

G_Project.RegisterNodeFactory(
    G_NodeFactory(G_Project.NodeID_ViewTracking, G_Project.ArtCtrlId_Tracker, G_ViewTrackingNode)
)

G_Project.RegisterNodeFactory(
    G_NodeFactory(G_Project.NodeID_ViewField, G_Project.ArtCtrlId_Fields, G_ViewFieldNode)
)

G_Project.RegisterNodeFactory(
    G_NodeFactory(G_Project.NodeID_ViewGlobalThemeOverrides, G_Project.ArtCtrlId_None, G_ViewGlobalThemeOverrideNode)
)

G_Project.RegisterNodeFactory(
    G_NodeFactory(G_Project.NodeID_ViewLocalThemeGallery, G_Project.ArtCtrlId_None, G_ViewLocalThemeGalleryNode)
)

G_Project.RegisterNodeFactory(
    G_NodeFactory(G_Project.NodeID_ViewLocalThemeOverrides, G_Project.ArtCtrlId_None, G_ViewLocalThemeOverridesNode)
)

G_Project.RegisterNodeFactory(
    G_NodeFactory(G_Project.NodeID_ViewThemeContainer, G_Project.ArtCtrlId_Theme, G_ViewThemeContainerNode)
)

G_Project.RegisterNodeFactory(
    G_NodeFactory(G_Project.NodeID_View, G_Project.ArtDocID_View, G_ViewNode)
)
