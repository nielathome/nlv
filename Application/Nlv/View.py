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

# Python imports
from math import log10

# wxWidgets imports
import wx
import wx.stc
from wx.lib.expando import ExpandoTextCtrl

# Application imports 
from .DataExplorer import G_DataExplorerProvider
from .DataExplorer import G_DataExplorerSync
from .Document import D_Document
from .Global import G_Const
from .Global import G_FrozenWindow
from .Global import G_Global
from .Logfile import G_DisplayNode
from .Logfile import G_DisplayChildNode
from .Logfile import G_DisplayControl
from .Logfile import G_PanelDisplayControl
from .MatchNode import G_MatchItem
from .MatchNode import G_MatchNode
from .Project import G_TabContainedNode
from .Project import G_TabContainerNode
from .Project import G_ListContainedNode
from .Project import G_ListContainerNode
from .Project import G_HideableTreeNode
from .Project import G_NodeFactory
from .Project import G_Project
from .StyleNode import G_ColourNode
from .StyleNode import G_ColourTraits
from .StyleNode import G_EnabledColourNode
from .StyleNode import G_HiliteStyleNode
from .StyleNode import G_StyleCombo
from .StyleNode import G_StyleTraits
from .Theme import G_ThemeNode
from .Theme import G_ThemeOverridesNode
from .Theme import G_ThemeGalleryNode

# Content provider interface
import Nlog



## G_StcView ###############################################

class G_StcView(wx.stc.StyledTextCtrl, G_DisplayControl):
    """STC editor displays the log data"""

    #-------------------------------------------------------
    def __init__(self, parent, ID = -1):
        wx.stc.StyledTextCtrl.__init__(self, parent, ID)



## G_ViewControl ###########################################

class G_ViewControl(G_PanelDisplayControl):

    #-------------------------------------------------------
    _StyleIdxBase = Nlog.EnumStyle.AnnotationBase

    _Descs = [
        # name, pen_style, scintilla style number, text colour, background
        ("Note", wx.PENSTYLE_TRANSPARENT, _StyleIdxBase + 0, "BLACK", "LEMON CHIFFON"),
        ("Good", wx.PENSTYLE_TRANSPARENT, _StyleIdxBase + 1, "NAVY", "LIGHT BLUE"),
        ("Neutral", wx.PENSTYLE_TRANSPARENT, _StyleIdxBase + 2, "SADDLE BROWN", "KHAKI"),
        ("Concern", wx.PENSTYLE_TRANSPARENT, _StyleIdxBase + 3, "FIREBRICK", "PINK")
    ]

    _Traits = [
        [d[0], d[1], d[2], G_ColourTraits.GetColour(d[3]), G_ColourTraits.GetColour(d[4])]
        for d in _Descs
    ]

    StyleTraits = G_StyleTraits(_Traits)


    #-------------------------------------------------------
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.BuildPage()

        # default style - "Note"
        self._StyleCombo.SetSelection(0)

        self._Annotation.Bind(wx.EVT_TEXT, self.OnAnnotationText)
        self._Annotation.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self._Annotation.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)

        self._StyleCombo.Bind(wx.EVT_COMBOBOX, self.OnStyleCombo)
        self._StyleCombo.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self._StyleCombo.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)

        self._ViewNode = None


    #-------------------------------------------------------
    def BuildPage(self):
        # lhs vertical sizer contains label and combo
        style_sizer = wx.BoxSizer(wx.VERTICAL)
        style_label = wx.StaticText(self, label = "Style:")
        style_sizer.Add(style_label, proportion = 0, flag = wx.LEFT | wx.TOP | wx.RIGHT, border = G_Const.Sizer_StdBorder)

        self._StyleCombo = G_StyleCombo(self, self.StyleTraits)
        style_sizer.Add(self._StyleCombo, proportion = 0, flag = wx.LEFT | wx.BOTTOM | wx.RIGHT, border = G_Const.Sizer_StdBorder)

        # rhs vertical sizer contains label and annotation text
        annotation_sizer = wx.BoxSizer(wx.VERTICAL)
        annotation_label = wx.StaticText(self, label = "Annotation:")
        annotation_sizer.Add(annotation_label, proportion = 0, flag = wx.LEFT | wx.TOP | wx.RIGHT, border = G_Const.Sizer_StdBorder)

        self._Annotation = ExpandoTextCtrl(self)
        annotation_sizer.Add(self._Annotation, proportion = 0, flag = wx.EXPAND | wx.LEFT | wx.BOTTOM | wx.RIGHT, border = G_Const.Sizer_StdBorder)

        # horizontal sizer contains the lhs/rhs sizers
        hsizer = self._AnnotationPane = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(style_sizer)
        hsizer.Add(annotation_sizer, proportion = 1)

        # overall sizer contains the horizontal sizer and the STC editor
        vsizer = wx.BoxSizer(wx.VERTICAL)
        vsizer.Add(hsizer, proportion = 0, flag = wx.EXPAND)
        vsizer.Show(hsizer, False, recursive = True)

        self._Editor = G_StcView(self, -1)
        vsizer.Add(self._Editor, proportion = 1, flag = wx.EXPAND)
        
        self.SetSizer(vsizer)


    #-------------------------------------------------------
    def GetEditor(self):
        return self._Editor

    def GetStyle(self):
        return self.StyleTraits.GetData(self._StyleCombo.GetValue())


    #-------------------------------------------------------
    def ShowAnnotationPane(self, show):
        sizer = self.GetSizer()
        sizer.Show(self._AnnotationPane, show, recursive = True)
        sizer.Layout()


    #-------------------------------------------------------
    def Activate(self, view_node):
        editor = self.GetEditor()
        line = editor.LineFromPosition(editor.GetSelectionEnd())

        annotation_text = editor.AnnotationGetText(line)
        self._Annotation.SetValue(annotation_text)

        if annotation_text != "":
            traits = self.StyleTraits
            style_no = editor.AnnotationGetStyle(line)
            self._StyleCombo.SetSelection(traits.GetIndexByData(style_no))

        self.ShowAnnotationPane(True)
        self._Annotation.SetFocus()

        self._ViewNode = view_node


    def DeActivate(self, focus_win = None):
        self._ViewNode = None
        self.ShowAnnotationPane(False)
        if focus_win is not None:
            focus_win.SetFocus()


    #-------------------------------------------------------
    def OnAnnotationText(self, event):
        """The annotation has altered; flush the new text into the editor and refresh all views"""

        view_node = self._ViewNode
        if view_node is not None:
            annotation_text = self._Annotation.GetValue()

            editor = self.GetEditor()
            line = editor.LineFromPosition(editor.GetSelectionEnd())
            editor.AnnotationSetText(line, annotation_text)
            editor.AnnotationSetStyle(line, self.GetStyle())

            view_node.GetLogNode().RefreshViews()

        # expando editor control uses this event to re-size
        event.Skip()


    #-------------------------------------------------------
    def OnKeyDown(self, event):
        """A key has been pressed in the annotation control"""

        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.DeActivate(self._Editor)
        else:
            event.Skip()


    #-------------------------------------------------------
    def OnStyleCombo(self, event):
        """The style has altered; update annotation and refresh all Scintilla controls"""

        view_node = self._ViewNode
        if view_node is not None:
            editor = self.GetEditor()
            line = editor.LineFromPosition(editor.GetSelectionEnd())
            editor.AnnotationSetStyle(line, self.GetStyle())
            view_node.GetLogNode().RefreshViews()


    #-------------------------------------------------------
    def OnKillFocus(self, event):
        next_focus = event.GetWindow()
        if next_focus is not self._StyleCombo and next_focus is not self._Annotation:
            self.DeActivate()

        event.Skip()



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
                with G_FrozenWindow(self.GetFrame()):
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



## G_ViewOptionsNode ########################################

class G_ViewOptionsNode(G_ViewChildNode, G_ThemeNode, G_ColourNode, G_TabContainedNode):
    """Define the view's general display"""

    _Type = [
        ["None", Nlog.EnumMarginType.Empty],
        ["Line Numbers", Nlog.EnumMarginType.LineNumber],
        ["Time Offset", Nlog.EnumMarginType.Offset]
    ]

    _Precision = [
        ["sec.msec.nsec", Nlog.EnumMarginPrecision.MsecDotNsec],
        ["sec.usec", Nlog.EnumMarginPrecision.Usec],
        ["sec.msec", Nlog.EnumMarginPrecision.Msec],
        ["sec", Nlog.EnumMarginPrecision.Sec],
		["min:sec", Nlog.EnumMarginPrecision.MinSec],
		["hour:min:sec", Nlog.EnumMarginPrecision.HourMinSec],
		["day:hour:min:sec", Nlog.EnumMarginPrecision.DayHourMinSec]
    ]


    #-------------------------------------------------------
    def BuildPage(parent):
        # class static function
        me = __class__
        me._Sizer = parent.GetSizer()

        window = parent.GetWindow()

        type = [item[0] for item in me._Type]
        me._MarginTypeCtl = wx.Choice(window)
        me._MarginTypeCtl.Set(type)
        me.BuildLabelledRow(parent, "Margin content", me._MarginTypeCtl)

        precision = [item[0] for item in me._Precision]
        me._MarginPrecisionCtl = wx.Choice(window)
        me._MarginPrecisionCtl.Set(precision)
        me.BuildLabelledRow(parent, "Margin offset precision", me._MarginPrecisionCtl)

        G_ColourNode.BuildColour(me, parent)


    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem, name, **kwargs):
        G_TabContainedNode.__init__(self, factory, wproject, witem)
        G_ThemeNode.__init__(self, G_ThemeNode.DomainView)

    def PostInitNode(self):
        self._Field = D_Document(self.GetDocument(), self)

    def PostInitLoad(self):
        # themes are setup now
        self.UpdateViewMargin()
        self.PostInitColour()


    #-------------------------------------------------------
    def EnablePrecisionCtl(self):
        self._MarginPrecisionCtl.Enable(self.GetMarginType() == Nlog.EnumMarginType.Offset)

    def Activate(self):
        self.ActivateCommon()

        self.Rebind(self._MarginTypeCtl, wx.EVT_CHOICE, self.OnMarginType)
        self._MarginTypeCtl.SetSelection(self._Field.MarginTypeIdx.Value)

        self.Rebind(self._MarginPrecisionCtl, wx.EVT_CHOICE, self.OnMarginPrecision)
        self._MarginPrecisionCtl.SetSelection(self._Field.MarginPrecisionIdx.Value)
        self.EnablePrecisionCtl()

        self.ActivateColour()

#        self.SetNodeHelp("View Tracking", "views.html", "viewtracking")


    #-------------------------------------------------------
    def GetMarginType(self):
        return self._Type[self._Field.MarginTypeIdx.Value][1]

    def GetMarginPrecision(self):
        return self._Precision[self._Field.MarginPrecisionIdx.Value][1]

    def UpdateViewMargin(self):
        self.GetViewNode().UpdateMargin(self.GetMarginType(), self.GetMarginPrecision())


    #-------------------------------------------------------
    def OnMarginType(self, event):
        self._Field.MarginTypeIdx.Value = self._MarginTypeCtl.GetSelection()
        self.EnablePrecisionCtl()
        self.UpdateViewMargin()
        self.SendFocusToDisplayCtrl()

    def OnMarginPrecision(self, event):
        self._Field.MarginPrecisionIdx.Value = self._MarginPrecisionCtl.GetSelection()
        self.UpdateViewMargin()
        self.SendFocusToDisplayCtrl()


    #-------------------------------------------------------
    def OnColour(self, refocus):
        """The margin text colour has altered; refresh the Scintilla control"""
        self.GetViewNode().UpdateMarginTextColour(self.GetColour())
        self.SendFocusToDisplayCtrl(refocus)



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

class G_ViewNode(G_DisplayNode, G_HideableTreeNode, G_TabContainerNode, G_DataExplorerProvider, G_DataExplorerSync):
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
        self.SetupDataExplorer()

        self._CursorLine = -1
        self._AutoHiliteText = ""
        self._OrigNameId = name.split("/")[-1]


    @G_Global.TimeFunction
    def PostInitNode(self):
        # make document fields accessible
        self._Field = D_Document(self.GetDocument(), self)

        # apply any user override to the node's label
        self.SetTreeLabel(self.GetNodeLabel())

        # ensure non-template fields exist and are initialised
        self._Field.Add(0, "FirstVisibleLine", replace_existing = False)
        self._Field.Add(0, "CursorLine", replace_existing = False)

        # make a Scintilla editor and a Nlog logfile view
        aui_notebook = self.GetAuiNotebook()
        view_control = self._ViewControl = G_ViewControl(aui_notebook)
        editor = view_control.GetEditor()
        self.SetDisplayCtrl(editor)
        self.InterceptKeys(editor)
        self.InterceptSetFocus(editor)
        editor.Bind(wx.stc.EVT_STC_UPDATEUI, self.OnUpdateUI)

        self._N_View = self.GetLogfile().CreateLogView()

        # make a Scintilla document to display the view, and
        # add it to the Scintilla editor
        self._S_Document = editor.CreateDocument(self._N_View.GetContent())
        editor.SetDocPointer(self._S_Document)

        # setup default text style
        face = "Segoe UI"
        editor.StyleSetSpec(wx.stc.STC_STYLE_DEFAULT, "face:{face},size:9".format(face = face))
        editor.StyleClearAll()

        # setup default style for margin text
        editor.StyleSetSpec(wx.stc.STC_STYLE_LINENUMBER, "face:{face},size:8".format(face = face))
        editor.StyleSetBackground(wx.stc.STC_STYLE_LINENUMBER, wx.Colour(0xe8e8e8))

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
        editor.SetMarginType(0, wx.stc.STC_MARGIN_RTEXT)

        marker_mask = (2 ** Nlog.EnumMarker.TrackerBase) - 1
        editor.SetMarginBackground(1, wx.Colour(0xf0f0f0))
        editor.SetMarginType(1, wx.stc.STC_MARGIN_COLOUR)
        editor.SetMarginWidth(1, 14)
        editor.SetMarginMask(1, marker_mask)

        # can't figure out how to set background colour for second symbol margin
        tracker_mask = 0xffffffff & ~marker_mask
        editor.SetMarginType(2, wx.stc.STC_MARGIN_SYMBOL)
        editor.SetMarginWidth(2, 14)
        editor.SetMarginMask(2, tracker_mask)

        # history line marker
        from .StyleNode import G_ColourTraits
        history_marker = Nlog.EnumMarker.History
        editor.MarkerDefine(history_marker, wx.stc.STC_MARK_BACKGROUND)
        editor.MarkerSetBackground(history_marker, G_ColourTraits.GetColour("MEDIUM SLATE BLUE"))
        editor.MarkerSetAlpha(history_marker, 50)

        # setup cursor unwanted zone (UZ); keeps GotoLine away from the top/bottom
        # of the screen
        editor.SetYCaretPolicy(wx.stc.STC_CARET_SLOP | wx.stc.STC_CARET_EVEN, 10)

        # setup caret line hiliting
        editor.SetCaretLineBackground(G_ColourTraits.GetColour("GOLDENROD"))
        editor.SetCaretLineBackAlpha(50)
        editor.SetCaretLineVisible(True)

        # setup annotation styles
        editor.AnnotationSetVisible(wx.stc.STC_ANNOTATION_BOXED)
        anno_traits = G_ViewControl.StyleTraits
        for anno_idx in range(anno_traits.GetNumStyles()):
            style_no = anno_traits.GetDataByIndex(anno_idx)
            editor.StyleSetItalic(style_no, True)
            editor.StyleSetForeground(style_no, anno_traits.GetForegroundColourByIndex(anno_idx))
            editor.StyleSetBackground(style_no, anno_traits.GetBackgroundColourByIndex(anno_idx))

        # editor must be set to read-only; switches off behaviour that Nlog
        # does not implement
        editor.SetReadOnly( True );

        # and add the Scintilla editor to the AUI notebook, without altering focus
        def Work():
            aui_notebook.AddPage(view_control, self.GetNodeLabel(), True)
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
    def ShowLocation(self, location):
        line = int(location)
        self.GetView().SetHistoryLine(line)
        self.ScrollToLine(line)
        self.RefreshView()
        return True


    def CreateDataExplorerPage(self, builder, location, page):
        builder.AddPageHeading("View")
        builder.AddLink(self.GetLogNode().MakeDataUrl(), "Show log ...")

        line = int(location)
        view = self.GetView()

        builder.AddField("Line No", location)

        for field_id, name in enumerate(self.GetLogNode().GetLogSchema().GetFieldNames()):
            builder.AddField(name, view.GetFieldText(line, field_id))

        builder.AddField("Line", view.GetNonFieldText(line))


    #-------------------------------------------------------
    def GetEditor(self):
        return self._ViewControl.GetEditor()

    def GetSelectedText(self):
        """Fetch the selected text in the editor"""
        return self.GetEditor().GetSelectedText()

    def GetView(self):
        return self._N_View

    def GetDefaultNodeLabel(self):
        return "{}/{}".format(self.GetLogNode().GetNodeLabel(), self._OrigNameId)


    #-------------------------------------------------------
    def GetTrackInfo(self):
        return self.FindChildNode(factory_id = G_Project.NodeID_ViewTracking).GetTrackInfo()

    def GetNearestUtcTimecode(self, line_no):
        return self._N_View.GetNearestUtcTimecode(line_no)


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
            timecode = self.GetNearestUtcTimecode(cur_line)
            self.UpdateTrackers(update_local, update_global_idx, [timecode])

            # flush any changes through to the GUI
            self.RefreshTrackers(update_local, update_global, self)

        # tell the data explorer
        self.GetDataExplorer().Update(self.MakeDataUrl(str(cur_line)))

        # tell the world
        self.NotifyLine(cur_line)

        # maintanance note - do not add any more random stuff to this function,
        # implement a proper notification system


    #-------------------------------------------------------
    def OnDisplayKey(self, key_code, modifiers, view_node):
        handled = False

        editor = self.GetEditor()
        cur_line = editor.LineFromPosition(editor.GetSelectionStart())
        if key_code == ord("A"):
            handled = True
            if modifiers ==  wx.MOD_CONTROL:
                self._ViewControl.Activate(self)
            else:
                view_node.GotoNextLine("annotation", modifiers = modifiers)

        elif key_code == ord("B"):
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
                timecode = self.GetNearestUtcTimecode(cur_line)
                self.UpdateTrackers(True, -1, [timecode])

        elif key_code in self._GlobalTrackerKeys:
            tracker_idx = self._GlobalTrackerKeys[key_code]
            if modifiers == 0:
                handled = True
                self.ScrollToLine(self._N_View.GetGlobalTrackerLine(tracker_idx))
            elif modifiers == wx.MOD_CONTROL:
                handled = True
                timecode = self.GetNearestUtcTimecode(cur_line)
                Nlog.SetGlobalTracker(tracker_idx, timecode)
                self.RefreshTrackers(False, True, self)
                self.UpdateTrackers(False, tracker_idx, [timecode])

        return handled


    #-------------------------------------------------------
    def ScrollToLine(self, line):
        editor = self.GetEditor()
        start = editor.PositionFromLine(line)
        end = editor.PositionFromLine(line + 1)
        editor.ScrollRange(start, end)


    #-------------------------------------------------------
    @G_Global.TimeFunction
    def SetFieldMask(self, field_mask):
        """Set the list of visible fields for this view"""

        # the update abuses Scintilla's internal notification system, so
        # manually preserve the screen state
        state = self.GetScreenState()
        self._N_View.SetFieldMask(field_mask)
        self.SetScreenState(state)
        self.GetEditor().Refresh()

    def UpdateFieldColour(self, field_id, colour):
        style_no = field_id + Nlog.EnumStyle.FieldBase
        self.GetEditor().StyleSetForeground(style_no, colour)


    #-------------------------------------------------------
    def RefreshView(self):
        self.GetEditor().Refresh()


    #-------------------------------------------------------
    def UpdateHiliterMatch(self, index, match):
        """A hiliter GUI page match field has been edited; update editor"""

        try:
            self._N_View.GetHiliter(index).SetMatch(match)
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
        ok = self._N_View.Filter(match)
        if ok:
            self.SetDataExplorerValidity("Filter: {match}".format(match = match.GetDescription()))
        return ok
            

    #-------------------------------------------------------
    def UpdateMargin(self, type, precision):
        editor = self.GetEditor()
        width = 0
        
        if type == Nlog.EnumMarginType.LineNumber:
            digits = 1 + int(log10(editor.GetNumberOfLines()))
            width = editor.TextWidth(wx.stc.STC_STYLE_LINENUMBER, "_" + "9" * digits)

        elif type == Nlog.EnumMarginType.Offset:
            begin_timecode = self.GetNearestUtcTimecode(0)
            end_timecode = self.GetNearestUtcTimecode(editor.GetNumberOfLines() - 1)
            duration = end_timecode.Subtract(begin_timecode) / 1000000000

            if precision == Nlog.EnumMarginPrecision.MinSec:
                duration /= 60
            elif precision == Nlog.EnumMarginPrecision.HourMinSec:
                duration /= (60 * 60)
            elif precision == Nlog.EnumMarginPrecision.DayHourMinSec:
                duration /= (24 * 60 * 60)

            digits = 1 + int(log10(duration))

            if precision == Nlog.EnumMarginPrecision.MsecDotNsec:
                digits += 10
            elif precision == Nlog.EnumMarginPrecision.Usec:
                digits += 6
            elif precision == Nlog.EnumMarginPrecision.Msec:
                digits += 3
            elif precision == Nlog.EnumMarginPrecision.MinSec:
                digits += 3
            elif precision == Nlog.EnumMarginPrecision.HourMinSec:
                digits += 6
            elif precision == Nlog.EnumMarginPrecision.DayHourMinSec:
                digits += 9

            width = editor.TextWidth(wx.stc.STC_STYLE_LINENUMBER, "__" + "9" * digits)

        if type != Nlog.EnumMarginType.Empty:
            self._N_View.SetupMarginText(type, precision)

        editor.SetMarginWidth(0, width)
        self.RefreshView()


    #-------------------------------------------------------
    def UpdateMarginTextColour(self, colour):
        self.GetEditor().StyleSetForeground(wx.stc.STC_STYLE_LINENUMBER, colour)
        self.RefreshView()



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
    G_NodeFactory(G_Project.NodeID_ViewOptions, G_Project.ArtCtrlId_Options, G_ViewOptionsNode)
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
