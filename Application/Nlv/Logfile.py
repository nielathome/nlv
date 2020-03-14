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
import datetime
from pathlib import Path
from weakref import ref as MakeWeakRef

# wxWidgets imports
import wx

# Application imports
from .DataExplorer import G_DataExplorerProvider
from .DataExplorer import G_DataExplorerSync
from .Document import D_Document
from .Global import G_Const
from .Global import G_Global
from .Logmeta import GetLogSchema
from .MatchNode import G_MatchItem
from .MatchNode import G_MatchNode
from .Project import G_TabContainerNode
from .Project import G_TabContainedNode
from .Project import G_ListContainedNode
from .Project import G_ListContainerNode
from .Project import G_HideableTreeNode
from .Project import G_NodeFactory
from .Project import G_Project
from .Session import G_SessionChildNode
from .StyleNode import G_ColourNode
from .StyleNode import G_MarkerStyleNode
from .StyleNode import G_TrackerStyleNode
from .Theme import G_ThemeNode
from .Theme import G_ThemeOverridesNode
from .Theme import G_ThemeGalleryNode
from .Theme import GetThemeGallery

# Content provider interface
import Nlog


## G_LogChildNode ##########################################

class G_LogChildNode(G_SessionChildNode):
    """Mixin class to extend child nodes of a logfile node with common behaviour"""

    #-------------------------------------------------------
    def GetLogNode(self):
        # recursive lookup
        return self.GetParentNode(G_Project.NodeID_Log)


    #-------------------------------------------------------
    def GetLogfile(self):
        """Fetch the Nlog logfile object associated with the logfile node"""
        return self.GetLogNode().GetLogfile()


    #-------------------------------------------------------
    def GetLogNodeChildNode(self, factory_id):
        return self.GetLogNode().FindChildNode(factory_id = factory_id, recursive = True)


    #-------------------------------------------------------
    def GetDisplayNode(self):
        # non-display child nodes of a LogfileNode still need to respond
        # to a GetDisplayNode request
        return None



## G_DelayedSendFocus ######################################

class G_DelayedSendFocus:

    #-------------------------------------------------------
    def __init__(self):
        self._DelayedFocusWindow = None


    #-------------------------------------------------------
    def SendFocusToCtrl(self, ctrl):
        """Delayed forwarding of input focus; safe to use in any event context"""

        # in practice, we do see recursion (even though that
        # makes little sense), so defend against that
        if self._DelayedFocusWindow is None:
            self._DelayedFocusWindow = ctrl
            self._DelayedFocusWindow.Bind(wx.EVT_IDLE, self.OnSendFocusToWindow)


    #-------------------------------------------------------
    def OnSendFocusToWindow(self, event):
        if self._DelayedFocusWindow is not None:
            # one shot delayed event, so disconnect now
            ctrl = self._DelayedFocusWindow
            self._DelayedFocusWindow = None
            ctrl.Unbind(wx.EVT_IDLE)

            # move the focus
            ctrl.SetFocus()

        # don't interfere with any use the editor has for idle events
        event.Skip()



## G_DisplayControl ########################################

class G_DisplayControl:
    """
    Base class for controls conveying content to the user.
    Will be a direct or indirect child of the main AUI tab.
    Works in conjunction with a node ownder - G_DisplayNode
    """

    #-------------------------------------------------------
    def GetAuiTabInfo(self, child):
        """
        Fetch the AUI tab index of the window containing
        this child.
        """
        return self.GetParent().GetAuiTabInfo(self)


    #-------------------------------------------------------
    def DestroyDisplayCtrl(self):
        # delete the AUI notebook tab (and this child window)
        aui_notebook, child_idx = self.GetAuiTabInfo(self)
        aui_notebook.DeletePage(child_idx)


    #-------------------------------------------------------
    def ShowDisplayCtrl(self, show):
        aui_notebook, child_idx = self.GetAuiTabInfo(self)
        aui_notebook.HidePage(child_idx, not show)


    #-------------------------------------------------------
    def SwitchToDisplayCtrl(self):
        self.GetParent().SwitchToDisplayChildCtrl(self)

    def SwitchToDisplayChildCtrl(self, child):
        self.GetParent().SwitchToDisplayChildCtrl(self)

    

## G_PanelDisplayControl ###################################

class G_PanelDisplayControl(wx.Panel, G_DisplayControl):

    #-------------------------------------------------------
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)



## G_NotebookDisplayControl ################################

class G_NotebookDisplayControl(wx.Notebook, G_DisplayControl, G_DelayedSendFocus):

    #-------------------------------------------------------
    def __init__(self, parent):
        wx.Notebook.__init__(self, parent, style = wx.NB_TOP)
        G_DelayedSendFocus.__init__(self)
        self.Bind(wx.EVT_SET_FOCUS, self.OnSetFocus)


    #-------------------------------------------------------
    def SwitchToDisplayChildCtrl(self, child):
        # if needed, switch this tab first
        idx = self.FindPage(child)
        cur = self.GetSelection()
        if idx != wx.NOT_FOUND and idx != cur:
            self.SetSelection(idx)

        # note: pass this window upwards, not the child
        self.GetParent().SwitchToDisplayChildCtrl(self)


    #-------------------------------------------------------
    def OnSetFocus(self, evt):
        """
        It seems tab control's don't forward input focus, so
        we do that manually.
        """
        page = self.GetCurrentPage()
        if page is not None:
            self.SendFocusToCtrl(page)



## G_DisplayNode ###########################################

class G_DisplayNode(G_LogChildNode, G_DelayedSendFocus):
    """
    Base class for nodes associated with a display in the
    tabbed pane area, displaying 'content' to the user
    """

    #-------------------------------------------------------
    def __init__(self):
        G_DelayedSendFocus.__init__(self)

        # the window contained in the AUI tab
        self._DisplayCtrl = None
        self._OwnsDisplayCtrl = False

        # either the same as _DisplayCtrl, or a child of it -
        # the window given input focus when this node is activated
        self._DisplayFocusCtrl = None

        # support bi-directional sync of tree node and notebook page
        # weak reference to the last known selected child node
        self.SetLastChild(self)

        # control UI updates in response to focus or selection events; will be inhibited during:
        #  processing notebook tab changes or editor focus changes
        #  processing tree view selection change events
        self._CanManageFocus = True


    #-------------------------------------------------------
    def GetDisplayNode(self):
        return self

    def GetNodeLabel(self):
        self._Field.Add("", "NodeUserLabel", replace_existing = False)
        label = self._Field.NodeUserLabel.Value
        if label != "":
            return label
        else:
            return self.GetDefaultNodeLabel()


    #-------------------------------------------------------
    def EnsureDisplayControlVisible(self):
        # don't switch aui tab if this node is hidden; it causes
        # the node to re-appear
        if self.IsNodeDisplayed():
            self._DisplayCtrl.SwitchToDisplayCtrl()

    def WithFocusLock(self, func):
        """Execute 'func' while holding the focus recursion-lock"""
        if self._CanManageFocus:
            self._CanManageFocus = False
            func()
            self._CanManageFocus = True


    def ChildActivating(self, child, focus_window = None):
        """A child node is activating; update the AuiNotebook accordingly"""

        def Work():
            # ensure containing notebook(s) set correctly
            self.EnsureDisplayControlVisible()

            # forward focus; unless otherwise specified, forward to the display control
            nonlocal child, focus_window
            if focus_window is None:
                focus_window = self._DisplayFocusCtrl
            self.SendFocusToWindow(focus_window)

            # and make a note of which child was activated
            self.SetLastChild(child)


        # skip if activation is a side effect of a display control getting
        # input focus, or if it is hidden
        if self.IsNodeDisplayed():
            self.WithFocusLock(Work)


    def OnDisplayCtrlSetFocus(self, event):
        """A display control associated with this node has received input focus"""

        def Work():
            # ensure containing notebook(s) set correctly
            self.EnsureDisplayControlVisible()

            # switch node in the tree view
            node = self._WLastChild()
            if node:
                node.MakeActive()

            # allow the node to take any required action
            self.OnDisplayFocus()

        # skip if focus is a side effect of a tree node being selected, or a recursive call
        self.WithFocusLock(Work)

        # always pass the event onwards
        event.Skip()


    def OnDisplayFocus(self):
        """Handle focus events sent to the display control"""
        pass


    #-------------------------------------------------------
    def DoClose(self, delete):
        """Remove display control from the UI"""

        if self._OwnsDisplayCtrl and self._DisplayCtrl is not None:
            self._DisplayCtrl.DestroyDisplayCtrl()

        super().DoClose(delete)


    #-------------------------------------------------------
    def OnDisplayKeyDown(self, event):
        """Intercept key presses sent to a display control"""

        # standard routing via child node
        handled = False
        key_code = event.GetKeyCode()
        modifiers = event.GetModifiers()
        for node in self.ListSubNodes(recursive = True, include_self = True):
            handled = node.OnDisplayKey(key_code, modifiers, self)
            if handled:
                break;

        # otherwise, pass to the underlying control
        if not handled:
            event.Skip()

    def OnDisplayKey(self, key_code, modifiers, view_node):
        """Intercept key presses sent to the display control"""
        return False

    def InterceptKeys(self, ctrl):
        ctrl.Bind(wx.EVT_KEY_DOWN, self.OnDisplayKeyDown)


    #-------------------------------------------------------
    def OnBeginLabelEdit(self):
        return True

    def OnEndLabelEdit(self, label):
        # an empty label seems to mean "no change"
        if label != "":
            aui_notebook, child_idx = self._DisplayCtrl.GetAuiTabInfo(self._DisplayCtrl)
            aui_notebook.SetPageText(child_idx, label)
            self._Field.NodeUserLabel.Value = label

        return True


    #-------------------------------------------------------
    def SendFocusToWindow(self, focus_window):
        """Delayed forwarding of input focus; safe to use in any event context"""
        if self.IsNodeDisplayed():
            self.SendFocusToCtrl(focus_window)

    def SendFocusToDisplayCtrl(self):
        self.SendFocusToWindow(self._DisplayFocusCtrl)


    #-------------------------------------------------------
    def SetDisplayFocusCtrl(self, display_focus_ctrl):
        self._DisplayFocusCtrl = display_focus_ctrl

    def SetDisplayCtrl(self, display_ctrl, display_focus_ctrl = None, owns_display_ctrl = True):
        self._DisplayFocusCtrl = self._DisplayCtrl = display_ctrl
        self._OwnsDisplayCtrl = owns_display_ctrl

        if display_focus_ctrl is not None:
            self._DisplayFocusCtrl = display_focus_ctrl

        return display_ctrl

    def InterceptSetFocus(self, ctrl):
        ctrl.Bind(wx.EVT_SET_FOCUS, self.OnDisplayCtrlSetFocus)


    #-------------------------------------------------------
    def SetLastChild(self, child):
        # strictly, 'child' can be any node in the project tree
        self._WLastChild = MakeWeakRef(child)


    #-------------------------------------------------------
    def UpdateNodeDisplay(self):
        self._DisplayCtrl.ShowDisplayCtrl(self.IsNodeDisplayed())


    #-------------------------------------------------------
    def UpdateTrackers(self, update_local, update_global_idx, timecodes):
        master_tracker_node = self.GetSessionNode().FindChildNode(factory_id = G_Project.NodeID_SessionTrackerOptions)
        master_tracker_node.UpdateTrackers(update_local, update_global_idx, timecodes)


    #-------------------------------------------------------
    def RefreshTrackers(self, update_local, update_global, originator):
        """Update all trackers in the session"""

        # ensure local editor is refreshed
        assert(update_local or update_global)
        if originator is not None:
            originator.RefreshView()

        # flush new tracker positions through to all other views
        lognode = self.GetLogNode()
        for view in self.GetSessionNode().ListSubNodes(factory_id = G_Project.NodeID_View, recursive = True):
            if view is not originator:
                view.RefreshTracker(lognode, update_local, update_global)


    def RefreshTracker(self, lognode, update_local, update_global):
        """Update this view's trackers"""

        tracker_line = -1
        info = self.GetTrackInfo()

        if update_local and info.SyncLocal() and lognode is self.GetLogNode():
            tracker_line = self._N_View.GetLocalTrackerLine()

        elif update_global and info.SyncGlobalIdx() >= 0:
            tracker_line = self._N_View.GetGlobalTrackerLine(info.SyncGlobalIdx())

        if tracker_line >= 0:
            self.ScrollToLine(tracker_line)

        self.RefreshView()
        


## G_DisplayChildNode ######################################

class G_DisplayChildNode(G_LogChildNode):
    """Base class for child nodes of G_DisplayNode"""

    #-------------------------------------------------------
    def GetDisplayNode(self):
        # recursive lookup; requires the display node to respond
        return self.GetParentNode().GetDisplayNode()


    #-------------------------------------------------------
    def ActivateCommon(self, focus_window = None):
        """Common activation behaviour for children of a view node"""

        # get the view to switch the editor window
        self.GetDisplayNode().ChildActivating(self, focus_window)


    #-------------------------------------------------------
    def OnDisplayKey(self, key_code, modifiers, view_node):
        """Intercept key presses sent to the display control"""
        return False


    #-------------------------------------------------------
    def SendFocusToDisplayCtrl(self, refocus = True):
        if refocus:
            self.GetDisplayNode().SendFocusToDisplayCtrl()



## G_OpenViewNode ##########################################

class G_OpenViewNode(G_LogChildNode, G_TabContainedNode):

    #-------------------------------------------------------
    def BuildPage(parent):
        # class static function
        me = __class__
        me._Sizer = parent.GetSizer()

        window = parent.GetWindow()
        me.BuildSubtitle(parent, "Available views:")
        me._ViewThemeList = wx.ListCtrl(window, size = (-1, G_Const.ListBoxH), style = wx.LC_LIST)
        parent.GetSizer().Add(me._ViewThemeList, proportion = 1, flag = wx.ALL | wx.EXPAND, border = G_Const.Sizer_StdBorder, userData = "OpenViewNode-view-theme-list")

        me._BtnNewView = wx.Button(window, label = "New View(s)", size = G_Const.ButtonSize)
        me.BuildLabelledRow(parent, "Create new view(s):", me._BtnNewView)

        me.BuildSubtitle(parent, "Available event analysers:")
        me._EventThemeList = wx.ListCtrl(window, size = (-1, G_Const.ListBoxH), style = wx.LC_LIST)
        parent.GetSizer().Add(me._EventThemeList, proportion = 2, flag = wx.ALL | wx.EXPAND, border = G_Const.Sizer_StdBorder, userData = "OpenViewNode-event-theme-list")

        me._BtnNewEvent = wx.Button(window, label = "New Event(s)", size = G_Const.ButtonSize)
        me.BuildLabelledRow(parent, "Create new events views(s):", me._BtnNewEvent)


    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem, name, **kwargs):
        G_TabContainedNode.__init__(self, factory, wproject, witem)
        self._ViewIds = []
        self._EventIds = []


    #-------------------------------------------------------
    def ActivateList(self, theme_list, theme_cls, button, sel_callback, cmd_callback):
        theme_list.DeleteAllItems()
        self.Rebind(theme_list, wx.EVT_LIST_ITEM_SELECTED, sel_callback)
        self.Rebind(theme_list, wx.EVT_LIST_ITEM_DESELECTED, sel_callback)
        self.Rebind(theme_list, wx.EVT_LIST_ITEM_ACTIVATED, cmd_callback)
        self.Rebind(button, wx.EVT_BUTTON, cmd_callback)
        button.Enable(False)

        theme_ids = []
        for (idx, theme) in enumerate(GetThemeGallery(theme_cls).GetThemeNames()):
            (name, theme_id) = theme
            theme_list.InsertItem(idx, name)
            theme_ids.append(theme_id)

        return theme_ids


    def Activate(self):
        self.SetNodeHelp("New View", "logfile.html", "openview")
        self._ViewIds = self.ActivateList(self._ViewThemeList, "view", self._BtnNewView, self.OnListView, self.OnCmdNewView)
        self._EventIds = self.ActivateList(self._EventThemeList, "event", self._BtnNewEvent, self.OnListEvent, self.OnCmdNewEvent)


    #-------------------------------------------------------
    @staticmethod
    def GetSelectedItems(list):
        items = []
        num_items = list.GetSelectedItemCount()

        if num_items != 0:
            item = list.GetFirstSelected()
            items.append(item)
            for i in range(num_items - 1):
                item = list.GetNextSelected(item)
                items.append(item)

        return items

        
    def OnListView(self, event):
        have_selection = self._ViewThemeList.GetSelectedItemCount() != 0
        self._BtnNewView.Enable(have_selection)

        
    @G_Global.TimeFunction
    def OnCmdNewView(self, event):
        for item in self.GetSelectedItems(self._ViewThemeList):
            self.GetLogNode().OnNewView(self._ViewIds[item])


    #-------------------------------------------------------
    def OnListEvent(self, event):
        have_selection = self._EventThemeList.GetSelectedItemCount() != 0
        self._BtnNewEvent.Enable(have_selection)

    @G_Global.TimeFunction
    def OnCmdNewEvent(self, event):
        for item in self.GetSelectedItems(self._EventThemeList):
            self.GetLogNode().OnNewEvents(self._EventIds[item], True)



## G_MarkerFormatNode ######################################

class G_MarkerFormatNode:
    """Manage common style/colour aspects of marker/tracker formatting"""

    #-------------------------------------------------------
    def __init__(self, index_offset):
        self._IndexOffset = index_offset


    #-------------------------------------------------------
    def PostInitFormat(self):
        self._Field = D_Document(self.GetDocument(), self)
        self.PostInitColour()
        self.PostInitStyle()


    #-------------------------------------------------------
    def ActivateFormat(self):
        self.ActivateColour()
        self.ActivateStyle()


    #-------------------------------------------------------
    def ApplyToEditors(self, editors):
        """Apply this marker to the supplied Scintilla editors"""
        index = self._IndexOffset + self.GetIndex()
        for editor in editors:
            editor.MarkerDefine(index, self.GetStyle())
            editor.MarkerSetBackground(index, self.GetColour())


    #-------------------------------------------------------
    def OnColour(self, refocus):
        """The colour has altered; refresh the associated editors"""
        self.GetLogNode().UpdateMarkerColour(self)


    #-------------------------------------------------------
    def OnStyle(self, refocus):
        """The style has altered; refresh the the associated editors"""
        self.GetLogNode().UpdateMarkerStyle(self)


    #-------------------------------------------------------
    def OnThemeChange(self, theme_cls, theme_id):
        """The colour and/or style has altered; refresh the the associated editors"""
        if theme_cls == G_Const.GlobalThemeCls:
            self.GetLogNode().UpdateMarker(self)



## G_MarkerNode ############################################

class G_MarkerNode(G_LogChildNode, G_ThemeNode, G_MatchNode, G_MarkerFormatNode, G_ColourNode, G_MarkerStyleNode, G_ListContainedNode):
    """A marker control"""

    #-------------------------------------------------------
    def BuildPage(parent):
        # class static function
        me = __class__
        me._Sizer = parent.GetSizer()

        # add child controls
        G_MatchNode.BuildMatch(me, parent, "Match", filter = True)
        G_ColourNode.BuildColour(me, parent)
        G_MarkerStyleNode.BuildStyle(me, parent)


    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem, name, **kwargs):
        G_ListContainedNode.__init__(self, factory, wproject, witem)
        G_MatchNode.__init__(self, G_Const.LogThemeCls, "Marker")
        G_MarkerFormatNode.__init__(self, Nlog.EnumMarker.StandardBase)
        G_MarkerStyleNode.__init__(self)
        G_ThemeNode.__init__(self, G_ThemeNode.DomainLogfile)


    #-------------------------------------------------------
    def PostInitMarker(self):
        self.PostInitFormat()

    def PostInitLoad(self):
        # need the whole tree available for themes to work
        self.PostInitMatch()


    #-------------------------------------------------------
    def Activate(self):
        self.ActivateMatch()
        self.ActivateFormat()


    #-------------------------------------------------------
    def OnMatch(self, match_item, refocus = None):
        """The match text has altered; refresh the logfile"""
        return self.GetLogNode().UpdateMarkerMatch(self.GetIndex(), match_item)


    #-------------------------------------------------------
    def OnThemeChange(self, theme_cls, theme_id):
        """The match has altered; refresh match controls and the associated editors"""
        G_MatchNode.OnThemeChange(self, theme_cls, theme_id)
        G_MarkerFormatNode.OnThemeChange(self, theme_cls, theme_id)



## G_MarkerContainerNode ###################################

class G_MarkerContainerNode(G_LogChildNode, G_ListContainerNode):
    """Container node for hosting markers"""

    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem, name, **kwargs):
        super().__init__(factory, wproject, witem)

    def PostInitChildren(self):
        # have to find out how many children in order to initialise logfile ...
        # the count is for *auto* markers, which given one marker is a *user*
        # marker, is one less than the number of children
        self.GetLogfile().SetNumAutoMarker(self.GetHrItem().GetChildrenCount()-1)

        # ... hence in turn, initialise the markers
        for marker in self.ListSubNodes(factory_id = G_Project.NodeID_Marker):
            marker.PostInitMarker()


    #-------------------------------------------------------
    def Activate(self):
        G_ListContainerNode.ActivateContainer(self)
        self.SetNodeHelp("Markers", "logfile.html", "markers")


    #-------------------------------------------------------
    def GetMarkerNames(self):
        return [nd.GetNodeName() for nd in self.ListSubNodes()]



## G_TrackerNode ###########################################

class G_TrackerNode(G_LogChildNode, G_ThemeNode, G_MarkerFormatNode, G_ColourNode, G_TrackerStyleNode, G_ListContainedNode):
    """A tracker control"""

    #-------------------------------------------------------
    def BuildPage(parent):
        # class static function
        me = __class__
        me._Sizer = parent.GetSizer()

        # add child controls
        me.BuildSubtitle(parent, "Tracker properties:")
        G_ColourNode.BuildColour(me, parent)
        G_TrackerStyleNode.BuildStyle(me, parent)


    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem, name, **kwargs):
        G_ListContainedNode.__init__(self, factory, wproject, witem)
        G_MarkerFormatNode.__init__(self, Nlog.EnumMarker.TrackerBase)
        G_TrackerStyleNode.__init__(self)
        G_ThemeNode.__init__(self, G_ThemeNode.DomainLogfile)


    #-------------------------------------------------------
    def PostInitNode(self):
        """Second initialisation; the tree is now initialised"""
        self.PostInitFormat()


    #-------------------------------------------------------
    def Activate(self):
        self.ActivateFormat()



## G_TrackerContainerNode ##################################

class G_TrackerContainerNode(G_LogChildNode, G_ListContainerNode):
    """Container node for hosting trackers"""

    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem, name, **kwargs):
        super().__init__(factory, wproject, witem)


    #-------------------------------------------------------
    def Activate(self):
        G_ListContainerNode.ActivateContainer(self)
        self.SetNodeHelp("Trackers", "logfile.html", "trackers")



## G_LogInfoNode ##########################################

class G_LogInfoNode(G_LogChildNode, G_TabContainedNode):
    """Information about a logfile; currently, its effective timezone"""

    # taken from https://en.wikipedia.org/wiki/Time_zone
    _Timezones = [
        ("UTC−12:00", -12    ),
        ("UTC−11:00", -11    ),
        ("UTC−10:00", -10    ),
        ("UTC−09:30", -9.5   ),
        ("UTC−09:00", -9     ),
        ("UTC−08:00", -8     ),
        ("UTC−07:00", -7     ),
        ("UTC−06:00", -6     ),
        ("UTC−05:00", -5     ),
        ("UTC−04:00", -4     ),
        ("UTC−03:30", -3.5   ),
        ("UTC−03:00", -3     ),
        ("UTC−02:00", -2     ),
        ("UTC−01:00", -1     ),
        ("UTC±00:00",  0     ),
        ("UTC+01:00",  1     ),
        ("UTC+02:00",  2     ),
        ("UTC+03:00",  3     ),
        ("UTC+03:30",  3.5   ),
        ("UTC+04:00",  4     ),
        ("UTC+04:30",  4.5   ),
        ("UTC+05:00",  5     ),
        ("UTC+05:30",  5.5   ),
        ("UTC+05:45",  5.75  ),
        ("UTC+06:00",  6     ),
        ("UTC+06:30",  6.5   ),
        ("UTC+07:00",  7     ),
        ("UTC+08:00",  8     ),
        ("UTC+08:30",  8.5   ),
        ("UTC+08:45",  8.75  ),
        ("UTC+09:00",  9     ),
        ("UTC+09:30",  9.5   ),
        ("UTC+10:00",  10    ),
        ("UTC+10:30",  10.5  ),
        ("UTC+11:00",  11    ),
        ("UTC+12:00",  12    ),
        ("UTC+12:45",  12.75 ),
        ("UTC+13:00",  13    ),
        ("UTC+14:00",  14    )
    ]

    #-------------------------------------------------------
    def BuildPage(parent):
        # class static function
        me = __class__
        me._Sizer = parent.GetSizer()

        # combo: effective timezone
        tz_names = [tz[0] for tz in __class__._Timezones]
        me._TimezoneCtl = wx.Choice(parent.GetWindow(), choices = tz_names)
        me.BuildLabelledRow(parent, "Interpret log file times as", me._TimezoneCtl)


    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem, name, **kwargs):
        G_TabContainedNode.__init__(self, factory, wproject, witem)

    def PostInitNode(self):
        self._Field = D_Document(self.GetDocument(), self)

        # ensure timezone info exists
        self._Field.Add(14, "LogTimezoneIdx", replace_existing = False)

        # ensure log file timezone is set
        self.SetTimezone()


    #-------------------------------------------------------
    def Activate(self):
        self.Rebind(self._TimezoneCtl, wx.EVT_CHOICE, self.OnUpdateTimezone)
        self._TimezoneCtl.SetSelection(self._Field.LogTimezoneIdx.Value)
        self.SetNodeHelp("TimeZone Info", "logfile.html", "timezone")


    #-------------------------------------------------------
    def OnUpdateTimezone(self, event):
        # persist new timezone offset to document
        idx = self._Field.LogTimezoneIdx.Value = self._TimezoneCtl.GetSelection()

        # tell Nlog
        self.SetTimezone(idx)

        # update screen
        self.GetLogNode().RefreshViews()

    def SetTimezone(self, idx = None):
        """Write the logfile's timezone offset to Nlog"""
        if idx is None:
            idx = self._Field.LogTimezoneIdx.Value
        tz_offset = 3600 * self._Timezones[idx][1]
        self.GetLogfile().SetTimezoneOffset(tz_offset)



## G_LogGlobalThemeOverridesNode ##########################

class G_LogGlobalThemeOverridesNode(G_LogChildNode, G_ThemeOverridesNode, G_ListContainedNode):
    """Logfile global theme overrides saving/restoring"""

    #-------------------------------------------------------
    def BuildPage(parent):
        # class static function
        me = __class__
        me._Sizer = parent.GetSizer()

        G_ThemeOverridesNode.BuildControl(me, parent)


    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem, name, **kwargs):
        G_ListContainedNode.__init__(self, factory, wproject, witem)
        G_ThemeOverridesNode.__init__(self, G_Const.GlobalThemeCls, G_ThemeNode.DomainLogfile)


    #-------------------------------------------------------
    def Activate(self):
        self.SetNodeHelp("Navigation Themes", "logfile.html", "lognavigation")
        self.ActivateControl()



## G_LogLocalThemeGalleryNode ##############################

class G_LogLocalThemeGalleryNode(G_LogChildNode, G_ThemeGalleryNode, G_ListContainedNode):
    """Logfile theme gallery"""

    #-------------------------------------------------------
    def BuildPage(parent):
        # class static function
        me = __class__
        me._Sizer = parent.GetSizer()

        G_ThemeGalleryNode.BuildGallery(me, parent, "log")


    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem, name, **kwargs):
        G_ListContainedNode.__init__(self, factory, wproject, witem)
        G_ThemeGalleryNode.__init__(self, G_Const.LogThemeCls)

        self._InitBuilderGuid = None 
        if "builder_guid" in kwargs:
            self._InitBuilderGuid = kwargs["builder_guid"]

    def PostInitNode(self):
        # make document fields accessible
        self._Field = D_Document(self.GetDocument(), self)

        theme_id = None
        if self._InitBuilderGuid is not None:
            builder = self.GetLogNode().GetLogSchema().GetBuilders().GetObjectByGuid(self._InitBuilderGuid)
            theme_id = builder.GetLogTheme()

        self.PostInitThemeGallery(theme_id)


    #-------------------------------------------------------
    def Activate(self):
        self.SetNodeHelp("Logfile Pattern Themes", "logfile.html", "logpatterns")
        self.ActivateThemeGallery()



## G_LogLocalThemeOverridesNode ###########################

class G_LogLocalThemeOverridesNode(G_LogChildNode, G_ThemeOverridesNode, G_ListContainedNode):
    """Logfile local theme overrides saving/restoring"""

    #-------------------------------------------------------
    def BuildPage(parent):
        # class static function
        me = __class__
        me._Sizer = parent.GetSizer()

        G_ThemeOverridesNode.BuildControl(me, parent)


    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem, name, **kwargs):
        G_ListContainedNode.__init__(self, factory, wproject, witem)
        G_ThemeOverridesNode.__init__(self, G_Const.LogThemeCls, G_ThemeNode.DomainLogfile)


    #-------------------------------------------------------
    def Activate(self):
        self.SetNodeHelp("Logfile Pattern Themes", "logfile.html", "logpatterns")
        self.ActivateControl()



## G_LogThemeContainerNode ################################

class G_LogThemeContainerNode(G_LogChildNode, G_ListContainerNode):
    """Container node for hosting theme controls"""

    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem, name, **kwargs):
        super().__init__(factory, wproject, witem)


    #-------------------------------------------------------
    def Activate(self):
        G_ListContainerNode.ActivateContainer(self)



## G_LogNode ##############################################

class G_LogNode(G_SessionChildNode, G_HideableTreeNode, G_TabContainerNode, G_DataExplorerProvider, G_DataExplorerSync):
    """
    Class that implements a logfile.
    Instances are attached to the logfile nodes in the project tree.
    """

    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem, name, **kwargs):
        super().__init__(factory, wproject, witem)
        self.SetupDataExplorer()

        self._ViewCount = 0
        self._N_Logfile = None
        self._OrigLogfileName = name

        self._InitSchemaGuid = None 
        if "schema_guid" in kwargs:
            self._InitSchemaGuid = kwargs["schema_guid"]

        self._InitBuilderGuid = None 
        if "builder_guid" in kwargs:
            self._InitBuilderGuid = kwargs["builder_guid"]

        self._InitCopyDefaults = False
        if "copy_defaults" in kwargs:
            self._InitCopyDefaults = kwargs["copy_defaults"]


    @G_Global.TimeFunction
    def PostInitNode(self):
        G_Global.GetCurrentTimer().AddArgument(self._OrigLogfileName)

        # make document fields accessible
        self._Field = D_Document(self.GetDocument(), self)

        # capture the current schema GUID
        if self._InitSchemaGuid is not None:
            self._Field.Add(self._InitSchemaGuid, "SchemaGuid", replace_existing = False)

        # and the current relative logfile path
        self._Field.Add(self._OrigLogfileName, "RelativeLogfilePath", replace_existing = False)

        # set node title to current relative path
        self.SetTreeLabel(self.GetNodeLabel())

        # open the logfile
        self._FullPath = fullpath = Path().cwd().joinpath(self._Field.RelativeLogfilePath.Value)
        self._N_Logfile = Nlog.MakeLogfile(str(fullpath), self.GetLogSchema(), G_Global.PulseProgressMeter)

        if self._N_Logfile is None:
            raise RuntimeError("Unable to index logfile {}".format(self._FullPath))

        # write saved annotations and user bookmarks (etc) into the logfile
        self._N_Logfile.PutState(self._Field.LogFileState.Value)


    def PostInitChildren(self):
        if len(self.ListSubNodes(factory_id = G_Project.NodeID_View)) != 0:
            return

        if self._InitBuilderGuid is None:
            # add a "default" view if no view children are present
            self.AppendNode(G_Project.NodeID_View)
        else:
            # otherwise follow the instructions in the builder
            builder = self.GetLogSchema().GetBuilders().GetObjectByGuid(self._InitBuilderGuid)
            for (factory_guid, theme_cls, view_theme_id) in builder.GetViewThemes():
                self.AppendNode(factory_guid, view_theme_id, True)


    def PostInitLayout(self):
        self.PostInitHideableTreeNode()


    #-------------------------------------------------------
    def Activate(self):
        self.ActivateContainer()


    #-------------------------------------------------------
    def CreatePopupMenu(self, handlers):
        menu = wx.Menu("Log file")

        menu.Append(G_Const.ID_LOGFILE_NEW_VIEW, "New view")
        handlers[G_Const.ID_LOGFILE_NEW_VIEW] = self.OnNewView

        menu.Append(G_Const.ID_LOGFILE_NEW_EVENTS, "New events table")
        handlers[G_Const.ID_LOGFILE_NEW_EVENTS] = self.OnNewEvents

        self.AppendPopupShowHide(menu, handlers, True)
        self.AppendPopupDeleteNode(menu, handlers, True)
        return menu


    #-------------------------------------------------------
    def DoClose(self, delete):
        """Release all resources owned by the logfile"""

        if self._N_Logfile is not None:
            # force release references to Nlog objects
            self._N_Logfile = None

        super().DoClose(delete)


    #-------------------------------------------------------
    def NotifyPreSave(self):
        """A save has been requested; lookup and record the log file state"""
        self._Field.LogFileState.Value = self._N_Logfile.GetState()

        relpath = G_Global.RelPath(self._FullPath)
        self._Field.RelativeLogfilePath.Value = str(relpath)


    #-------------------------------------------------------
    def GetEditors(self):
        """Create a list of all Scintilla editors viewing this logfile"""
        return [node.GetEditor() for node in self.ListSubNodes(factory_id = G_Project.NodeID_View)]


    #-------------------------------------------------------
    def GetMarkers(self, factory_id):
        """Create a list of all markers/trackers related to this logfile"""
        return self.ListSubNodes(factory_id = factory_id, recursive = True)


    #-------------------------------------------------------
    def ApplyMarkersToEditors(self, markers, editors):
        for marker in markers:
            marker.ApplyToEditors(editors)


    #-------------------------------------------------------
    def GetLogfile(self):
        return self._N_Logfile

    def GetNodeLabel(self):
        """The default logfile name is the current relative path"""
        return str(Path(self._Field.RelativeLogfilePath.Value).as_posix())

    def GetLogSchema(self):
        return GetLogSchema(self._Field.SchemaGuid.Value)

    def MakeSessionDir(self):
        session_guid = self.GetSessionNode().GetSessionGuid()
        return G_Global.MakeCacheDir(self._FullPath, session_guid)


    #-------------------------------------------------------
    def CreateDataExplorerPage(self, builder, location, page):
        builder.AddPageHeading("Log")

        builder.AddField("Path", str(self._FullPath))

        stat = self._FullPath.stat()

        size = int(stat.st_size / 1024)
        builder.AddField("Size", "{size} K".format(size = size))

        mtime = datetime.datetime.fromtimestamp(stat.st_mtime)
        builder.AddField("Modified", mtime.strftime("%A %d %B %Y %H:%M:%S"))


    #-------------------------------------------------------
    def RefreshViews(self, source_view = None):
        """Refresh all views displaying this document"""

        for view in self.ListSubNodes(factory_id = G_Project.NodeID_View):
            if not view is source_view:
                view.RefreshView()


    #-------------------------------------------------------
    def IsNew(self):
        """
        Return True of the logfile was created new, as opposed to,
        loaded from an existing document.
        """
        return self._InitCopyDefaults


    #-------------------------------------------------------
    def OnNewView(self, theme_id = None):
        self.AppendNode(G_Project.NodeID_View, theme_id)

    def OnNewEvents(self, theme_id = None, do_analysis = False):
        self.AppendNode(G_Project.NodeID_LogAnalysis, theme_id, do_analysis)

    def SetMarkersForView(self, view):
        self.ApplyMarkersToEditors(self.GetMarkers(G_Project.NodeID_Marker), [view.GetEditor()])
        self.ApplyMarkersToEditors(self.GetMarkers(G_Project.NodeID_Tracker), [view.GetEditor()])

    def AppendNode(self, guid, theme_id = None, do_analysis = False):
        """Append a new view to this logfile"""

        count = self._Field.ViewCounter.Value = self._Field.ViewCounter.Value + 1
        name = str(count)
        self.BuildNodeFromDefaults(guid, name, theme_id = theme_id, do_analysis = do_analysis)


    #-------------------------------------------------------
    def UpdateMarkerMatch(self, index, match):
        """A marker GUI page match field has been edited; update logfile"""
        valid_match = True
        if match.IsEmpty():
            self.GetLogfile().ClearAutoMarker(index)
        else:
            valid_match = self.GetLogfile().SetAutoMarker(index, match)

        if valid_match:
            self.RefreshViews()

        return valid_match


    #-------------------------------------------------------
    def UpdateMarker(self, marker):
        """Apply a marker to all child views (editors)"""
        self.ApplyMarkersToEditors([marker], self.GetEditors())

    def UpdateMarkerColour(self, marker):
        """Apply a marker colour change to all child views (editors)"""
        self.UpdateMarker(marker)

    def UpdateMarkerStyle(self, marker):
        """Apply a marker style change to all child views (editors)"""
        self.UpdateMarker(marker)



## MODULE ##################################################

G_Project.RegisterNodeFactory(
    G_NodeFactory(G_Project.NodeID_OpenView, G_Project.ArtCtrlId_Open, G_OpenViewNode)
)

G_Project.RegisterNodeFactory(
    G_NodeFactory(G_Project.NodeID_Marker, G_Project.ArtCtrlId_None, G_MarkerNode)
)

G_Project.RegisterNodeFactory(
    G_NodeFactory(G_Project.NodeID_MarkerContainer, G_Project.ArtCtrlId_Markers, G_MarkerContainerNode)
)

G_Project.RegisterNodeFactory(
    G_NodeFactory(G_Project.NodeID_Tracker, G_Project.ArtCtrlId_None, G_TrackerNode)
)

G_Project.RegisterNodeFactory(
    G_NodeFactory(G_Project.NodeID_TrackerContainer, G_Project.ArtCtrlId_Tracker, G_TrackerContainerNode)
)

G_Project.RegisterNodeFactory(
    G_NodeFactory(G_Project.NodeID_LogInfo , G_Project.ArtCtrlId_Info, G_LogInfoNode)
)

G_Project.RegisterNodeFactory(
    G_NodeFactory(G_Project.NodeID_LogGlobalThemeOverrides, G_Project.ArtCtrlId_None, G_LogGlobalThemeOverridesNode)
)

G_Project.RegisterNodeFactory(
    G_NodeFactory(G_Project.NodeID_LogLocalThemeGallery, G_Project.ArtCtrlId_None, G_LogLocalThemeGalleryNode)
)

G_Project.RegisterNodeFactory(
    G_NodeFactory(G_Project.NodeID_LogLocalThemeOverrides, G_Project.ArtCtrlId_None, G_LogLocalThemeOverridesNode)
)

G_Project.RegisterNodeFactory(
    G_NodeFactory(G_Project.NodeID_LogThemeContainer, G_Project.ArtCtrlId_Theme, G_LogThemeContainerNode)
)

G_Project.RegisterNodeFactory(
    G_NodeFactory(G_Project.NodeID_Log, G_Project.ArtDocID_Log, G_LogNode)
)
