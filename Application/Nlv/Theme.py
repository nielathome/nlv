#
# Copyright (C) Niel Clausen 2018. All rights reserved.
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
from glob import glob
from pathlib import Path
from uuid import uuid4
import xml.etree.ElementTree as et

# wxWidgets imports
import wx

# Application imports
from .Project import G_Const
from .Project import G_Global



## D_ThemeInfo #############################################

class D_ThemeInfo:
    """POD to keep track of a theme file"""

    def __init__(self, root, path):
        self._Root = root
        self._Path = path



## D_ThemeGallery ##########################################

class D_ThemeGallery:
    """
    Holds an array of themes of a particular class; provides
    support for copying, removing and renaming individual themes,
    and their backing files.
    """

    #-------------------------------------------------------
    def __init__(self, theme_cls, directories):
        self._ThemeCls = theme_cls
        self._ThemeInfoMap = {}
        self._InUse = {}
        self._Root = et.Element("root")

        file_match = "theme.{}.*.xml".format(theme_cls)
        for dir in directories:
            for file in glob(str(dir / file_match)):
                self._AddTheme(file)


    #-------------------------------------------------------
    def _IsInUse(self, theme_id):
        return theme_id in self._InUse

    def IsReadOnly(self, theme_id):
        theme = self._GetTheme(theme_id)
        if theme is not None:
            ro = self._GetTheme(theme_id).get("read_only")
            return (ro is not None) and (ro != "0")
        else:
            return True


    #-------------------------------------------------------
    def _GetTheme(self, theme_id):
        """Fetch a theme's XML element"""
        return self._Root.find("./theme[@guid='{}']".format(theme_id))

    def _GetThemeItem(self, theme_id, field_id):
        """Getch a theme item's XML element"""
        return self._GetTheme(theme_id).find("./item[@field_id='{}']".format(field_id))


    #-------------------------------------------------------
    def _AddTheme(self, path, name = None, theme_id = None):
        """
        Add a new theme file to the theme manager; allow caller to
        override the theme_id/name in the XML file.
        """
        root = et.parse(path).getroot()
        element = root.find("theme")
        self._Root.append(element)

        save = False
        if theme_id is None:
            theme_id = element.get("guid")
        else:
            element.set("guid", theme_id)
            element.set("name", name)
            element.set("read_only", "0")
            save = True

        info = D_ThemeInfo(root, path)
        self._ThemeInfoMap.update([(theme_id, info)])

        if save:
            self.SaveTheme(theme_id, info)


    #-------------------------------------------------------
    def CheckThemeId(self, theme_id):
        """
        Check whether a theme_id exists; if it doesn't return
        the id of the first available theme. Use to validate theme_ids
        in a document.
        """
        theme = self._GetTheme(theme_id)

        if theme is None:
            element = self._Root.find("./theme")
            if element is not None:
                theme_id = element.get("guid")

        return theme_id


    #-------------------------------------------------------
    def CanDelete(self, theme_id):
        """Determine whether the theme is deletable"""
        if self._IsInUse(theme_id):
            return False

        return not self.IsReadOnly(theme_id)

    def IncUse(self, theme_id):
        """Increment the use count for the theme"""
        if theme_id in self._InUse:
            self._InUse[theme_id] += 1
        else:
            self._InUse.update([(theme_id, 1)])

    def DecUse(self, theme_id):
        """Decrement the use count for the theme"""
        if self._InUse[theme_id] == 1:
            del(self._InUse[theme_id])
        else:
            self._InUse[theme_id] -= 1

    def SwitchUse(self, from_theme_id, to_theme_id):
        self.DecUse(from_theme_id)
        self.IncUse(to_theme_id)


    #-------------------------------------------------------
    def DeleteTheme(self, theme_id):
        # inverse of DuplicateTheme - remove theme and then delete the file

        if self.CanDelete(theme_id):
            element = self._GetTheme(theme_id)
            self._Root.remove(element)

            del_path = Path(self._ThemeInfoMap[theme_id]._Path)
            del_path.unlink()

            del self._ThemeInfoMap[theme_id]


    #-------------------------------------------------------
    def DuplicateTheme(self, orig_theme_id):
        element = self._GetTheme(orig_theme_id)

        # create properties for the new theme
        copy_guid = str(uuid4())
        name = element.get("name") + " (Copy)"

        # copy the theme file to a new name
        orig_path = self._ThemeInfoMap[orig_theme_id]._Path
        new_path = str(Path(G_Global.GetConfigDir()) / "theme.{}.{}.xml".format(self._ThemeCls, copy_guid))
        from shutil import copy
        copy(orig_path, new_path)

        # and load it into the gallery
        self._AddTheme(new_path, name, copy_guid)
        return copy_guid


    #-------------------------------------------------------
    def GetThemeAsText(self, theme_id):
        """Map the theme to plain text."""

        fields = []
        for item in self._GetTheme(theme_id).iterfind("item"):
            fields.append([item.get("field_id"), item.text])

        text = GetThemeStore().GetFieldsAsText(fields)

        return text


    #-------------------------------------------------------
    def GetThemeName(self, theme_id):
        return self._GetTheme(theme_id).get("name")

    def GetThemeNames(self):
        """Fetch list of pairs (name, theme_id), sorted by name"""
        def Key(element):
            return element.get("name")
        return [(e.get("name"), e.get("guid")) for e in sorted(self._Root.iterfind("theme"), key = Key)]


    #-------------------------------------------------------
    def SaveTheme(self, theme_id, info = None):
        if info is None:
            info = self._ThemeInfoMap[theme_id]
        et.ElementTree(info._Root).write(info._Path)


    #-------------------------------------------------------
    def SetThemeName(self, theme_id, name):
        """Set the GUI name for the current theme"""
        
        self._GetTheme(theme_id).set("name", name)
        self.SaveTheme(theme_id)


    #-------------------------------------------------------
    # D_Document interfaces

    def _GetThemeItemValue(self, theme_id, field_id):
        """Lookup the theme value for the supplied field ID"""
        value = self._GetThemeItem(theme_id, field_id).text
        if value is None:
            value = ""
        return value

    def _SetThemeItemValue(self, theme_id, field_id, value):
        """Save the theme value for the supplied GUID"""
        self._GetThemeItem(theme_id, field_id).text = value



## D_ThemeStore ############################################

class D_ThemeStore:
    """
    Theme storage; effectively an array of D_ThemeGallery, one
    for each known theme class
    """

    #-------------------------------------------------------
    def __init__(self):
        self._GalleryList = {}
        self._DirList = [Path(G_Global.GetConfigDir())]

        # field_id name map
        inst_dir = Path(__file__).parent
        self._FieldIdToNameMap = et.parse(inst_dir / "_field_names.xml").getroot()


    #-------------------------------------------------------
    def _MakeGallery(self, theme_cls):
        """
        Create a gallery for the given theme class, by locating all
        related theme files from all known directories
        """
        return D_ThemeGallery(theme_cls, self._DirList)


    #-------------------------------------------------------
    def RegisterDirectory(self, directory):
        """Add directory to the list of directories containing themes"""
        self._DirList.append(directory)


    #-------------------------------------------------------
    def GetFieldIdAsText(self, field_id):
        """
        Map the field ID to its friendly name. _field_names.xml
        contains entries of the form:
           <name field_id="_GUID_">_TEXT_</name>
        """
        elem = self._FieldIdToNameMap.find("./name[@field_id='{}']".format(field_id))
        if elem is None:
            return None
        else:
            return elem.text


    #-------------------------------------------------------
    def _ArrayElementsToText(self, begin_idx, end_idx, value):
        if begin_idx == end_idx:
            return "\n   {}: {}".format(begin_idx, value)
        else:
            return "\n   {}..{}: {}".format(begin_idx, end_idx, value)

    def _ArrayValueToText(self, array):
        text = ""
        values = array.split(";")

        last_value = None
        cur_idx = -1
        range_idx = 0
        for value in values:
            cur_idx += 1
            if last_value == None:
                last_value = value
                range_idx = cur_idx
            
            elif value == last_value:
                continue

            else:
                text += self._ArrayElementsToText(range_idx, cur_idx - 1, last_value)
                last_value = value
                range_idx = cur_idx

        text += self._ArrayElementsToText(range_idx, cur_idx - 1, last_value)
        return text

    def GetFieldsAsText(self, fields):
        """
        Map an array of [field_id, value] pairs to a block of
        text describing all of the fields in the array.
        """

        text = ""
        for (field_id, value) in fields:
            name = self.GetFieldIdAsText(field_id)
            if name is None:
                continue
    
            if value is None:
                value = ""
            elif G_Global.IsMarked(value) != 0:
                value = "<...>"
            elif value.find(";") >= 0:
                value = "[] =" + self._ArrayValueToText(value)
            else:
                line_return = value.find("\n")
                if line_return >= 0:
                    value = value[:line_return] + "..."

                # arbitrary limit to prevent screen overflow
                max_len = 60
                if len(value) > max_len:
                    value = value[:max_len] + "..."
            
            text = text +  "{}: {}\n".format(name, value)

        return text


    #-------------------------------------------------------
    def GetGallery(self, theme_cls):
        if not theme_cls in self._GalleryList:
            self._GalleryList.update([(theme_cls, self._MakeGallery(theme_cls))])
        return self._GalleryList[theme_cls]


    #-------------------------------------------------------
    def GetThemeSupportFile(self, filename):
        for dir in self._DirList:
            path = dir / filename
            if path.exists():
                return path

        return None



## G_ThemeNode #############################################

class G_ThemeNode:
    """
    Standard handling for nodes containing themed fields. The common case
    is where the node contains colour and style themable fields, which are
    handled here.

    The class must be inherited before any class which derives from G_Node,
    to ensure the methods here override the defaults in G_Node.

    An individual field in the UI has field_id and theme_cls attributes. The
    field_id uniquely identifies the field. The theme_cls (global, log,
    view or event) identifies which fields belong to which theme. I.e. all
    fields in a theme have the same theme_cls.

    Theme classes are divided into two types, the single global theme, and
    the local themes (log, view and event). Note that a given node can
    contain fields from different classes - namely the global theme class
    and a local theme class. E.g. look at a Search node.

    A theme (the XML file) is a list of values, one for each field_id in the
    theme.

    The theme class defines which theme gallery node (G_ThemeGalleryNode)
    manages theme activation (and copying, renaming, deleting):
    . global - Session | Theme
    . local (log, view, event) - their namesake node.

    On activation, the relevent set of nodes receive a notification
    (OnThemeChange) to update their UI, as themed field values may have
    changed. The relevent set is the entire tree for the global theme class,
    and the nodes within the log/view/event sub-tree for the other classes.
    The node should use the theme class to determine which field values
    it needs to process and update in the UI.

    A theme override node manages the relationship between nodes within
    the override node's 'domain' and a theme. The domains are log, view and
    event. All children of a view or event node will belong to the domain
    with the same name. All children of a log node, except the contained
    view/event sub-trees will belong to the log domain. The override node
    can save modified field values to a theme, or clear modifications to
    a field's value, permitting the theme's value for the field to be re-
    instated.

    Since a given node can contain fields belonging to different theme
    classes, a domain can contain override nodes for more than one theme
    class - namely a the global theme class and a local theme class.

    Conversely, a given domain is not guaranteed to contain every field
    in a theme class. Hence the override node only manages a subset of the
    fields within a theme. I.e. a given theme may be updated (saved) via
    more than one override node, each modifying some sub-set of the fields
    (e.g. the logfile modifies marker colours, whereas a view modifies
    hiliter colours). The implementation uses both the theme class and
    domain to select specific field values to be saved or cleared.

    G_ThemeOverridesNode actions are:
    . clear - removes any local overrides. This applies only to the local
      domain (e.g. a single view). As the overrides are removed in the
      document, the nodes within the domain are notified so they can update
      their UI.

    . save - saves local overides to the theme. Nodes within the local
      domain save their overrides back to the theme. Then, the *whole*
      tree is notified of the change, as any peer log/view/event node
      could reference the newly changed theme. This is an expensive
      operation.
    """

    DomainLogfile = 0
    DomainView = 1
    DomainEvent = 2


    #-------------------------------------------------------
    def __init__(self, domain):
        # uniquely identify the owner of this item
        self._Domain = domain


    #-------------------------------------------------------
    def GetThemeOverrides(self, theme_cls, domain):
        """Identify field values which override the current theme"""
        res = []

        if domain == self._Domain:
            res = self._Field.GetThemeOverrides(theme_cls)

        return res


    #-------------------------------------------------------
    def SaveOverridesToTheme(self, theme_cls, domain):
        if domain == self._Domain:
            self._Field.SaveOverridesToTheme(theme_cls)


    #-------------------------------------------------------
    def ClearThemeOverrides(self, theme_cls, domain, notify):
        if domain is None or domain == self._Domain:
            if self._Field.ClearThemeOverrides(theme_cls) and notify:
                self.OnThemeChange(theme_cls, None)



## G_ThemeManagerNode ######################################

class G_ThemeManagerNode:
    """Common theme manager class"""

    #-------------------------------------------------------
    def __init__(self, theme_cls, domain = None):
        # uniquely identify the domain of this control
        self._Domain = domain
        self._ThemeCls = theme_cls


    #-------------------------------------------------------
    def GetThemeBaseNode(self):
        """Identify the node containing all of this manager's children"""
        return self.GetParentNode().GetParentNode()

    def _GetThemeChildren(self):
        return self.GetThemeBaseNode().ListSubNodes(recursive = True)


    #-------------------------------------------------------
    def DoClearThemeOverrides(self, notify):
        for node in self._GetThemeChildren():
            node.ClearThemeOverrides(self._ThemeCls, self._Domain, notify)



## G_ThemeOverridesNode ####################################

class G_ThemeOverridesNode(G_ThemeManagerNode):
    """Control saving/restoring of theme overrides"""

    #-------------------------------------------------------
    def BuildControl(me, page):
        window = page.GetWindow()
        me._BtnSave = wx.Button(window, label = "Save", size = G_Const.ButtonSize)
        me.BuildLabelledRow(page, "Save changes to theme:", me._BtnSave)

        me._BtnClear = wx.Button(window, label = "Clear", size = G_Const.ButtonSize)
        me.BuildLabelledRow(page, "Clear changes and revert to theme:", me._BtnClear)

        me.BuildSubtitle(page, "Changes:")
        me._TxtOverrides = wx.TextCtrl(window, style = wx.TE_READONLY | wx.TE_MULTILINE)
        me._Sizer.Add(me._TxtOverrides, proportion = 1, flag = wx.BOTTOM | wx.LEFT | wx.RIGHT | wx.EXPAND, border = G_Const.Sizer_StdBorder, userData = "ThemeOverridesNode-overrides")


    #-------------------------------------------------------
    def __init__(self, theme_cls, domain):
        G_ThemeManagerNode.__init__(self, theme_cls, domain)


    #-------------------------------------------------------
    def _GetCurrentThemeId(self):
        from .Document import GetThemeId
        return GetThemeId(self, self._ThemeCls)


    #-------------------------------------------------------
    def _SetTxtOverrides(self):
        overrides= []
        for node in self._GetThemeChildren():
            overrides.extend(node.GetThemeOverrides(self._ThemeCls, self._Domain))

        text = GetThemeStore().GetFieldsAsText(overrides)
        self._TxtOverrides.SetValue(text)

        return text != ""


    #-------------------------------------------------------
    def ActivateControl(self):
        has_overrides = self._SetTxtOverrides()
        read_only = GetThemeGallery(self._ThemeCls).IsReadOnly(self._GetCurrentThemeId())
        self._BtnSave.Enable(has_overrides and not read_only)
        self._BtnClear.Enable(has_overrides)

        self.Rebind(self._BtnSave, wx.EVT_BUTTON, self.OnSave)
        self.Rebind(self._BtnClear, wx.EVT_BUTTON, self.OnClear)


    #-------------------------------------------------------
    def OnSaveWithFrameLock(self):
        for node in self._GetThemeChildren():
            node.SaveOverridesToTheme(self._ThemeCls, self._Domain)

        # ensure consumers of the newly changed theme update their UI
        theme_id = self._GetCurrentThemeId()
        self.GetRootNode().NotifyThemeChange(self._ThemeCls, theme_id)
        self.ActivateControl()
        GetThemeGallery(self._ThemeCls).SaveTheme(theme_id)

    def OnSave(self, event):
        self.WithFrameLocked(self.OnSaveWithFrameLock)


    #-------------------------------------------------------
    def OnClearWithFrameLock(self):
        self.DoClearThemeOverrides(True)
        self.ActivateControl()

    def OnClear(self, event):
        self.WithFrameLocked(self.OnClearWithFrameLock)



## G_ThemeGalleryNode ######################################

class G_ThemeGalleryNode(G_ThemeManagerNode):
    """Theme gallery management"""

    #-------------------------------------------------------
    def BuildGallery(me, parent, name):
        # class static function
        window = parent.GetWindow()
        me._ThemeText = wx.StaticText(window, label = "#")
        me.BuildLabelledRow(parent, "Active '{}' theme:".format(name), me._ThemeText)

        me.BuildSubtitle(parent, "Available themes:")
        me._ThemeList = wx.ListCtrl(window, style = wx.LC_LIST | wx.LC_EDIT_LABELS | wx.LC_SINGLE_SEL)
        parent.GetSizer().Add(me._ThemeList, proportion = 2, flag = wx.ALL | wx.EXPAND, border = G_Const.Sizer_StdBorder, userData = "ThemeGalleryNode-theme-list")

        me.BuildSubtitle(parent, "Values:")
        me._TxtTheme = wx.TextCtrl(window, style = wx.TE_READONLY | wx.TE_MULTILINE)
        me._Sizer.Add(me._TxtTheme, proportion = 1, flag = wx.BOTTOM | wx.LEFT | wx.RIGHT | wx.EXPAND, border = G_Const.Sizer_StdBorder, userData = "ThemeGalleryNode-theme")


    #-------------------------------------------------------
    def GetThemeGallery(self):
        return GetThemeGallery(self._ThemeCls)


    #-------------------------------------------------------
    def __init__(self, theme_cls):
        G_ThemeManagerNode.__init__(self, theme_cls)


    #-------------------------------------------------------
    def PostInitThemeGallery(self, theme_id = None):
        """
        Validate the theme_id. Handles missing theme file or case
        where a document is moved to a system without the previously
        selected theme available. Note that where a theme is missing,
        it is replaced with an effectively random theme from those
        available to the current user.
        """

        if theme_id is not None:
            # user preference, via a builder
            self._Field.CurrentThemeId.Value = current_theme_id = theme_id
        else:
            current_theme_id = self._Field.CurrentThemeId.Value

            # for new documents, non-global themes default can be overridden
            # by the schema
            if self._ThemeCls != "global" and self.GetLogNode().IsNew():
                theme_id = self.GetLogNode().GetLogSchema().GetDefaultTheme(self._ThemeCls)
                if theme_id is not None:
                    current_theme_id = self._Field.CurrentThemeId.Value = theme_id

        theme_gallery = self.GetThemeGallery()
        actual_theme_id = theme_gallery.CheckThemeId(current_theme_id)
        if actual_theme_id != current_theme_id:
            self._Field.CurrentThemeId.Value = actual_theme_id

        theme_gallery.IncUse(actual_theme_id)


    #-------------------------------------------------------
    def ActivateThemeGallery(self):
        theme_list = self._ThemeList
        theme_list.DeleteAllItems()

        self.Rebind(theme_list, wx.EVT_LIST_ITEM_RIGHT_CLICK, self.OnListRightClickTheme)
        self.Rebind(theme_list, wx.EVT_LIST_KEY_DOWN, self.OnListKeyDownTheme)
        self.Rebind(theme_list, wx.EVT_LIST_ITEM_ACTIVATED, self.OnListActivateTheme)
        self.Rebind(theme_list, wx.EVT_LIST_ITEM_SELECTED, self.OnListSelectTheme)
        self.Rebind(theme_list, wx.EVT_LIST_END_LABEL_EDIT, self.OnListRenameTheme)

        self._ThemeIds = []
        current_theme_id = self._Field.CurrentThemeId.Value
        select_idx = 0
        idx = 0

        theme_gallery = self.GetThemeGallery()
        for (name, theme_id) in theme_gallery.GetThemeNames():
            if theme_gallery.IsReadOnly(theme_id):
                name = name + " (read-only)"

            if theme_id == current_theme_id:
                select_idx = idx
                self.ActivateThemeText(name, False)

            theme_list.InsertItem(idx, name)
            self._ThemeIds.append(theme_id)

            idx += 1

        theme_list.Select(select_idx)

    def ActivateThemeText(self, name = None, idx = -1, relay = True):
        if name is None:
            name = self._ThemeList.GetItemText(idx)
        
        self._ThemeText.SetLabel(name)

        if relay:
            self._Sizer.Layout()


    #-------------------------------------------------------
    def DoClose(self, delete):
        """Release all resources owned by the gallery"""

        self.GetThemeGallery().DecUse(self._Field.CurrentThemeId.Value)

        super().DoClose(delete)


    #-------------------------------------------------------
    def SwitchThemeWithFrameLock(self, new_theme_id, idx, do_clear):
        """Set the identified theme as the active theme"""
        old_theme_id = self._Field.CurrentThemeId.Value
        self.GetThemeGallery().SwitchUse(old_theme_id, new_theme_id)
        self._Field.CurrentThemeId.Value = new_theme_id

        if do_clear:
            self.DoClearThemeOverrides(False)

        self.GetThemeBaseNode().NotifyThemeChange(self._ThemeCls, new_theme_id)
        if idx is not None:
            self.ActivateThemeText(idx = idx)

    def OnActivateTheme(self, idx, new_theme_id):
        self.WithFrameLocked(self.SwitchThemeWithFrameLock, new_theme_id, idx, True)

    def OnCopyTheme(self, theme_id):
        new_theme_id = self.GetThemeGallery().DuplicateTheme(theme_id)
        self.WithFrameLocked(self.SwitchThemeWithFrameLock, new_theme_id, None, False)
        self.Activate()

    def OnDeleteTheme(self, theme_id):
        self.GetThemeGallery().DeleteTheme(theme_id)
        self.Activate()


    #-------------------------------------------------------
    def OnListActivateTheme(self, event):
        """A theme has been activated in the list, set it as the current theme"""
        idx = event.GetIndex()
        self.OnActivateTheme(idx, self._ThemeIds[idx])

    def OnListRenameTheme(self, event):
        """The user has edited a theme name in the theme list"""
        idx = event.GetIndex()
        theme_id = self._ThemeIds[idx]
        new_name = event.GetText()
        self.GetThemeGallery().SetThemeName(theme_id, new_name)
        if self._Field.CurrentThemeId.Value == theme_id:
            self.ActivateThemeText(idx = idx)

    def OnListSelectTheme(self, event):
        """The user has selected a theme in the list"""
        theme_id = self._ThemeIds[event.GetIndex()]
        desc = self.GetThemeGallery().GetThemeAsText(theme_id)
        self._TxtTheme.SetValue(desc)


    #-------------------------------------------------------
    def OnListDispatch(self, cmd, idx):
        """Handle a list request - not very extensible code"""
        theme_id = self._ThemeIds[idx]

        if cmd == G_Const.ID_THEME_ACTIVATE:
            self.OnActivateTheme(idx, theme_id)

        elif cmd == G_Const.ID_THEME_COPY:
            self.OnCopyTheme(theme_id)

        elif self._CanDeleteTheme(idx) and cmd == G_Const.ID_THEME_DELETE:
            self.OnDeleteTheme(theme_id)

        elif not self._IsReadOnlyTheme(idx) and cmd == G_Const.ID_THEME_RENAME:
            # theme rename has been requested; set the list to edit mode
            self._ThemeList.EditLabel(idx)


    #-------------------------------------------------------
    def _IsCurrentTheme(self, idx):
        my_theme_id = self._ThemeIds[idx]
        cur_theme_id = self._Field.CurrentThemeId.Value
        return my_theme_id == cur_theme_id

    def _CanDeleteTheme(self, idx):
        return self.GetThemeGallery().CanDelete(self._ThemeIds[idx])

    def _IsReadOnlyTheme(self, idx):
        return self.GetThemeGallery().IsReadOnly(self._ThemeIds[idx])

    def OnListRightClickTheme(self, event):
        # build the popup menu
        idx = event.GetIndex()

        menu = wx.Menu("Theme")

        if not self._IsCurrentTheme(idx):
            menu.Append(G_Const.ID_THEME_ACTIVATE, "Activate\tEnter")

        menu.Append(G_Const.ID_THEME_COPY, "Copy\tInsert")

        if not self._IsReadOnlyTheme(idx):
            menu.Append(G_Const.ID_THEME_RENAME, "Rename ...\tF2")

        if self._CanDeleteTheme(idx):
            menu.Append(G_Const.ID_THEME_DELETE, "Delete\tDelete")

        # get and action request from user
        cmd = self._ThemeList.GetPopupMenuSelectionFromUser(menu)
        self.OnListDispatch(cmd, idx)

    def OnListKeyDownTheme(self, event):
        # documentation says index < 0 if nothing is selected
        idx = event.GetIndex()
        if idx < 0:
            return

        cmd = 0
        key_code = event.GetKeyCode()
        if key_code == wx.WXK_INSERT:
            cmd = G_Const.ID_THEME_COPY
        elif key_code == wx.WXK_F2:
            cmd = G_Const.ID_THEME_RENAME
        elif key_code == wx.WXK_DELETE:
            cmd = G_Const.ID_THEME_DELETE

        if cmd != 0:
            self.OnListDispatch(cmd, idx)



## PRIVATE #################################################

_ThemeStore = None



## MODULE ##################################################

def GetThemeStore():
    global _ThemeStore
    if _ThemeStore is None:
        _ThemeStore = D_ThemeStore()
    return _ThemeStore

def GetThemeGallery(theme_cls = "global"):
    return GetThemeStore().GetGallery(theme_cls)

def GetThemeSupportFile(filename):
    return GetThemeStore().GetThemeSupportFile(filename)
