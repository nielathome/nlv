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
import datetime
import html
import io
import logging
from pathlib import Path
import time
from uuid import uuid4
from weakref import ref as MakeWeakRef
import xml.etree.ElementTree as et

# wxWidgets imports
import wx
import wx.html2

# Application imports
from .Document import D_Document
from .Extension import GetExtensionNames
from .Logmeta import GetLogSchema, GetLogSchemataNames
from .Project import G_Const
from .Project import G_Global
from .Project import G_TabContainerNode
from .Project import G_TabContainedNode
from .Project import G_TreeNode
from .Project import G_NodeFactory
from .Project import G_Project
from .Project import G_WindowInfo
from .Shell import G_Shell
from .Theme import G_ThemeGalleryNode
from .Theme import GetThemeGallery

# Content provider interface
import Nlog


## G_DataExplorerPageCache #################################

class G_DataExplorerPageCache:
    """Wrapper for wx.MemoryFSHandler"""

    _MaxHistory = 150


    #-------------------------------------------------------
    def __init__(self):
        # both containers have the same contents, but are used
        # for different purposes

        # order list of keys, first entry is oldest, last is newest
        self._MRU = []

        # tuples of validity (date/time) and navigability of a page
        self._Keys = dict()


    #-------------------------------------------------------
    def Clear(self):
        for key in self._Keys:
            wx.MemoryFSHandler.RemoveFile(key)

        self._MRU.clear()
        self._Keys.clear()


    #-------------------------------------------------------
    def Remove(self, key):
        wx.MemoryFSHandler.RemoveFile(key)
        self._MRU.remove(key)
        del self._Keys[key]


    #-------------------------------------------------------
    def Prune(self):
        while len(self._MRU) > self._MaxHistory:
            self.Remove(self._MRU[0])


    #-------------------------------------------------------
    def Contains(self, key):
        contains = key in self._Keys
        if contains:
            # effectively, drop key to end of MRU list; makes
            # it the most-recently-used key
            self._MRU.remove(key)
            self._MRU.append(key)
        return contains


    #-------------------------------------------------------
    def Valid(self, key, ref_date):
        # returns a tuple of validity and navigability; a
        # valid is key where the cache entry was created after
        # the reference date
        cache_date, navigable = self._Keys[key]
        return (ref_date < cache_date, navigable)


    #-------------------------------------------------------
    def Add(self, key, data, navigable = True):
        if key in self._Keys:
            self.Remove(key)

        self._Keys[key] = (datetime.datetime.now(), navigable)
        self._MRU.append(key)
        wx.MemoryFSHandler.AddFileWithMimeType(key, data, "text/html")
        self.Prune()
    


## G_DataExplorerPageBuilder ###############################

def MakeWebUrl(data_url):
    return "memory:" + data_url

class G_DataExplorerPageBuilder:
    """Support building pages to display in the data explorer"""

    _PageHead = """
        <!DOCTYPE html>
        <html>
        <head>
            <link rel="stylesheet" type="text/css" href="memory:style.css">
        </head>
        <body>
    """

    _PageTail = """
        </body></html>
    """


    #-------------------------------------------------------
    def __init__(self, data_explorer):
        self._DataExplorer = data_explorer
        self._HtmlStream = io.StringIO()
        self.AddText(self._PageHead)


    #-------------------------------------------------------
    def AddText(self, text):
        self._HtmlStream.write(text + "\n")

    def AddElement(self, tag, text, style = None):
        if style is not None:
            style = ' style="{style}"'.format(style = style)
        else:
            style = ""

        self.AddText("<{tag}{style}>{text}</{tag}>".format(tag = tag, style = style, text = html.escape(text)))


    #-------------------------------------------------------
    def AddPageHeading(self, text, style = None):
        self.AddElement("h1", text, style)

    def AddFieldHeading(self, text):
        self.AddElement("h2", text)

    def AddFieldValue(self, text):
        self.AddElement("p", text)

    def AddField(self, heading, value):
        self.AddFieldHeading(heading)
        self.AddFieldValue(value)

    def AddLink(self, data_url, text):
        if self._DataExplorer.CreatePage(data_url):
            self.AddText('<p><a href="{web_url}">{text}</a></p>'.format(web_url = MakeWebUrl(data_url), text = html.escape(text)))


    #-------------------------------------------------------
    def Close(self):
        self.AddText(self._PageTail)
        return self._HtmlStream.getvalue()



## G_DataExplorer ##########################################

class G_DataExplorer:
    """Class that implements the project data explorer panel"""

    _DataExplorer = None

    _NodePathSplit = "__node_path__"
    _LocationSplit = "__at__"
    _PageSplit = "__page__"


    #-------------------------------------------------------
    @classmethod
    def SplitDataUrl(cls, url):
        # url is node-factory-id<path-split>node-path<loc-split>location<page-split>page
        factory_id, rem = url.split(cls._NodePathSplit)
        node_path, rem = rem.split(cls._LocationSplit)
        location, page = rem.split(cls._PageSplit)

        return factory_id, node_path, location, page


    @classmethod
    def MakeDataUrl(cls, factory_id, node_path, location, page):
        return "{factory_id}{node_split}{node_path}{loc_split}{location}{page_split}{page}".format(
            factory_id = factory_id,
            node_split = cls._NodePathSplit, node_path = node_path,
            loc_split = cls._LocationSplit, location = location,
            page_split = cls._PageSplit, page = page
        )


    #-------------------------------------------------------
    @classmethod
    def Instance(cls, frame = None):
        if cls._DataExplorer == None:
            cls._DataExplorer = cls(frame)
        return cls._DataExplorer


    #-------------------------------------------------------
    def __init__(self, frame):
        self._Frame = frame
        self._PageCache = G_DataExplorerPageCache()
        self._LastWebUrl = None

        parent = frame.GetDataExplorer()

        # create web control
        self._WebView = wx.html2.WebView.New(parent)
        self._WebView.EnableHistory(True)

        # setup virtual filesystem: "memory:"
        wx.FileSystem.AddHandler(wx.MemoryFSHandler())
        self._WebView.RegisterHandler(wx.html2.WebViewFSHandler("memory"))

        # can't seem to access local files from HTML; so workaround
        with open(str(Path( __file__ ).parent.joinpath("data.css"))) as css_file:
            css_str = css_file.read();
            wx.MemoryFSHandler.AddFile("style.css", css_str)

        # layout
        vsizer = wx.BoxSizer(wx.VERTICAL)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        parent.Bind(wx.html2.EVT_WEBVIEW_NAVIGATING, self.OnWebViewNavigating)

        button = wx.Button(parent, style = wx.BU_NOTEXT)
        button.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_GO_BACK, wx.ART_TOOLBAR, (16, 16)))
        button.SetToolTip("Navigate to previous location in history")
        parent.Bind(wx.EVT_BUTTON, self.OnPrevPageButton, button)
        hsizer.Add(button, proportion = 0, flag = wx.EXPAND)
        parent.Bind(wx.EVT_UPDATE_UI, self.OnCheckCanGoBack, button)

        button = wx.Button(parent, style = wx.BU_NOTEXT)
        button.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_GO_FORWARD, wx.ART_TOOLBAR, (16, 16)))
        button.SetToolTip("Navigate to next location in history")
        parent.Bind(wx.EVT_BUTTON, self.OnNextPageButton, button)
        hsizer.Add(button, proportion = 0, flag = wx.EXPAND)
        parent.Bind(wx.EVT_UPDATE_UI, self.OnCheckCanGoForward, button)

        vsizer.Add(hsizer, proportion = 0, flag = wx.EXPAND | wx.ALL, border = G_Const.Sizer_StdBorder)
        vsizer.Add(self._WebView, proportion = 1, flag = wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border = G_Const.Sizer_StdBorder)
        parent.SetSizer(vsizer)


    #-------------------------------------------------------
    def FindNode(self, factory_id, node_path):
        root_node = self._Frame.GetProject().GetRootNode()
        for node in root_node.ListSubNodes(factory_id, recursive = True):
            if node.GetNodePath() == node_path:
                return node
        return None


    #-------------------------------------------------------
    def ClearHistory(self):
        self._PageCache.Clear()
        self._WebView.ClearHistory()


    #-------------------------------------------------------
    def CreatePage(self, data_url):
        factory_id, node_path, location, page = self.SplitDataUrl(data_url)
        node = self.FindNode(factory_id, node_path)

        if node is not None:
            if not self._PageCache.Contains(data_url):
                page_builder = G_DataExplorerPageBuilder(self)
                node.CreateDataExplorerPage(page_builder, location, page)
                self._PageCache.Add(data_url, page_builder.Close())
            return True

        else:
            return False


    def Update(self, data_url):
        if self.CreatePage(data_url):
            self._LastWebUrl = web_url = MakeWebUrl(data_url)
            self._WebView.LoadURL(web_url)


    #-------------------------------------------------------
    def MakeErrorPage(self, title, text, data_url):
        builder = G_DataExplorerPageBuilder(self)
        builder.AddPageHeading(title, "color:darkred")
        builder.AddFieldValue(text)

        factory_id, node_path, location, page = self.SplitDataUrl(data_url)
        builder.AddField("Path", node_path)
        builder.AddField("Location", location)
        builder.AddField("Page", page)

        self._PageCache.Add(data_url, builder.Close(), False)


    #-------------------------------------------------------
    def OnPrevPageButton(self, event):
        self._WebView.GoBack()

    def OnNextPageButton(self, event):
        self._WebView.GoForward()

    def OnCheckCanGoBack(self, event):
        event.Enable(self._WebView.CanGoBack())

    def OnCheckCanGoForward(self, event):
        event.Enable(self._WebView.CanGoForward())


    #-------------------------------------------------------
    def OnWebViewNavigating(self, event):
        web_url = event.GetURL()
        if web_url.find("memory:") != 0:
            return

        scheme, data_url = web_url.split(':')
        if not self._PageCache.Contains(data_url):
            self.MakeErrorPage("Page not found", "The data explorer page has dropped from the cache, and its data is no longer available.", data_url)

        factory_id, node_path, location, page = self.SplitDataUrl(data_url)
        node = self.FindNode(factory_id, node_path)

        if node is None:
            self.MakeErrorPage("View not found", "The view cannot be found. It has probably been deleted.", data_url)
            return

        valid, navigable = self._PageCache.Valid(data_url, node.GetDataExplorerValidDate())
        if not valid:
            self.MakeErrorPage("Outdated View", "The view has been modified, and has not been synchronised to the data explorer.", data_url)
            return

        if navigable and self._LastWebUrl != web_url and node.ShowLocation(location):
            node.MakeActive()
            self._LastWebUrl = web_url

        

## G_DataExplorerChildNode #################################

class G_DataExplorerChildNode():

    """
    G_DataExplorer integration/support. Nodes will need to
    implement:
        GetNodePath()
        GetFactoryID()
        ShowLocation(location)
        CreateDataExplorerPage(builder, location, page)
    """

    #-------------------------------------------------------
    def GetDataExplorer(self):
        return self.GetSessionNode().GetDataExplorer()


    #-------------------------------------------------------
    def MakeDataUrl(self, location = "any", page = "0"):
        return G_DataExplorer.MakeDataUrl(self.GetFactoryID(), self.GetNodePath(), location, page)


    #-------------------------------------------------------
    def ShowLocation(self, location):
        # default is to do nothing
        return False


    #-------------------------------------------------------
    def SetDataExplorerValid(self):
        self._DataExplorerValid = datetime.datetime.now()

    def GetDataExplorerValidDate(self):
        return self._DataExplorerValid



## G_SessionManager ########################################

class G_SessionManager:
    """
    Manage the creation and saving of sessions; implemented as a singleton.
    """

    #-------------------------------------------------------
    _HistoryLen = 30

    def __init__(self):
        self._WRootNode = None


    #-------------------------------------------------------
    def _MakeKey(self, idx):
        return "{}".format(idx)


    #-------------------------------------------------------
    def _ListTouch(self, path_or_idx):
        """
        Moves the given item to the top of the history list
        Returns latest history path, or '' if none exists
        """

        # fetch and update list
        item = ""
        list = self.GetRecent()
        if isinstance(path_or_idx, int):
            if path_or_idx < len(list):
                item = list.pop(path_or_idx)
        else:
            item = path_or_idx
            try:
                list.remove(path_or_idx)
            except:
                pass

        list.insert(0, item)

        # save the revised list back to user preferences
        config = wx.ConfigBase.Get()
        config.SetPath("/NLV/SessionList")
        for i in range(self._HistoryLen):
            path = ""
            if i < len(list):
                path = list[i]
            config.Write(self._MakeKey(i), path)

        config.Flush()

        return list[0]


    #-------------------------------------------------------
    def AppError(self, message):
        self.GetRootNode().AppError(message)


    #-------------------------------------------------------
    def GetRecent(self):
        """Copy the session history list from the user configration data"""
        list = []

        config = wx.ConfigBase.Get()
        config.SetPath("/NLV/SessionList")
        for i in range(self._HistoryLen):
            path = config.Read(self._MakeKey(i))
            if path != "" and Path(path).is_file():
                list.append(path)

        return list

    def GetRootNode(self):
        # will force crash if used improperly
        return self._WRootNode()

    def GetSessionNode(self):
        return self.GetRootNode().FindChildNode(G_Project.NodeID_Session)
        
    def SessionPathToName(self, path = None):
        if path is None:
            return "Unnamed session"
        else:
            return str(Path(path).name)

    def IsValid(self):
        return self._CurrentPath is not None


    #-------------------------------------------------------
    def MakeSessionDir(self):
        guid = self.GetSessionNode().GetSessionGuid()
        return G_Global.MakeCacheDir(self._CurrentPath, guid)

    def CheckGuidCollision(self):
        # no session implies no collision
        if not self.IsValid():
            return

        # no sentinel file implies no collision; claim
        # Guid for this document and finish
        sentinel_filename = "sentinel.txt"
        file = self.MakeSessionDir() / sentinel_filename
        if not file.exists():
            file.write_text(self._CurrentPath)
            return

        # if Guid taken by another document; create new Guid
        # and claim it
        owning_path = file.read_text()
        if owning_path != self._CurrentPath:
            self.GetSessionNode().NewSessionGuid()
            (self.MakeSessionDir() / sentinel_filename).write_text(self._CurrentPath)


    #-------------------------------------------------------
    def SetSessionFilename(self, doc_path = None):
        """Set the current working directory to match the session file location"""

        self._CurrentPath = doc_path
        if doc_path is None:
            return

        # since the document contains relative paths to the logfiles, ensure
        # CWD is correct
        import os
        os.chdir(str(Path(doc_path).parent))


    #-------------------------------------------------------
    def SessionNew(self):
        self.SetSessionFilename()
        self.GetRootNode().LoadNode(self.SessionPathToName())
        self.GetSessionNode().Select()


    #-------------------------------------------------------
    def SessionOpen(self, path_or_idx):
        """Open the given session; if that fails, create a new session"""

        # set requested path to the top of the history list
        doc_path = self._ListTouch(path_or_idx)
        doc_path_object = Path(doc_path)

        if doc_path == "":
            logging.error("No document in 'Recent' list, creating new")
            self.SessionNew()
        
        # confirm the file exists
        elif not doc_path_object.parent.is_dir() or not doc_path_object.is_file():
            self.AppError("Document '{}' missing\nCreating new".format(doc_path))
            self.SessionNew()

        else:
            self.SetSessionFilename(doc_path)
            node = self.GetRootNode().LoadNode(self.SessionPathToName(doc_path), doc_path)

            if node is not None:
                self.GetSessionNode().Select()
            else:
                self.AppError("Document '{}' failed to load\nCreating new".format(doc_path))
                self.SessionNew()


    #-------------------------------------------------------
    def SessionReap(self):
        # best efforts at saving current file; will skip new sessions
        self.SessionSave(False)

        # take down the current session node; caller will need to make a new one
        self.GetSessionNode().OnCmdDelete()


    #-------------------------------------------------------
    def SessionSave(self, touch = True):
        if not self.IsValid():
            return

        if touch:
            self._ListTouch(self._CurrentPath)


        self.GetRootNode().SaveNode(self._CurrentPath)


    def SessionSaveAs(self, doc_path):
        self.SetSessionFilename(doc_path)
        self.SessionSave()


    #-------------------------------------------------------
    def SessionSetup(self, root_node, program_args):
        """Initialise the session manager; makes it operational"""

        self._WRootNode = MakeWeakRef(root_node)
        self._CurrentPath = None

        self.GetRootNode().WithFrameLocked(self._SessionSetup, program_args)

    def _SessionSetup(self, args):
        """Implement session startup; frame window is locked"""    

        path = args.session
        if path is not None:
            self.SessionOpen(path)
        elif args.recent:
            self.SessionOpen(0)
        else:
            self.SessionNew()

        logfile_descs = args.log
        if logfile_descs is None:
            return

        base_path = Path.cwd()
        schemata = dict(GetLogSchemataNames())

        for desc in logfile_descs:
            try:
                elems = desc.count('@')
                builder_name = None
                if elems == 2:
                    (path, schema_name) = desc.split('@')
                elif elems == 3:
                    (path, schema_name, builder_name) = desc.split('@')
                else:
                    logging.error("Unrecognised logfile descriptor: '{}'".format(desc))

                if schema_name not in schemata:
                    schemata_names = "".join(schemata.keys())
                    logging.error("Unrecognised schema in '{}'; valid schemata are: '{}'".format(desc, schemata_names))
                    return

                schema_guid = schemata[schema_name]
                builders = dict(GetLogSchema(schema_guid).GetBuildersNameGuidList())

                builder_guid = None
                if builder_name is not None:
                    if len(builders) == 0:
                        logging.error("Builder name included in logfile descriptor '{}', but schema defined no builders".format(builder_name))
                        return

                    if builder_name in builders:
                        builder_guid = builders[builder_name]
                    else:
                        builder_names = "".join(builders.keys())
                        logging.error("Unrecognised builder in '{}'; valid builders are: '{}'".format(desc, builder_names))
                        return

                p = Path(path)
                if p.is_absolute():
                    p = G_Global.RelPath(p, base_path).as_posix()

                self.GetSessionNode().AppendLog(str(p), builder_guid)

            except ValueError:
                logging.error("No schema in log descriptor '{}'; expected 'path@schema@builder' where valid schema names are: '{}'".format(desc, schemata_names))


    #-------------------------------------------------------
    def OnCmdSessionNew(self, event = None):
        def New():
            self.SessionReap()
            self.SessionNew()
            self.GetSessionNode().Select()

        self.GetRootNode().WithFrameLocked(New)


    #-------------------------------------------------------
    def OnCmdSessionOpen(self, event):
        ext = G_Shell.Extension()
        dlg = wx.FileDialog(
            self.GetRootNode().GetFrame(),
            message = "Open session",
            defaultDir = str(Path.cwd()),
            wildcard = "Session files (*{})|*{}".format(ext, ext),
            style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
        )

        path = None
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()

        dlg.Destroy()

        if path is not None:
            def Open(path):
                self.SessionReap()
                self.SessionOpen(path)

            self.GetRootNode().WithFrameLocked(Open, path)


    #-------------------------------------------------------
    def OnCmdSessionRecent(self, idx):
        def Recent(idx):
            self.SessionReap()
            self.SessionOpen(idx)

        self.GetRootNode().WithFrameLocked(Recent, idx)


    #-------------------------------------------------------
    def OnCmdSessionSave(self, event = None):
        from .MatchNode import GetHistoryManager
        GetHistoryManager().Save()

        if self.IsValid():
            self.SessionSave()
        else:
            self.OnCmdSessionSaveAs()


    #-------------------------------------------------------
    def OnCmdSessionSaveAs(self, event = None):
        name = None

        base_path = Path.cwd()
        ext = G_Shell.Extension()
        dlg = wx.FileDialog(
            self.GetRootNode().GetFrame(),
            message = "Save session",
            defaultDir = str(base_path),
            wildcard = "Session files (*{})|*{}".format(ext, ext),
            style = wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
        )

        new_path = None
        if dlg.ShowModal() == wx.ID_OK:
            new_path = dlg.GetPath()

        dlg.Destroy()

        if new_path is not None:
            self.SessionSaveAs(new_path)

            # flush any new name into the GUI
            self.GetSessionNode().SetTreeLabel(str(Path(new_path).name))


    #-------------------------------------------------------
    def OnDropFiles(self, files):
        if len(files) > 1:
            return False

        def Open(path):
            self.SessionReap()
            self.SessionOpen(path)

        self.GetRootNode().WithFrameLocked(Open, files[0])

        return True



## G_SessionChildNode ######################################

class G_SessionChildNode(G_DataExplorerChildNode):
    """Mixin class to extend child nodes of a session node with common behaviour"""

    #-------------------------------------------------------
    def GetSessionNode(self):
        return self.GetParentNode(G_Project.NodeID_Session)



## G_SessionManagerNode ####################################

class G_SessionManagerNode(G_SessionChildNode, G_TabContainedNode):
    """
    Interface to the Session Manager
    """

    #-------------------------------------------------------
    _HistoryLen = 30


    #-------------------------------------------------------
    def BuildPage(parent):
        # class static function
        me = __class__
        me._Sizer = parent.GetSizer()

        window = parent.GetWindow()
        me._BtnSessionNew = wx.Button(window, label = "New", size = G_Const.ButtonSize)
        me.BuildLabelledRow(parent, "Create new session:", me._BtnSessionNew)

        me._BtnSessionOpen = wx.Button(window, label = "Open ...", size = G_Const.ButtonSize)
        me.BuildLabelledRow(parent, "Open existing session:", me._BtnSessionOpen)

        me._BtnSessionSaveAs = wx.Button(window, label = "Save As ...", size = G_Const.ButtonSize)
        me.BuildLabelledRow(parent, "Save session as:", me._BtnSessionSaveAs)

        me._BtnSessionSave = wx.Button(window, label = "Save", size = G_Const.ButtonSize)
        me.BuildLabelledRow(parent, "Save session:", me._BtnSessionSave)

        me.BuildSubtitle(parent, "Recent sessions:")
        me._ListRecent = wx.ListBox(window, size = (-1, 2 * G_Const.ListBoxH), style = wx.LB_SINGLE | wx.LB_HSCROLL)
        me._Sizer.Add(me._ListRecent, proportion = 1, flag = wx.ALL | wx.EXPAND, border = G_Const.Sizer_StdBorder, userData = "SessionManagerNode-list-recent-sessions")

        me._BtnSessionRecent = wx.Button(window, label = "Recent", size = G_Const.ButtonSize)
        me.BuildLabelledRow(parent, "Open recent session:", me._BtnSessionRecent)


    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem, name, **kwargs):
        G_TabContainedNode.__init__(self, factory, wproject, witem)


    #-------------------------------------------------------
    def Activate(self):
        self.SetNodeHelp("Open Session", "session.html", "opensession")
        self.Rebind(self._BtnSessionNew, wx.EVT_BUTTON, GetSessionManager().OnCmdSessionNew)
        self.Rebind(self._BtnSessionOpen, wx.EVT_BUTTON, GetSessionManager().OnCmdSessionOpen)
        self.Rebind(self._BtnSessionSave, wx.EVT_BUTTON, GetSessionManager().OnCmdSessionSave)
        self.Rebind(self._BtnSessionSaveAs, wx.EVT_BUTTON, GetSessionManager().OnCmdSessionSaveAs)

        recent = self._ListRecent
        recent.Unbind(wx.EVT_LISTBOX_DCLICK)
        recent.Unbind(wx.EVT_LISTBOX)
        recent.Clear()

        for r in GetSessionManager().GetRecent():
            recent.Append(r)

        recent.Bind(wx.EVT_LISTBOX_DCLICK, self.OnCmdSessionRecent)
        recent.Bind(wx.EVT_LISTBOX, self.OnSessionRecentList)

        self.Rebind(self._BtnSessionRecent, wx.EVT_BUTTON, self.OnCmdSessionRecent)
        self._BtnSessionRecent.Enable(False)


    #-------------------------------------------------------
    def OnSessionRecentList(self, event):
        have_selection = self._ListRecent.GetSelection() != wx.NOT_FOUND
        self._BtnSessionRecent.Enable(have_selection)
        

    #-------------------------------------------------------
    def OnCmdSessionRecent(self, event):
        selection = self._ListRecent.GetSelection()
        if selection != wx.NOT_FOUND:
            GetSessionManager().OnCmdSessionRecent(selection)



## G_OpenLogNode ###########################################

class G_OpenLogNode(G_SessionChildNode, G_TabContainedNode):
    """Node to provide UI interface for opening logfiles"""

    #-------------------------------------------------------
    def BuildPage(parent):
        # class static function
        me = __class__
        me._Sizer = parent.GetSizer()

        # add log schema label, chooser and description
        window = parent.GetWindow()
        me._SchemataNames = GetLogSchemataNames()
        names = [name[0] for name in me._SchemataNames]
        me._ChoiceLogSchema = wx.Choice(window, size = (-1, G_Const.ComboRowHeight), choices = names)
        me.BuildLabelledRow(parent, "Log file schema:", me._ChoiceLogSchema)
        me._TxtLogSchema = wx.TextCtrl(window, style = wx.TE_READONLY | wx.TE_MULTILINE)
        me._Sizer.Add(me._TxtLogSchema, proportion = 1, flag = wx.BOTTOM | wx.LEFT | wx.RIGHT | wx.EXPAND, border = G_Const.Sizer_StdBorder, userData = "OpenNode-schema")

        me._ChoiceLogBuilder = wx.Choice(window, size = (-1, G_Const.ComboRowHeight))
        me.BuildLabelledRow(parent, "Log builder:", me._ChoiceLogBuilder)
        me._TxtLogBuilder = wx.TextCtrl(window, style = wx.TE_READONLY | wx.TE_MULTILINE)
        me._Sizer.Add(me._TxtLogBuilder, proportion = 1, flag = wx.BOTTOM | wx.LEFT | wx.RIGHT | wx.EXPAND, border = G_Const.Sizer_StdBorder, userData = "OpenNode-builder")

        # Open button is last ...
        me._BtnOpenLogfile = wx.Button(window, label = "Open ...", size = G_Const.ButtonSize)
        me.BuildLabelledRow(parent, "Open a logfile:", me._BtnOpenLogfile)


    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem, name, **kwargs):
        G_TabContainedNode.__init__(self, factory, wproject, witem)

    def PostInitNode(self):
        # make document fields accessible
        self._Field = D_Document(self.GetDocument(), self)


    #-------------------------------------------------------
    def Activate(self):
        self.SetNodeHelp("Open Log", "session.html", "openlog")
        self.Rebind(self._BtnOpenLogfile, wx.EVT_BUTTON, self.OnCmdOpenLogfile)

        guid = self._Field.SchemaGuid.Value
        if guid == "None" and len(self._SchemataNames) != 0:
            guid = self._Field.SchemaGuid.Value = self._SchemataNames[0][1]

        idx = 0
        for name in self._SchemataNames:
            if name[1] == guid:
                break
            idx = idx + 1

        cm = self._ChoiceLogSchema
        self.Rebind(cm, wx.EVT_CHOICE, self.OnChoiceLogSchema)
        cm.SetSelection(idx)
        self.OnChoiceLogSchema()

        self.Rebind(self._BtnOpenLogfile, wx.EVT_BUTTON, self.OnCmdOpenLogfile)


    #-------------------------------------------------------
    def GetLogSchemaGuid(self):
        return self._Field.SchemaGuid.Value

    def GetLogSchema(self):
        return GetLogSchema(self.GetLogSchemaGuid())


    #-------------------------------------------------------
    def OnCmdOpenLogfile(self, event):
        schema = self.GetLogSchema()
        schema_name = schema.GetName()
        ext = schema.GetExtension()
        wildcard = "{} log files (*.{})|*.{}|All files (*.*)|*.*".format(schema_name, ext, ext)

        dlg = wx.FileDialog(
            self.GetProject().GetFrame(),
            message = "Select {} log file(s)".format(schema_name),
            defaultDir = str(Path.cwd()),
            wildcard = wildcard,
            style = wx.FD_OPEN | wx.FD_MULTIPLE | wx.FD_FILE_MUST_EXIST
        )

        # maintenance warning: Python errors seem to be eaten while
        # the dialog is open, so do as little work here as possible
        paths = []
        if dlg.ShowModal() == wx.ID_OK:
            paths = dlg.GetPaths()

        dlg.Destroy()

        for path in paths:
            builder_guid = None
            if len(self._BuilderNames) != 0:
                builder_guid = self._BuilderNames[self._ChoiceLogBuilder.GetSelection()][1]

            relative_path = str(G_Global.RelPath(path).as_posix())
            self.GetSessionNode().AppendLog(relative_path, self.GetLogSchemaGuid(), builder_guid)



    #-------------------------------------------------------
    def OnChoiceLogBuilder(self, event = None):
        guid = self._BuilderNames[self._ChoiceLogBuilder.GetSelection()][1]
        builder = self.GetLogSchema().GetBuilders().GetObjectByGuid(guid)

        theme_id = builder.GetLogTheme()
        desc = "Log theme: {}".format(GetThemeGallery("log").GetThemeName(theme_id))

        for (factory, theme_cls, view_theme_id) in builder.GetViewThemes():
            theme_cls_name = theme_cls[0].upper() + theme_cls[1:]
            desc += "\n{} theme: {}".format(theme_cls_name, GetThemeGallery(theme_cls).GetThemeName(view_theme_id))

        self.SetLogBuilderText(desc)

    def SetLogBuilderText(self, desc = ""):
        self._TxtLogBuilder.SetValue(desc)


    #-------------------------------------------------------
    def OnChoiceLogSchema(self, event = None):
        guid = self._SchemataNames[self._ChoiceLogSchema.GetSelection()][1]
        self._Field.SchemaGuid.Value = guid
        schema = self.GetLogSchema()

        desc = schema.GetUserDescription()
        self._TxtLogSchema.SetValue(desc)

        choice_builder = self._ChoiceLogBuilder
        self.Rebind(choice_builder, wx.EVT_CHOICE, self.OnChoiceLogBuilder)
        builders = self._BuilderNames = schema.GetBuildersNameGuidList()

        if len(builders) == 0:
            choice_builder.Clear()
            self.SetLogBuilderText()
        else:
            choice_builder.Set([name[0] for name in builders])
            choice_builder.SetSelection(0)
            self.OnChoiceLogBuilder()



## G_SessionTrackerOptionsNode #############################

c_Thousand = 1000
c_Million = c_Thousand * c_Thousand
c_Billion = c_Thousand * c_Million

class G_SessionTrackerOptionsNode(G_SessionChildNode, G_TabContainedNode):
    """Node to provide UI interface for overall tracker and delta options"""

    #-------------------------------------------------------
    _DeltaFormat = "s.f"

    _LocalTrackerFormats = [
        ["ddd dd mmm yyyy hh:mm::ss.f", "%a %d %b %Y %H:%M:%S"],
        ["dd mmm yyyy hh:mm::ss.f", "%d %b %Y %H:%M:%S"],
        ["dd/mm/yy hh:mm::ss.f", "%d/%m/%y %H:%M:%S"],
        ["dd/mm hh:mm::ss.f", "%d/%m %H:%M:%S"],
        ["dd hh:mm::ss.f", "%d %H:%M:%S"],
        ["hh:mm::ss.f", "%H:%M:%S"],
        [_DeltaFormat, None]
    ]

    _GlobalTrackerFormats = [
        ["ddd dd mmm yyyy hh:mm::ss.f", "%a %d %b %Y %H:%M:%S"],
        ["dd mmm yyyy hh:mm::ss.f", "%d %b %Y %H:%M:%S"],
        ["dd/mm/yy hh:mm::ss.f", "%d/%m/%y %H:%M:%S"],
        ["dd/mm hh:mm::ss.f", "%d/%m %H:%M:%S"],
        ["dd hh:mm::ss.f", "%d %H:%M:%S"],
        ["hh:mm::ss.f", "%H:%M:%S"]
    ]

    def NoFrac(offset_ns):
        return ""

    def MsecDotNsec(offset_ns):
        msec = int(offset_ns / c_Million)
        nsec = offset_ns - (msec * c_Million)
        return ".{:0=3d}.{:0=6d}".format(msec, nsec)

    def Usec(offset_ns):
        usec = int(offset_ns / c_Thousand)
        return ".{:0=6d}".format(usec)

    def Msec(offset_ns):
        msec = int(offset_ns / c_Million)
        return ".{:0=3d}".format(msec)

    _Precision = [
        ["msec.nsec", MsecDotNsec],
        ["usec", Usec],
        ["msec", Msec],
        ["sec", NoFrac]
    ]


    #-------------------------------------------------------
    class Info:
        """Shared timecode to text support"""

        @staticmethod
        def OffsetToText(offset_ns, precision):
            # note: the offset_ns can be negative
            sec = int(offset_ns / c_Billion)
            remainder = abs(offset_ns - (sec * c_Billion))
            frac = precision(remainder)
            return "{}".format(sec) + frac

        @staticmethod
        def TimecodeToText(timecode, format, precision):
            if timecode is None:
                return "-"

            elif format is None:
                offset_ns = timecode.GetOffsetNs()
                return __class__.OffsetToText(offset_ns, precision)

            else:
                # normalise the datum/offset to usable UTC values
                timecode.Normalise()
                offset_ns = timecode.GetOffsetNs()

                # convert to text
                date = time.strftime(format, time.gmtime(timecode.GetUtcDatum()))
                frac = precision(offset_ns)
                return date + frac


    #-------------------------------------------------------
    class TrackerInfo(Info):
        def __init__(self, display_ctrl, format_precsion):
            self.DisplayCtrl = display_ctrl
            self.Timecode = None
            self.FormatPrecision = format_precsion

        def Display(self):
            (format, precision) = self.FormatPrecision()
            text = self.TimecodeToText(self.Timecode, format, precision)
            self.DisplayCtrl.SetLabel(text)


    #-------------------------------------------------------
    class DeltaOption:
        """Keep track of the time difference a delta measures"""

        def __init__(self, fm_name = None, to_name = None, fm_idx = None, to_idx = None):
            desc = "Unused"
            if fm_name is not None:
                desc = "{} .. {}".format(fm_name.split(" ")[1], to_name.split(" ")[1])

            self.Description = desc
            self.From = fm_idx
            self.To = to_idx
            

    _DeltaOptions = []

    @staticmethod
    def InitDeltaOptions():
        """Build a list of delta options a user can choose amongst"""

        me = __class__

        to = G_Const.LocalTrackerName
        for idxf, fm in enumerate(G_Const.GlobalTrackerNames):
            me._DeltaOptions.append(me.DeltaOption(fm, to, 1 + idxf, 0))

        fm = G_Const.LocalTrackerName
        for idxt, to in enumerate(G_Const.GlobalTrackerNames):
            me._DeltaOptions.append(me.DeltaOption(fm, to, 0, 1 + idxt))

        for idxf, fm in enumerate(G_Const.GlobalTrackerNames):
            for idxt, to in enumerate(G_Const.GlobalTrackerNames[idxf+1:]):
                me._DeltaOptions.append(me.DeltaOption(fm, to, 1 + idxf, 1 + idxf + 1 + idxt))

        me._DeltaOptions.append(me.DeltaOption())

            
    #-------------------------------------------------------
    class DeltaInfo(Info):
        def __init__(self, label_ctrl, display_ctrl, display_id, option_precision):
            self.LabelCtrl = label_ctrl
            self.DisplayCtrl = display_ctrl
            self._DisplayId = display_id
            self.OptionPrecision = option_precision

        def Display(self, tracker_infos):
            (desc, fm, to, precision) = self.OptionPrecision(self._DisplayId)

            value = "-"
            if desc == "Unused":
                desc = value = ""

            elif to.Timecode is not None and fm.Timecode is not None:
                offset_ns = to.Timecode.Subtract(fm.Timecode)
                value = self.OffsetToText(offset_ns, precision)
            
            self.LabelCtrl.SetLabel(desc)
            self.DisplayCtrl.SetLabel(value)


    #-------------------------------------------------------
    _NumDeltaDisplays = 4

    def BuildPage(parent):
        # class static function
        me = __class__
        me._Sizer = parent.GetSizer()

        # add log schema label, chooser and description
        window = parent.GetWindow()

        local_formats = [item[0] for item in me._LocalTrackerFormats]
        global_formats = [item[0] for item in me._GlobalTrackerFormats]
        precision = [item[0] for item in me._Precision]

        me.BuildSubtitle(parent, "Tracker display format", True)
        me._LocalTrackerFormatCtl = wx.Choice(window)
        me._LocalTrackerFormatCtl.Set(local_formats)
        me.BuildLabelledRow(parent, "Local Tracker", me._LocalTrackerFormatCtl)

        me._GlobalTrackerFormatCtl = wx.Choice(window)
        me._GlobalTrackerFormatCtl.Set(global_formats)
        me.BuildLabelledRow(parent, "Global Trackers", me._GlobalTrackerFormatCtl)

        me.InitDeltaOptions()

        descs = [opt.Description for opt in me._DeltaOptions]
        me._DeltaDisplayCtls = [wx.Choice(window, choices = descs) for i in range(me._NumDeltaDisplays)]

        me.BuildSubtitle(parent, "Time delta displays", True)
        for i, ctl in enumerate(me._DeltaDisplayCtls):
            me.BuildLabelledRow(parent, "Delta {}".format(i), ctl)

        me.BuildSubtitle(parent, "Time display", True)
        me._PrecisionCtl = wx.Choice(window)
        me._PrecisionCtl.Set(precision)
        me.BuildLabelledRow(parent, "Precision", me._PrecisionCtl)


    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem, name, **kwargs):
        G_TabContainedNode.__init__(self, factory, wproject, witem)

    def PostInitNode(self):
        # make document fields accessible
        self._Field = D_Document(self.GetDocument(), self)

        # (re-)build display panels
        self.BuildTrackerPanel()
        self.BuildDeltasPanel()

        # ensure global tracker persistence data exists
        class TrackerTimecodeTemplate(D_Document.D_Value):
            def __init__(self):
                self.InUse = False
                self.UtcDatum = 0
                self.OffsetNs = 0

        self._GlobalTrackerTimecodes = self._Field.Add([], "GlobalTrackerTimecodes", replace_existing = False)
        if len(self._GlobalTrackerTimecodes) == 0:
            for i in range(G_Const.NumGlobalTrackers):
                self._GlobalTrackerTimecodes.Add(TrackerTimecodeTemplate())


    def PostInitLoad(self):
        # apply any persisted tracker data into Nlog; themes are setup now
        timecodes = []

        for i in range(G_Const.NumGlobalTrackers):
            tracker = self._GlobalTrackerTimecodes[i]
            if tracker.InUse.Value:
                timecodes.append(Nlog.Timecode(tracker.UtcDatum.Value, tracker.OffsetNs.Value))

        self.SetTrackers(False, 0, timecodes)


    #-------------------------------------------------------
    def AddPage(self, page_name, at_idx):
        info_panel = self.GetFrame().GetInfoPanel()

# bodge - get rid of it
        for page in range(info_panel.GetPageCount()):
            if info_panel.GetPageText(page) == page_name:
                info_panel.DeletePage(page)
                break

        page = G_WindowInfo.MakePane(info_panel)
        info_panel.InsertPage(at_idx, page.GetWindow(), page_name)
        return page


    def BuildTrackerPanel(self):
        self._Trackers = []

        tracker_panel = self._TrackerPanel = self.AddPage("Trackers", 0)

        label = wx.StaticText(tracker_panel.GetWindow(), label = "#")
        self.BuildLabelledRow(tracker_panel, G_Const.LocalTrackerName, label)
        self._Trackers.append(self.TrackerInfo(label, self.GetLocalFormatPrecision))

        for name in G_Const.GlobalTrackerNames:
            label = wx.StaticText(tracker_panel.GetWindow(), label = "#")
            self.BuildLabelledRow(tracker_panel, name, label, flag = wx.LEFT | wx.RIGHT)
            self._Trackers.append(self.TrackerInfo(label, self.GetGlobalFormatPrecision))


    def BuildDeltasPanel(self):
        self._Deltas = []

        deltas_panel = self._DeltasPanel = self.AddPage("Deltas", 1)

        for display_id in range(self._NumDeltaDisplays):
            label = wx.StaticText(deltas_panel.GetWindow(), label = "#")
            value = wx.StaticText(deltas_panel.GetWindow(), label = "-")
            self._Deltas.append(self.DeltaInfo(label, value, display_id, self.GetDeltaOptionPrecision))
            self.BuildRow(deltas_panel, label, value, "delta_{}".format(display_id), flag = wx.LEFT | wx.RIGHT)


    #-------------------------------------------------------
    def Activate(self):
        self.SetNodeHelp("Open Log", "session.html", "openlog")

        self.Rebind(self._LocalTrackerFormatCtl, wx.EVT_CHOICE, self.OnLocalTrackerFormat)
        self._LocalTrackerFormatCtl.SetSelection(self._Field.LocalTrackerFormatIdx.Value)

        self.Rebind(self._GlobalTrackerFormatCtl, wx.EVT_CHOICE, self.OnGlobalTrackerFormat)
        self._GlobalTrackerFormatCtl.SetSelection(self._Field.GlobalTrackerFormatIdx.Value)

        delta_displays_idx = self._Field.DeltaDisplaysIdx.Value
        for i, ctl in enumerate(self._DeltaDisplayCtls):
            self.Rebind(ctl, wx.EVT_CHOICE, self.OnDeltaDisplayCtl)
            ctl.SetSelection(delta_displays_idx[i])

        self.Rebind(self._PrecisionCtl, wx.EVT_CHOICE, self.OnPrecision)
        self._PrecisionCtl.SetSelection(self._Field.PrecisionIdx.Value)


    #-------------------------------------------------------
    def GetPrecision(self):
        return self._Precision[self._Field.PrecisionIdx.Value][1]

    def GetLocalFormatPrecision(self):
        return (self._LocalTrackerFormats[self._Field.LocalTrackerFormatIdx.Value][1],
            self.GetPrecision())

    def GetGlobalFormatPrecision(self):
        return (self._GlobalTrackerFormats[self._Field.GlobalTrackerFormatIdx.Value][1],
            self.GetPrecision())

    def GetDeltaOptionPrecision(self, display_id):
        delta_displays_idx = self._Field.DeltaDisplaysIdx.Value
        option = self._DeltaOptions[delta_displays_idx[display_id]]
        
        fm = to = None
        if option.From is not None:
            fm = self._Trackers[option.From]
        if option.To is not None:
            to = self._Trackers[option.To]

        return (option.Description, fm, to, self.GetPrecision())


    #-------------------------------------------------------
    def OnLocalTrackerFormat(self, evt):
        self._Field.LocalTrackerFormatIdx.Value = self._LocalTrackerFormatCtl.GetSelection()
        self.UpdateTrackerPanel()

    def OnGlobalTrackerFormat(self, evt):
        self._Field.GlobalTrackerFormatIdx.Value = self._GlobalTrackerFormatCtl.GetSelection()
        self.UpdateTrackerPanel()

    def OnDeltaDisplayCtl(self, evt):
        delta_displays_idx = [ctl.GetSelection() for ctl in self._DeltaDisplayCtls]
        self._Field.DeltaDisplaysIdx.Value = delta_displays_idx
        self.UpdateDeltasPanel()
        
    def OnPrecision(self, evt):
        self._Field.PrecisionIdx.Value = self._PrecisionCtl.GetSelection()
        self.UpdateTrackerPanel()
        self.UpdateDeltasPanel()


    #-------------------------------------------------------
    def UpdateTrackerPanel(self):
        for tracker in self._Trackers:
            tracker.Display()
            
        self._TrackerPanel.GetSizer().Layout()


    def UpdateDeltasPanel(self):
        for delta in self._Deltas:
            delta.Display(self._Trackers)
            
        self._DeltasPanel.GetSizer().Layout()


    #-------------------------------------------------------
    def SetTrackers(self, update_local, update_global_idx, timecodes):
        if update_local:
            assert(len(timecodes) == 1)
            self._Trackers[0].Timecode = timecodes[0]

        if update_global_idx >= 0:
            for (idx, timecode) in enumerate(timecodes):
                Nlog.SetGlobalTracker(update_global_idx + idx, timecode)
                self._Trackers[1+update_global_idx+idx].Timecode = timecode

        self.UpdateTrackerPanel()
        self.UpdateDeltasPanel()


    #-------------------------------------------------------
    def UpdateTrackers(self, update_local, update_global_idx, timecodes):
        if update_global_idx >= 0:
            # record the new global tracker timecodes in the document
            for (idx, timecode) in enumerate(timecodes):
                tracker = self._GlobalTrackerTimecodes[update_global_idx + idx]
                tracker.InUse.Value = True
                tracker.UtcDatum.Value = timecode.GetUtcDatum()
                tracker.OffsetNs.Value = timecode.GetOffsetNs()

        self.SetTrackers(update_local, update_global_idx, timecodes)




## G_GlobalThemeGalleryNode ################################

class G_GlobalThemeGalleryNode(G_SessionChildNode, G_ThemeGalleryNode, G_TabContainedNode):
    """Theme manager interface"""

    #-------------------------------------------------------
    def BuildPage(parent):
        # class static function
        me = __class__
        me._Sizer = parent.GetSizer()

        G_ThemeGalleryNode.BuildGallery(me, parent, "navigation")


    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem, name, **kwargs):
        G_TabContainedNode.__init__(self, factory, wproject, witem)
        G_ThemeGalleryNode.__init__(self, G_Const.GlobalThemeCls)

    def PostInitNode(self):
        # make document fields accessible
        self._Field = D_Document(self.GetDocument(), self)

        # ensure the current theme is setup
        self.PostInitThemeGallery()


    #-------------------------------------------------------
    def Activate(self):
        self.SetNodeHelp("Themes", "session.html", "themes")
        self.ActivateThemeGallery()



## G_SessionNode ##########################################

class G_SessionNode(G_TabContainerNode):
    """
    Parent session node
    """

    #-------------------------------------------------------
    def __init__(self, factory, wproject, witem, name, **kwargs):
        super().__init__(factory, wproject, witem)
        self._DatabaseManager = None

        # allow perspective saving to be disabled; AUI notebooks can
        # and do become corrupted
        self._StoreManagerPerspective = True
        self._StoreNotebookPerspective = True

        G_DataExplorer.Instance(self.GetFrame()).ClearHistory()



    def PostInitNode(self):
        # make document fields accessible
        self._Field = D_Document(self.GetDocument(), self)
        self._Field.Add(str(uuid4()), "Guid", replace_existing = False)
        self._Field.Add(1, "EventId", replace_existing = False)

            
    def PostInitLoad(self):
        # control/restore window layout; this should be last, as the
        # UI changes can result in tab window focus changes, which drives
        # node selection events into the project - clearly, the project
        # must be fully setup in order to handle the events correctly
        try:
            self._Field.Add("", "AuiManager2", replace_existing = False)
            layout = self._Field.AuiManager2.Value
            if len(layout) != 0:
                self.GetAuiManager().LoadPerspective(layout, update=False)

        except IndexError:
            logging.error("Unable to load AUI manager perspective")
            self._StoreManagerPerspective = False

        try:
            self._Field.Add("", "AuiNotebook", replace_existing = False)
            layout = self._Field.AuiNotebook.Value
            if len(layout) != 0:
                self.GetAuiNotebook().LoadPerspective(layout)

        except IndexError:
            logging.error("Unable to load AUI notebook perspective")
            self._StoreNotebookPerspective = False

        self._Field.Add("", "Project", replace_existing = False)
        layout = self._Field.Project.Value
        if len(layout) == 0:
            self.GetProject().DefaultPerspective()
        else:
            self.GetProject().LoadPerspective(layout)

        # backwards compatibility; make sure the data explorer is shown
        self.GetAuiManager().ShowPane(self.GetFrame().GetDataExplorer(), True)

        self.CheckGuidCollision()


    #-------------------------------------------------------
    def GetDataExplorer(self):
        return G_DataExplorer.Instance()


    #-------------------------------------------------------
    def GetSessionGuid(self):
        return self._Field.Guid.Value

    def NewSessionGuid(self):
        self._Field.Guid.Value = str(uuid4())


    #-------------------------------------------------------
    def GetEventId(self):
        return self._Field.EventId.Value

    def UpdateEventId(self, event_id):
        self._Field.EventId.Value = event_id


    #-------------------------------------------------------
    def AppendLog(self, relative_path, schema_guid, builder_guid):
        self.BuildNodeFromDefaults(G_Project.NodeID_Log, relative_path, schema_guid = schema_guid, builder_guid = builder_guid)


    #-------------------------------------------------------
    def Activate(self):
        self.ActivateContainer()


    #-------------------------------------------------------
    def CreatePopupMenu(self, handlers):
        manager = GetSessionManager()
        menu = wx.Menu("Session")

        menu.Append(G_Const.ID_SESSION_SAVE, "Save")
        handlers[G_Const.ID_SESSION_SAVE] = manager.OnCmdSessionSave

        menu.Append(G_Const.ID_SESSION_SAVE_AS, "Save As ...")
        handlers[G_Const.ID_SESSION_SAVE_AS] = manager.OnCmdSessionSaveAs

        return menu


    #-------------------------------------------------------
    def NotifyPreSave(self):
        """A save has been requested; perform any tasks that must be completed before the save takes place"""
        self.CheckGuidCollision()

        layout = ""
        if self._StoreManagerPerspective:
            layout = self.GetAuiManager().SavePerspective()
        self._Field.AuiManager2.Value = layout

        layout = ""
        if self._StoreNotebookPerspective:
            layout = self.GetAuiNotebook().SavePerspective()
        self._Field.AuiNotebook.Value = layout

        self._Field.Project.Value = self.GetProject().SavePerspective()


    #-------------------------------------------------------
    def CheckGuidCollision(self):
        GetSessionManager().CheckGuidCollision()

    def IsValid(self):
        return GetSessionManager().IsValid()



## MODULE ##################################################

G_Project.RegisterNodeFactory(
    G_NodeFactory(G_Project.NodeID_SessionManager, G_Project.ArtCtrlId_Session, G_SessionManagerNode)
)

G_Project.RegisterNodeFactory(
    G_NodeFactory(G_Project.NodeID_OpenLog, G_Project.ArtCtrlId_Open, G_OpenLogNode)
)

G_Project.RegisterNodeFactory(
    G_NodeFactory(G_Project.NodeID_SessionTrackerOptions, G_Project.ArtCtrlId_Tracker, G_SessionTrackerOptionsNode)
)

G_Project.RegisterNodeFactory(
    G_NodeFactory(G_Project.NodeID_GlobalThemeGallery, G_Project.ArtCtrlId_Theme, G_GlobalThemeGalleryNode)
)

G_Project.RegisterNodeFactory(
    G_NodeFactory(G_Project.NodeID_Session, G_Project.ArtDocID_Home, G_SessionNode)
)

_SessionManager = G_SessionManager()
def GetSessionManager():
    return _SessionManager
