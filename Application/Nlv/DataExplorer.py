#
# Copyright (C) Niel Clausen 2019-2020. All rights reserved.
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
from pathlib import Path

# wxWidgets imports
import wx
import wx.html2

# Application imports
from .Global import G_Const
from .Global import G_Global



## G_DataExplorerPageCache #################################

class G_DataExplorerPageCache:
    """
    Wrapper to maintain wx.MemoryFSHandler live entries.
    """

    _MaxHistory = 5


    #-------------------------------------------------------
    def __init__(self):
        # ordered list of keys, first entry is oldest, last is newest
        self._MRU = []


    #-------------------------------------------------------
    def Clear(self):
        for key in self._MRU:
            wx.MemoryFSHandler.RemoveFile(key)

        self._MRU.clear()


    #-------------------------------------------------------
    def Remove(self, key):
        wx.MemoryFSHandler.RemoveFile(key)
        self._MRU.remove(key)


    #-------------------------------------------------------
    def Prune(self):
        while len(self._MRU) > self._MaxHistory:
            self.Remove(self._MRU[0])


    #-------------------------------------------------------
    def Replace(self, key, data):
        if key in self._MRU:
            self.Remove(key)

        self._MRU.append(key)
        wx.MemoryFSHandler.AddFileWithMimeType(key, data, "text/html")
        self.Prune()
    


## G_DataExplorerPageBuilder ###############################

def MakeWebUrl(data_url):
    return "memory:" + data_url

class G_DataExplorerPageBuilder:
    """Support building pages to display in the data explorer"""

    #-------------------------------------------------------
    def __init__(self, data_explorer):
        self._DataExplorer = data_explorer

        self._HeaderHtmlStream = io.StringIO()
        self.AddHeaderText("""
            <!DOCTYPE html>
            <head>
                <link rel="stylesheet" type="text/css" href="memory:style.css">
        """)

        self._BodyHtmlStream = io.StringIO()
        self.AddBodyText("<body>")


    #-------------------------------------------------------
    def AddHeaderText(self, text):
        self._HeaderHtmlStream.write(text + "\n")

    def AddHeaderElement(self, tag, text):
        self.AddHeaderText("<{tag}>{text}</{tag}>".format(tag = tag, text = html.escape(text)))


    #-------------------------------------------------------
    def AddBodyText(self, text):
        self._BodyHtmlStream.write(text + "\n")

    def AddBodyElement(self, tag, text, style = None):
        if style is not None:
            style = ' style="{style}"'.format(style = style)
        else:
            style = ""

        self.AddBodyText("<{tag}{style}>{text}</{tag}>".format(tag = tag, style = style, text = html.escape(text)))


    #-------------------------------------------------------
    def AddPageHeading(self, text, style = None):
        self.AddBodyElement("h1", text, style)

    def AddFieldHeading(self, text, style = None):
        self.AddBodyElement("h2", text, style)

    def AddFieldValue(self, text, style = None):
        self.AddBodyElement("p", text, style)

    def AddField(self, heading, value, heading_style = None, value_style = None):
        self.AddFieldHeading(heading, heading_style)
        self.AddFieldValue(value, value_style)

    def AddLink(self, data_url, text):
        self.AddBodyText('<p><a href="{web_url}">{text}</a></p>'.format(web_url = MakeWebUrl(data_url), text = html.escape(text)))


    #-------------------------------------------------------
    def Close(self):
        self.AddBodyText("</body>")

        self.AddHeaderText("</head>")
        self.AddHeaderText(self._BodyHtmlStream.getvalue())
        self.AddHeaderText("</html>")

        return self._HeaderHtmlStream.getvalue()



## G_DataExplorer ##########################################

class G_DataExplorer:
    """Class that implements the project data explorer panel"""

    _DataExplorer = None

    _LocationSplit = "__at__"
    _PageSplit = "__page__"


    #-------------------------------------------------------
    @classmethod
    def SplitDataUrl(cls, url):
        # url is node-id<loc-split>location<page-split>page
        node_id, rem = url.split(cls._LocationSplit)
        location, page = rem.split(cls._PageSplit)

        return node_id, location, page


    @classmethod
    def MakeDataUrl(cls, node_id, location, page):
        return "{node_id}{loc_split}{location}{page_split}{page}".format(
            node_id = node_id,
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

        parent = frame.GetDataExplorerPanel()

        # create web control
        self._WebView = wx.html2.WebView.New(parent)
        self._WebView.EnableHistory(True)
        self._WebView.EnableContextMenu(False)

        # setup virtual filesystem: "memory:"
        wx.FileSystem.AddHandler(wx.MemoryFSHandler())
        self._WebView.RegisterHandler(wx.html2.WebViewFSHandler("memory"))

        # can't seem to access local files from HTML; so workaround
        with open(str(G_Global.GetInstallDir() / "data.css")) as css_file:
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
    def FindNode(self, node_id):
        root_node = self._Frame.GetProject().GetRootNode()
        return root_node.FindChildNode(node_id = int(node_id), recursive = True)


    #-------------------------------------------------------
    def ClearHistory(self):
        self._PageCache.Clear()
        self._WebView.ClearHistory()


    #-------------------------------------------------------
    def Update(self, data_url):
        self._WebView.LoadURL(MakeWebUrl(data_url))


    #-------------------------------------------------------
    def MakeErrorPage(self, title, text, data_url, field_name = None, field_value = None):
        builder = G_DataExplorerPageBuilder(self)
        builder.AddPageHeading(title, "color:darkred")
        builder.AddFieldValue(text)

        if field_name is not None:
            builder.AddField(field_name, field_value)

        node_id, location, page = self.SplitDataUrl(data_url)
        builder.AddField("ID", node_id)
        builder.AddField("Location", location)
        builder.AddField("Page", page)

        self._PageCache.Replace(data_url, builder.Close())


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
        scheme, data_url = web_url.split(':')
        if scheme != "memory":
            return

        node_id, location, page = self.SplitDataUrl(data_url)
        node = self.FindNode(node_id)
        if node is None:
            self.MakeErrorPage("View not found", "The view cannot be found. It has probably been deleted.", data_url)
            return

        page_builder = G_DataExplorerPageBuilder(self)
        node.DataExplorerNavigate(page_builder, location, page)
        self._PageCache.Replace(data_url, page_builder.Close())


        #ref_validity = node.GetDataExplorerProvider().GetDataValidity()
        #invalidity_reason, navigable = self._PageCache.Valid(data_url, ref_validity)
        #if invalidity_reason is not None:
        #    self.MakeErrorPage("Modified View", "The view has been modified, and has not been synchronised to the data explorer.", data_url, "Modification", invalidity_reason)
        #    return

        #if self._LastWebUrl != web_url and node.DataExplorerSync(location):
        #    node.MakeActive()
        #    self._LastWebUrl = web_url

       

## G_DataExplorerProvider #################################

class G_DataExplorerProvider:

    #-------------------------------------------------------
    def SetDataValidity(self, reason = "Initialisation"):
        self._Validity = (datetime.datetime.now(), reason)


    #-------------------------------------------------------
    def GetDataValidity(self):
        return self._Validity



## G_DataExplorerChildNode #################################

class G_DataExplorerChildNode:
    """
    G_DataExplorer integration/support.
    """

    #-------------------------------------------------------
    def UpdateDataExplorer(self, location = "any", page = "0"):
        self._LastLocation = location
        data_explorer = self.GetSessionNode().GetDataExplorer()
        data_explorer.Update(self.MakeDataUrl(location))


    #-------------------------------------------------------
    def MakeDataUrl(self, location = "any", page = "0"):
        return G_DataExplorer.MakeDataUrl(self.GetNodeId(), location, page)


    #-------------------------------------------------------
    def SetupDataExplorer(self, on_navigate):
        self._LastLocation = None
        self._DataExplorerNavigate = on_navigate
        self.SetDataExplorerValidity("Initialisation")

    #def GetDataExplorerProvider(self):
    #    if self._DataExplorerProvider is None:
    #        return self
    #    else:
    #        return self._DataExplorerProvider

    #def GetDataExplorerSync(self):
    #    if self._DataExplorerSync is None:
    #        return self
    #    else:
    #        return self._DataExplorerSync


    #-------------------------------------------------------
    def SetDataExplorerValidity(self, reason):
        return
#        self.GetDataExplorerProvider().SetDataValidity(reason)



    #-------------------------------------------------------
    def DataExplorerNavigate(self, builder, location, page):
        sync = self._LastLocation != location
        self._LastLocation = None
        if self._DataExplorerNavigate is not None:
            self._DataExplorerNavigate(sync, builder, location, page)

    #def DataExplorerSync(self, location):
    #    if self._DataExplorerSync is not None:
    #        self._DataExplorerSync(location)