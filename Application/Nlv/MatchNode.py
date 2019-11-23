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
import html
from pathlib import Path
import xml.etree.ElementTree as et

# wxWidgets imports
import wx.dataview
import wx.html

# Application imports
from .Document import D_Document
from .Global import G_Const
from .Global import G_Global
from .Project import G_WindowInfo

# Content provider interface
import Nlog



## G_MatchItemMetaData #####################################

class G_MatchItemMetaData:
    """Descriptive information for the various match item types"""

    #-------------------------------------------------------
    def __init__(self, name, abbreviation, use_case, use_search_ctrl, selector_id):
        self.Name = name
        self.Abbreviation = abbreviation
        self.UseCase = use_case
        self.UseSearchCtrl = use_search_ctrl
        self.SelectorId = selector_id



## G_MatchItem #############################################

class G_MatchItem(D_Document.D_Value):
    """Definition (and 'state') of a text search, match, or filter"""

    #-------------------------------------------------------
    _MetaData = [
        G_MatchItemMetaData("Literal", "lit", True, True, Nlog.EnumSelector.Literal),
        G_MatchItemMetaData("Regular Expression", "re", True, True, Nlog.EnumSelector.RegularExpression),
        G_MatchItemMetaData("LogView Filter", "LVF", False, False, Nlog.EnumSelector.LogviewFilter),
        G_MatchItemMetaData("LogView Analyser", "LVA", False, False, Nlog.EnumSelector.LogviewFilter)
    ]


    #-------------------------------------------------------
    def GetMatchType(abbreviation):
        """(Static) Convert a type abbreviation back to a full match type"""

        # backwards compatibility
        if abbreviation == "LFL":
            abbreviation = "LVF"

        me = __class__
        for meta in me._MetaData:
            if meta.Abbreviation == abbreviation:
                return meta.Name

        raise RuntimeError


    #-------------------------------------------------------
    def GetMetaDataForType(match_type):
        """(Static) Fetch metadata for the supplied type"""

        for meta in __class__._MetaData:
            if meta.Name == match_type:
                return meta

        raise RuntimeError("Unrecognised match item type: {}".format(match_type))


    #-------------------------------------------------------
    def GetMetaNames(with_filter):
        """(Static) Fetch a list of match item types"""

        # fetch all metadata names
        me = __class__
        names = [meta.Name for meta in me._MetaData]

        # determine the number of names to return: 2 for no filter support, otherwise, 3
        num_names = 2
        if with_filter:
            num_names = 3

        return names[0:num_names]


    #-------------------------------------------------------
    def MakeMatchItem(match_like_item):
        """(Static) Copy construct a real G_MatchItem from a G_MatchItem-like object"""
        item = G_MatchItem()
        item.MatchType = match_like_item.MatchType
        item.MatchText = match_like_item.MatchText
        item.MatchCase = match_like_item.MatchCase

        # confirm the MatchType is valid
        item.GetMetaData()

        return item


    #-------------------------------------------------------
    def __init__(self, match_type = "Literal", match_text = "", match_case = True):
        if type(match_text) is not str:
            raise TypeError

        self.MatchType = match_type
        self.MatchText = match_text
        self.MatchCase = match_case

        # confirm the MatchType is valid
        self.GetMetaData()


    #-------------------------------------------------------
    def __eq__(self, other):
        return self.MatchText == other.MatchText and self.MatchType == other.MatchType and self.MatchCase == other.MatchCase


    #-------------------------------------------------------
    def GetMetaData(self):
        # backwards compatibility
        if self.MatchType == "LogView Filter Language":
            self.MatchType = "LogView Filter"
    
        return G_MatchItem.GetMetaDataForType(self.MatchType)


    #-------------------------------------------------------
    def GetSelectorId(self):
        return self.GetMetaData().SelectorId


    #-------------------------------------------------------
    def IsEmpty(self):
        """Return True if the match has no content"""
        return len(self.MatchText) == 0


    #-------------------------------------------------------
    def GetDescription(self):
        """Determine a representatitive description of the filter"""
        if self.IsEmpty():
            return "Cleared"
        else:
            return "{type}=[{text}]".format(type = self.MatchType, text = self.MatchText)



## G_MatchAllHistoryStore ##################################

class G_MatchAllHistoryStore:
    """Global history store management"""

    #-------------------------------------------------------
    def __init__(self):
        self._Changed = False

        # global store kept on a per-user install basis
        path = self._StorePath = Path(G_Global.GetConfigDir()) / "Search.xml"
        if path.exists():
            self._XmlStore = et.parse(path).getroot()
        else:
            self._XmlStore = et.Element("root")


    #-------------------------------------------------------
    def GetXml(self):
        return self._XmlStore


    #-------------------------------------------------------
    def SetChanged(self):
        self._Changed = True


    #-------------------------------------------------------
    def Save(self):
        if(self._Changed):
            et.ElementTree(self._XmlStore).write(self._StorePath)
        self._Changed = False



## G_MatchAllHistoryModel ##################################

class G_MatchAllHistoryModel(wx.dataview.PyDataViewModel):
    """Globally shared history list of all match terms"""

    _ColumnMap = {
        0 : "string", # search type
        1 : "bool",   # case sensitive
        2 : "string"  # search text
    }

    _AttributeMap = [
        "crt",
        "use",
        "cnt",
        "type",
        "case",
    ]


    #-------------------------------------------------------
    def __init__(self, store):
        super().__init__()
        self._Store = store
        self._Filter = ""


    #-------------------------------------------------------
    def SetFilter(self, filter):
        """Filter items in the model"""
        if filter != self._Filter:
            self._Filter = filter
            self.Cleared()


    #-------------------------------------------------------
    def SetKey(self, key):
        """The key distinguishes the purpose of a match (e.g. filter or search)"""
        self._Key = key.lower()
        self._Filter = ""


    #-------------------------------------------------------
    def AddItem(self, key, match):
        """Add a match item to the global history"""

        self._Store.SetChanged()

        when = datetime.datetime.today()
        whens = when.isoformat(" ", "seconds")

        case = "0"
        if match.MatchCase:
            case = "1"

        type = match.GetMetaData().Abbreviation
        term = match.MatchText

        # first, see if the entry already exists
        group = self.GetGroup(key)
        for e in group.iterfind("item"):
            if type != e.get("type"):
                continue
            if case != e.get("case"):
                continue
            if term != e.text:
                continue

            # entry found, so modify it in the store
            count = int(e.get("cnt")) + 1
            counts = "{:0>4}".format(count)

            e.set("use", whens)
            e.set("cnt", counts)
            return

        # still here, add the entry
        element = et.SubElement(group, "item", type = type, case = case, crt = whens, use = whens, cnt = "0001")
        element.text = term


    #-------------------------------------------------------
    def ClearItems(self, items):
        """Delete items from the history"""

        self._Store.SetChanged()

        group = self._Store.GetXml().find(self._Key)
        for item in items:
            group.remove(self.ItemToObject(item))

        self.Cleared()


    #-------------------------------------------------------
    def GetItem(self, item):
        """Fetch a match item from the global history"""
        if item.GetID() is None:
            return None

        else:
            element = self.ItemToObject(item)
            match_type = G_MatchItem.GetMatchType(element.get("type"))
            match_case = element.get("case") != "0"
            match_text = element.text
            return G_MatchItem(match_type, match_text, match_case)


    #-------------------------------------------------------
    def GetGroup(self, key = None):
        """Fetch a group of history items by key"""

        if key is None:
            key = self._Key

        xml = self._Store.GetXml()
        group = xml.find(key)
        if group is None:
            group = et.SubElement(xml, key)

        return group


    #-------------------------------------------------------
    def GetColumnCount(self):
        """Report how many columns this model provides data for."""
        # Maintenance note: have never seen this called
        return 6


    def GetColumnType(self, col):
        """Map the data column numbers to the data type"""
        # Maintenance note: have never seen this called
        return _ColumnMap[col]


    def GetChildren(self, parent, children):
        """
        The view calls this method to find the children of any node in the
        control. There is an implicit hidden root node, and the top level
        item(s) should be reported as children of this node. A List view
        simply provides all items as children of this hidden root. A Tree
        view adds additional items as children of the other items, as needed,
        to provide the tree hierarchy.
        """

        if parent:
            raise RuntimeError

        filter = self._Filter
        no_filter = filter == ""

        # "children" argument has no extend method, so use iterator here
        count = 0
        for e in self.GetGroup().iterfind("item"):
            if no_filter or e.text.find(filter) >= 0:
                children.append(self.ObjectToItem(e))
                count += 1

        return count


    def IsContainer(self, item):
        """Return True if the item has children, False otherwise."""

        # The hidden root is a container
        if not item:
            return True
        return False


    def GetParent(self, item):
        "Return the item which is this item's parent."""
        # Maintenance note: have never seen this called
        return wx.dataview.NullDataViewItem


    def GetValue(self, item, col):
        """Return the value to be displayed for this item and column."""

        value = ""
        element = self.ItemToObject(item)

        if col < len(self._AttributeMap):
            value = element.get(self._AttributeMap[col])

        elif col == 5:
            value = element.text

        else:
            raise RuntimeError

        if col == 4:
            if value == "0":
                return False
            else:
                return True

        else:
            return value




## G_MatchAllHistoryPopup ##################################

class G_MatchAllHistoryPopup(wx.Dialog):
    """Window containing the history list"""

    #-------------------------------------------------------
    def __init__(self):
        # originally wanted this to be a PopupTransientWindow, but that
        # currently has some issues, and appears to steal mouse clicks from
        # the DVC control, so going with a standard dialog instead

        super().__init__(
            None, 
            style = wx.DEFAULT_DIALOG_STYLE
            | wx.CAPTION
            | wx.RESIZE_BORDER
            | wx.CLOSE_BOX
            | wx.MAXIMIZE_BOX
        )

        self._FilterHistory = []

        sizer = wx.BoxSizer(wx.VERTICAL)

        filter = self._TxtFilter = wx.SearchCtrl(self, style = wx.TE_PROCESS_ENTER)
        filter.ShowSearchButton(True)
        filter.ShowCancelButton(True)
        filter.SetDescriptiveText("Filter")

        filter.Bind(wx.EVT_SEARCHCTRL_SEARCH_BTN, self.OnFilter)
        filter.Bind(wx.EVT_SEARCHCTRL_CANCEL_BTN, self.OnFilterClear)

        sizer.Add(self._TxtFilter, flag = wx.TOP | wx.LEFT | wx.RIGHT | wx.EXPAND, border = G_Const.Sizer_StdBorder)

        dvc = self._DVC = wx.dataview.DataViewCtrl(
            self,
            size = (800,600),
            style = wx.dataview.DV_ROW_LINES
            | wx.dataview.DV_VERT_RULES
            | wx.dataview.DV_MULTIPLE
        )

        flags = wx.dataview.DATAVIEW_COL_RESIZABLE | wx.dataview.DATAVIEW_COL_SORTABLE | wx.dataview.DATAVIEW_COL_REORDERABLE
        dvc.AppendTextColumn("Created", 0, width = 130, flags = flags, align = wx.ALIGN_LEFT)
        dvc.AppendTextColumn("Accessed", 1, width = 110, flags = flags, align = wx.ALIGN_LEFT)
        dvc.AppendTextColumn("Count", 2, width = 45, flags = flags, align = wx.ALIGN_CENTER)
        dvc.AppendTextColumn("Type", 3, width = 40, flags = flags, align = wx.ALIGN_CENTER)
        dvc.AppendToggleColumn("Case", 4, width = 40, flags = flags)
        dvc.AppendTextColumn("Term", 5, flags = flags)

        dvc.Bind(wx.dataview.EVT_DATAVIEW_SELECTION_CHANGED, self.OnSelectionChanged)
        dvc.Bind(wx.dataview.EVT_DATAVIEW_ITEM_ACTIVATED, self.OnItemActivated)

        sizer.Add(dvc, 1, flag = wx.ALL | wx.EXPAND, border = G_Const.Sizer_StdBorder)

        clear = self._BtnClear = wx.Button(self, label = "Clear", size = G_Const.ButtonSize)
        clear.Bind(wx.EVT_BUTTON, self.OnClearHistory)
        sizer.Add(clear, flag = wx.BOTTOM | wx.LEFT | wx.RIGHT, border = G_Const.Sizer_StdBorder)
        clear.Enable(False)

        self.SetSizer(sizer)
        sizer.Fit(self)


    #-------------------------------------------------------
    def Display(self, host_node, model, match_key):
        """Display the history dialog"""

        self.SetTitle("All {} items:".format(match_key))
        self._BtnClear.Enable(False)
        self._TxtFilter.Clear()

        self._Node = host_node
        model.SetKey(match_key)

        dvc = self._DVC
        if dvc.GetModel() is None:
            self._DVC.AssociateModel(model)
        else:
            model.Cleared()

        val = self.ShowModal()

        self._Node = None


    #-------------------------------------------------------
    def OnClearHistory(self, event):
        """Remove selected history items"""
        dvc = self._DVC
        dvc.GetModel().ClearItems(dvc.GetSelections())


    #-------------------------------------------------------
    def OnFilter(self, event):
        filter_text = event.GetString()
        self._DVC.GetModel().SetFilter(filter_text)
        self._FilterHistory.append(filter_text)
        self._TxtFilter.AutoComplete(self._FilterHistory)


    #-------------------------------------------------------
    def OnFilterClear(self, event):
        self._DVC.GetModel().SetFilter("")


    #-------------------------------------------------------
    def OnSelectionChanged(self, event):
        """Copy the selected history item into the UI"""

        dvc = self._DVC
        self._BtnClear.Enable(dvc.HasSelection())

        match = dvc.GetModel().GetItem(event.GetItem())
        if match is None:
            return False
        else:
            self._Node.UpdateMatch(match)
            return True


    #-------------------------------------------------------
    def OnItemActivated(self, event):
        """Copy and apply the selected history item into the match"""
        if self.OnSelectionChanged(event):
            self._Node.OnMatchCmd()
            self.EndModal(0)


 
## G_HistoryManager ########################################

class G_HistoryManager:
    """Provide global access to the history manager and dialog"""

    # the manager is a singleton
    _Manager = None


    #-------------------------------------------------------
    def __init__(self):
        self._Store = None
        self._Model = None
        self._Dlg = None


    #-------------------------------------------------------
    def _GetStore(self):
        """ Fetch the initialised store """

        # If required, initialise the store; can't be done earlier, as the
        # wx.ConfigBase lookup requires wx.App to exist
        if self._Store is None:
            self._Store = G_MatchAllHistoryStore()

        return self._Store


    #-------------------------------------------------------
    def _GetModel(self):
        if self._Model is None:
            self._Model = G_MatchAllHistoryModel(self._GetStore())

        return self._Model


    #-------------------------------------------------------
    def AddItem(self, match_key, match):
        """Add a new match history item to the global list"""

        # skip empty string
        if match.MatchText == "":
            return

        self._GetModel().AddItem(match_key.lower(), match)


    #-------------------------------------------------------
    def Display(self, host_node, match_key):
        dlg = self._Dlg

        if dlg is None:
            dlg = self._Dlg = G_MatchAllHistoryPopup()
            dlg.CenterOnScreen()

        dlg.Display(host_node, self._GetModel(), match_key)


    #-------------------------------------------------------
    def Close(self):
        self.Save()

        if self._Dlg is not None:
            self._Dlg.Destroy()
            self._Dlg = None


    #-------------------------------------------------------
    def Save(self):
        if self._Store is not None:
            self._Store.Save()


# global
def GetHistoryManager():
    manager = G_HistoryManager._Manager

    if manager is None:
        manager = G_HistoryManager._Manager = G_HistoryManager()

    return manager



## G_MatchRecentHistoryList ################################

class G_MatchRecentHistoryList(wx.html.HtmlListBox):
    """Limited list of recent match terms"""

    #-------------------------------------------------------
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)


    #-------------------------------------------------------
    def OnGetItem(self, row):
        """Fetch HTML text for a list item"""

        # identify metadata
        match = G_MatchItem.MakeMatchItem(self._History[row].Value)
        meta = match.GetMetaData()

        info = [ meta.Abbreviation ]
        if meta.UseCase:
            if match.MatchCase:
                info.append("case")
            else:
                info.append("nocase")

        # convert info to suitable HTML
        match_text = html.escape(match.MatchText)
        meta_text = ""
        if len(info) != 0:
            meta_text = "<b>[</b><i>{}</i><b>]</b> ".format(", ".join(info))

        font = self.GetFont()
        return """
            <FONT face={} size={}px>
                <TABLE border="0" cellpadding="0" cellspacing="0">
                <TR>
                    <TD>{}{}</TD>
                </TR>
                </TABLE>
            </FONT>
        """.format(font.GetFaceName(), font.GetPixelSize(), meta_text, match_text)


    #-------------------------------------------------------
    def OnDrawSeparator(self, dc, rect, n):
        dc.SetPen(wx.Pen(wx.Colour(192, 192, 192), 1, wx.PENSTYLE_DOT))

        y = rect.y + rect.height - 1
        dc.DrawLine(rect.x, y, rect.x + rect.width, y)


    #-------------------------------------------------------
    def AddItem(self, match):
        """Add a new match history item to this list"""

        # skip empty string
        if match.MatchText == "":
            return

        # if match is already in the list, then remove it
        history = self._History
        for row in range(len(history)):
            cmp = history[row].Value
            if match == cmp:
                history.remove(row)
                break

        # add match to top of list
        history.Add(match, at_front = True)

        # prevent excessive list length
        if len(history) > 30:
            history.remove()

        # redraw control
        self.SetItemCount(len(history))
        self.Refresh()


    #-------------------------------------------------------
    def Update(self, history):
        self._History = history
        self.SetItemCount(len(history))
        self.Refresh()



## G_MatchNode #############################################

class G_MatchNode:
    """Helper class to extend nodes with UI support for text search"""

    #-------------------------------------------------------
    def BuildMatch(me, page, subtitle, height = -1, search = False, filter = False, search_buttons = False):
        # class static function
        me._ShowSearchButtons = search_buttons

        # all match controls live in a single sizer; for show/hide control
        window = page.GetWindow()
        me._MatchSizer = vsizer = wx.BoxSizer(wx.VERTICAL)
        match_page = G_WindowInfo(vsizer, window)

        me.BuildSubtitle(match_page, "{} properties:".format(subtitle))

        # add Match Type combo box and case-sensitivity check box
        me._ComboMatchType = wx.ComboBox(window,
            style = wx.CB_DROPDOWN | wx.CB_READONLY,
            choices = G_MatchItem.GetMetaNames(filter)
        )
        me._ChkMatchCase = wx.CheckBox(window, label = "Case sensitive")
        me.BuildRow(match_page, me._ComboMatchType, me._ChkMatchCase, "MatchNode-type")

        me.BuildSubtitle(match_page, "{} description:".format(subtitle))

        # unfortunately, the search control does a lousy job when set to multiple lines, as it tries
        # to scale up the search/cancel buttons, with comical consequences - so we use different
        # controls in different circumstances, which is tedious
        me._TextSearch = wx.SearchCtrl(window, size = (-1, -1), style = wx.TE_PROCESS_ENTER)
        me._TextSearch.ShowSearchButton(True)
        me._TextSearch.ShowCancelButton(True)
        me._TextSearch.SetDescriptiveText(subtitle)
        vsizer.Add(me._TextSearch, flag = wx.BOTTOM | wx.LEFT | wx.RIGHT | wx.EXPAND, border = G_Const.Sizer_StdBorder, userData = "MatchNode-search-text")

        me._TextSimple = wx.TextCtrl(window, size = (-1, height), style = wx.TE_BESTWRAP | wx.TE_MULTILINE)
        vsizer.Add(me._TextSimple, flag = wx.BOTTOM | wx.LEFT | wx.RIGHT | wx.EXPAND, border = G_Const.Sizer_StdBorder, userData = "MatchNode-simple-text")

        row_sizer = wx.BoxSizer(wx.HORIZONTAL)
        vsizer.Add(row_sizer, flag = wx.ALL | wx.EXPAND, border = G_Const.Sizer_StdBorder, userData = "MatchNode-controls")
        row_sizer.AddStretchSpacer(1)

        btn = me._BtnApply = wx.Button(window, label = "Apply", size = G_Const.ButtonSizeSmall)
        row_sizer.Add(btn, flag = wx.ALIGN_CENTER_VERTICAL)

        btn = me._BtnClear = wx.Button(window, label = "Clear", size = G_Const.ButtonSizeSmall)
        row_sizer.AddSpacer(G_Const.ButtonSpacer)
        row_sizer.Add(btn, flag = wx.ALIGN_CENTER_VERTICAL)

        # if requested, add search buttons
        if me._ShowSearchButtons:
            btn = me._BtnSearchRev = wx.Button(window, label = "<< Prev", size = G_Const.ButtonSizeSmall)
            row_sizer.AddSpacer(G_Const.ButtonSpacer)
            row_sizer.Add(btn, flag = wx.ALIGN_CENTER_VERTICAL)
            
            btn = me._BtnSearchFwd = wx.Button(window, label = "Next >>", size = G_Const.ButtonSizeSmall)
            row_sizer.AddSpacer(G_Const.ButtonSpacer)
            row_sizer.Add(btn, flag = wx.ALIGN_CENTER_VERTICAL)

        # add recent history label and list
        me.BuildSubtitle(match_page, "Recent {} items:".format(subtitle))
        me._ListRecentHistory = G_MatchRecentHistoryList(window, size = (-1, 200))
        vsizer.Add(me._ListRecentHistory, flag = wx.BOTTOM | wx.LEFT | wx.RIGHT | wx.EXPAND, proportion = 1, border = G_Const.Sizer_StdBorder, userData = "MatchNode-history")

        # add all history label and button
        me._BtnAllHistory = wx.Button(window, label = "Show ...", size = G_Const.ButtonSize)
        me.BuildLabelledRow(match_page, "All {} items:".format(subtitle), me._BtnAllHistory)

        # add everything to parent sizer
        page.GetSizer().Add(vsizer, flag = wx.EXPAND, border = G_Const.Sizer_StdBorder, proportion = 1, userData = "MatchNode-match")


    #-------------------------------------------------------
    def __init__(self, theme_cls, match_key):
        self._ThemeCls = theme_cls
        self._MatchKey = match_key
        self._TextMatch = None
        self._MatchColour = wx.WHITE

        
    #-------------------------------------------------------
    def PostInitMatch(self):
        # attach/initialise to match history
        self._DocumentList = self._Field.Add([], "MatchHistory", replace_existing = False)

        # ensure parents respond to match at load time
        if self._Field.MatchText.Value != "":
            self.OnMatch(self.MakeMatchItem())


    #-------------------------------------------------------
    def MakeMatchItem(self):
        """Make a match item from the current (document) state"""
        return G_MatchItem(self._Field.MatchType.Value, self._Field.MatchText.Value, self._Field.MatchCase.Value)


    #-------------------------------------------------------
    def SetTextCtrl(self, to, make_active):
        # switches between _TextSearch and _TextSimple (class variables)
        # note _TextMatch is an instance variable

        sizer = self._MatchSizer
        other = self._TextSearch
        if other == to:
            other = self._TextSimple

        other.Unbind(wx.EVT_TEXT)
        other.Enable(False)
        sizer.Show(other, False)

        self._TextMatch = to
        to.Enable(True)
        to.Unbind(wx.EVT_TEXT)
        to.SetValue(self._Field.MatchText.Value)
        to.Bind(wx.EVT_TEXT, self.OnMatchText)
        to.SetBackgroundColour(self._MatchColour)

        # make_active is a kludge to prevent changes that would otherwise
        # cause the text control to mysteriously appear when the node is not
        # active; which would happen when SetMatch is called

        # code is fragile: it can result in the text box not being changed
        # when it should; since this is relatively rare, it is seen as better
        # than the text box appearing when it should not
        if make_active:
            sizer.Show(to, True)

        sizer.Layout()


    def ActivateSearchText(self, make_active):
        self.SetTextCtrl(self._TextSearch, make_active)
        self.Rebind(self._TextSearch, wx.EVT_SEARCHCTRL_SEARCH_BTN, self.OnMatchCmd)
        self.Rebind(self._TextSearch, wx.EVT_SEARCHCTRL_CANCEL_BTN, self.OnMatchClear)


    def ActivateSimpleText(self, make_active):
        self.SetTextCtrl(self._TextSimple, make_active)


    def ActivateMatch(self):
        focus_window = None

        # show/hide match UI elements as appropriate
        show = self._Field.MatchEdit.Value
        self._Sizer.Show(self._MatchSizer, show)

        if show:
            self.Rebind(self._BtnApply, wx.EVT_BUTTON, self.OnMatchCmd)
            self.Rebind(self._BtnClear, wx.EVT_BUTTON, self.OnMatchClear)
            self.Rebind(self._ComboMatchType, wx.EVT_COMBOBOX, self.OnComboMatchType)
            self.Rebind(self._ChkMatchCase, wx.EVT_CHECKBOX, self.OnChkMatchCase)

            self.Rebind(self._ListRecentHistory, wx.EVT_LISTBOX, self.OnRecentHistorySelected)
            self.Rebind(self._ListRecentHistory, wx.EVT_LISTBOX_DCLICK, self.OnRecentHistoryActivated)

            if self._ShowSearchButtons:
                self.Rebind(self._BtnSearchRev, wx.EVT_BUTTON, self.OnCmdSearchRev)
                self.Rebind(self._BtnSearchFwd, wx.EVT_BUTTON, self.OnCmdSearchFwd)

            self.Rebind(self._BtnAllHistory, wx.EVT_BUTTON, self.OnCmdAllHistory)

            # also initialises _TextMatch
            self.UpdateMatch(self.MakeMatchItem())

            # tell caller the preferred window to switch input focus to
            focus_window = self._TextMatch

        return focus_window


    #-------------------------------------------------------
    def UpdateMatchText(self, text):
        if self._Field.MatchText.Value != text:
            self._Field.MatchText.Value = text

    def UpdateMatchType(self, type, make_active = True):
        if self._Field.MatchType.Value != type:
            self._Field.MatchType.Value = type

        meta = G_MatchItem.GetMetaDataForType(type)
        self._ChkMatchCase.Enable(meta.UseCase)
        if meta.UseSearchCtrl:
            self.ActivateSearchText(make_active)
        else:
            self.ActivateSimpleText(make_active)


    def UpdateMatchCase(self, case):
        if self._Field.MatchCase.Value != case:
            self._Field.MatchCase.Value = case


    def UpdateMatch(self, match_item, make_active = True, update_history = True):
        """Set UI controls and document state from the supplied state"""
        self._ComboMatchType.SetValue(match_item.MatchType)
        self.UpdateMatchType(match_item.MatchType, make_active)

        self._TextMatch.SetValue(match_item.MatchText)
        self.UpdateMatchText(match_item.MatchText)

        self._ChkMatchCase.SetValue(match_item.MatchCase)
        self.UpdateMatchCase(match_item.MatchCase)

        if update_history:
            self._ListRecentHistory.Update(self._DocumentList)


    #-------------------------------------------------------
    def OnMatchText(self, event):
        """The match text has altered; keep a copy of it"""
        self.UpdateMatchText(self._TextMatch.GetValue())


    #-------------------------------------------------------
    @G_Global.TimeFunction
    def OnMatchCmd(self, event = None, update_history = True, refocus = True):
        """Action the match; derived class must implement OnMatch"""
        match_item = self.MakeMatchItem()
        if self.OnMatch(match_item, refocus):
            if update_history:
                GetHistoryManager().AddItem(self._MatchKey, match_item)
                self._ListRecentHistory.AddItem(match_item)
            self._MatchColour = wx.WHITE
        else:
            self._MatchColour = wx.TheColourDatabase.Find("ORANGE")

        if self._TextMatch is not None:
            self._TextMatch.SetBackgroundColour(self._MatchColour)
            self._TextMatch.Refresh()


    #-------------------------------------------------------
    def SetMatch(self, match, make_active = True, update_history = True, refocus = True):
        """Programmatically update the search/filter"""
        if make_active:
            self.MakeActive()
        self.UpdateMatch(match, make_active, update_history)
        self.OnMatchCmd(update_history = update_history, refocus = refocus)


    #-------------------------------------------------------
    def OnMatchClear(self, event):
        self._TextMatch.SetValue("")
        self.OnMatchCmd()


    #-------------------------------------------------------
    def OnComboMatchType(self, event):
        self.UpdateMatchType(self._ComboMatchType.GetValue())


    #-------------------------------------------------------
    def OnChkMatchCase(self, event):
        self.UpdateMatchCase(self._ChkMatchCase.GetValue())


    #-------------------------------------------------------
    def OnRecentHistorySelected(self, event):
        """Copy the selected history item into the match"""
        self.UpdateMatch(self._DocumentList[event.GetSelection()].Value)
        

    #-------------------------------------------------------
    def OnRecentHistoryActivated(self, event):
        """Copy and apply the selected history item into the match"""
        self.OnRecentHistorySelected(event)
        self.OnMatchCmd()


    #-------------------------------------------------------
    def OnCmdSearchRev(self, event):
        self.OnSearch(forward = False)

    def OnCmdSearchFwd(self, event):
        self.OnSearch(forward = True)


    #-------------------------------------------------------
    def OnCmdAllHistory(self, event):
        GetHistoryManager().Display(self, self._MatchKey)


    #-------------------------------------------------------
    def OnThemeChange(self, theme_cls, theme_id):
        """The match has altered; refresh match controls and the associated editors"""
        if self.IsThemeApplicable(theme_cls, theme_id, self._ThemeCls):
            self.OnMatchCmd(update_history = False, refocus = False)

