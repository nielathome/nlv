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
import base64
import html
import json
import io
from pathlib import Path
from urllib.parse import urlparse

# wxWidgets imports
import wx
import wx.html2

# Application imports
from .Global import G_Const
from .Global import G_Global



## URL #####################################################

_TimeBase = 1


def _MakeLocation(node_id, **kwargs):
    global _TimeBase
    _TimeBase += 1

    return dict(
        kwargs,
        timebase = _TimeBase,
        node_id = node_id
    )


def _DataUrlToLocation(data_url):
    b64_bytes = base64.urlsafe_b64decode(data_url[:-5])
    data = json.loads(b64_bytes.decode())
    return data


def _LocationToDataUrl(location):
    data_bytes = json.dumps(location).encode('utf-8')
    b64_bytes = base64.urlsafe_b64encode(data_bytes)
    res = b64_bytes.decode()
    return res + ".html"


def _MakeWebUrl(data_url):
    return "http://localhost:8000/{}".format(data_url)



## G_DataExplorerPageCache #################################

class G_DataExplorerPageCache:
    _MaxHistory = 5


    #-------------------------------------------------------
    def __init__(self):
        # ordered list of keys, first entry is oldest, last is newest
        self._MRU = []


    #-------------------------------------------------------
    def Clear(self):
        for key in self._MRU:
            G_Global.MakeTempPath(key).unlink()

        self._MRU.clear()


    #-------------------------------------------------------
    def Remove(self, key):
        G_Global.MakeTempPath(key).unlink()
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

        with open(str(G_Global.MakeTempPath(key)), 'w') as file:
            file.write(data)

        self.Prune()
    


## G_DataExplorerPageBuilder ###############################

class G_DataExplorerPageBuilder:
    """Support building pages to display in the data explorer"""

    #-------------------------------------------------------
    def __init__(self, data_explorer):
        self._DataExplorer = data_explorer

        self._HeaderHtmlStream = io.StringIO()
        self.AddHeaderText("""
            <!DOCTYPE html>
            <head>
                <link rel="stylesheet" type="text/css" href="http:style.css">
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
        self.AddBodyText('<p><a href="{web_url}">{text}</a></p>'.format(web_url = _MakeWebUrl(data_url), text = html.escape(text)))


    #-------------------------------------------------------
    def MakeErrorPage(self, title, explanation, fields = []):
        self.AddPageHeading(title, "color:darkred")
        self.AddFieldValue(explanation)

        for name, value in fields:
            self.AddField(name, value)


    def MakeUnknownLocationErrorPage(self, fields):
        self.MakeErrorPage(
            "Unknown Location",
            "The view has been modified, and the location can no longer be found.",
            fields
        )


    def MakeHiddenLocationErrorPage(self, fields):
        self.MakeErrorPage(
            "Hidden Location",
            "The view has been modified, and the location is no longer visible.",
            fields
        )

 
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
        self._LastDataUrl = None

        parent = frame.GetDataExplorerPanel()

        # create web control
        self._WebView = wx.html2.WebView.New(parent)
        self._WebView.EnableHistory(True)
        self._WebView.EnableContextMenu(False)

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
        self._WebView.LoadURL(_MakeWebUrl(data_url))


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
        last_node = None
        if self._LastDataUrl is not None:
            last_location = _DataUrlToLocation(self._LastDataUrl)
            last_node = self.FindNode(last_location["node_id"])

        self._LastDataUrl = None
        web_url = event.GetURL()
        split = urlparse(web_url)
        scheme = split.scheme
        data_url = split.path.lstrip("/")

        if scheme != "http":
            if last_node is not None:
                last_node.DataExplorerUnload(last_location)

        else:    
            next_location = _DataUrlToLocation(data_url)
            next_node = self.FindNode(next_location["node_id"])
            page_builder = G_DataExplorerPageBuilder(self)

            if next_node is None:
                page_builder.MakeErrorPage("View not found", "The view cannot be found. It has probably been deleted.")

            else:
                if last_node is not None and last_location["node_id"] != next_location["node_id"]:
                    last_node.DataExplorerUnload(last_location)

                self._LastDataUrl = data_url
                next_node.DataExplorerLoad(page_builder, next_location)

            self._PageCache.Replace(data_url, page_builder.Close())



## G_DataExplorerProvider #################################

class G_DataExplorerProvider:

    #-------------------------------------------------------
    def SetNavigationValidityReason(self, reason):
        self._Validity = (self.GetNavigationValidTime(), reason)

    def SetNavigationValidity(self, reason = "Initialisation"):
        self._Validity = (_TimeBase, reason)


    #-------------------------------------------------------
    def GetNavigationValidTime(self):
        return self._Validity[0]

    def GetNavigationValidReason(self):
        return self._Validity[1]


    #-------------------------------------------------------
    def IsNavigationValid(self, builder, location, node_name):
        if location["timebase"] < self.GetNavigationValidTime():
            builder.MakeUnknownLocationErrorPage([
                ("Location", node_name),
                ("Reason", self.GetNavigationValidReason())
            ])
            return False
        else:
            return True



## G_DataExplorerChildNode #################################

class G_DataExplorerChildNode(G_DataExplorerProvider):
    """
    G_DataExplorer integration/support.
    """

    #-------------------------------------------------------
    def UpdateDataExplorer(self, **kwargs):
        data_explorer = self.GetSessionNode().GetDataExplorer()
        self._LastLocation = _MakeLocation(self.GetNodeId(), **kwargs)
        data_explorer.Update(_LocationToDataUrl(self._LastLocation))


    #-------------------------------------------------------
    def MakeDataUrl(self, **kwargs):
        location = _MakeLocation(self.GetNodeId(), **kwargs)
        return _LocationToDataUrl(location)


    #-------------------------------------------------------
    def SetupDataExplorer(self, on_load = None, on_unload = None):
        self._LastLocation = None
        self._DataExplorerLoad = on_load
        self._DataExplorerUnload = on_unload
        self.SetNavigationValidity("Initialisation")


    #-------------------------------------------------------
    def DataExplorerLoad(self, builder, location):
        sync = self._LastLocation != location
        self._LastLocation = None
        if self._DataExplorerLoad is not None:
            self._DataExplorerLoad(sync, builder, location)

    def DataExplorerUnload(self, location):
        if self._DataExplorerUnload is not None:
            self._DataExplorerUnload(location)
