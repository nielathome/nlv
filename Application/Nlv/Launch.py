#
# Copyright (C) Niel Clausen 2020. All rights reserved.
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
import wx.lib.agw.labelbook
from wx.lib.agw.fmresources import *



## G_FileDropTarget ########################################

class G_FileDropTarget(wx.FileDropTarget):

    #-------------------------------------------------------
    def __init__(self, handler):
        wx.FileDropTarget.__init__(self)
        self._Handler = handler


    #-------------------------------------------------------
    def OnDropFiles(self, x, y, files):
        return self._Handler(files)


## G_ActionStep ############################################

class G_ActionStep(wx.Panel):
    def __init__(self, parent):

        super().__init__(parent)
        self.SetBackgroundColour(wx.Colour(255,255,255))

        static = wx.StaticText(self, -1, "Label", pos=(10, 10))



## G_LaunchFrame ###########################################

class G_LaunchFrame(wx.Frame):

    #-------------------------------------------------------
    def __init__(self, parent, title):
        super().__init__(
            parent, -1, title,
            size = (970, 720),
            style = wx.DEFAULT_FRAME_STYLE
                | wx.NO_FULL_REPAINT_ON_RESIZE
        )

        frame_sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(frame_sizer)
        self.SetBackgroundColour(wx.Colour(255, 255, 255))

        border = 5
        dropper_sizer = wx.StaticBoxSizer(wx.VERTICAL, self, label = "File to launch")
        frame_sizer.Add(dropper_sizer, flag = wx.ALL | wx.EXPAND, border = border)

        path_ctrl = self._PathCtrl = wx.StaticText(dropper_sizer.GetStaticBox(), label = "Drop file here")
        path_ctrl.SetDropTarget(G_FileDropTarget(self.OnDropFiles))
        dropper_sizer.Add(path_ctrl, flag = wx.ALL | wx.EXPAND, border = border)

        action_sizer = wx.StaticBoxSizer(wx.VERTICAL, self, label = "Action")
        frame_sizer.Add(action_sizer, flag = wx.ALL | wx.EXPAND, border = border)
        action_ctrl = self._ActionCtrl = wx.StaticText(action_sizer.GetStaticBox(), label = "None")
        action_sizer.Add(action_ctrl, flag = wx.ALL | wx.EXPAND, border = border)

        book = self._LabelBook = wx.lib.agw.labelbook.LabelBook(self,
            style = wx.BORDER_THEME,
            agwStyle = INB_LEFT
            | INB_SHOW_ONLY_TEXT
            | INB_BORDER
            | INB_WEB_HILITE
            | INB_FIT_LABELTEXT
        )
        book.AddPage(G_ActionStep(book), "Hello1")
        book.AddPage(G_ActionStep(book), "Hello2")

        frame_sizer.Add(book, proportion = 1, flag = wx.ALL | wx.EXPAND, border = border)
        self.CenterOnScreen()


    #-------------------------------------------------------
    def OnDropFiles(self, files):
        if len(files) > 1:
            return False

        self._PathCtrl.SetLabel(files[0])
        return True



## G_LaunchApp #############################################

class G_LaunchApp(wx.App):

    #-------------------------------------------------------
    def OnInit(self):
        # have to manually set the Posix locale
        self._Locale = wx.Locale(wx.LANGUAGE_DEFAULT)

        appname = "NlvLaunch"
        self.SetAppName(appname)

        # startup the GUI window
        G_LaunchFrame(None, appname).Show()
        return True



## MODULE ##################################################

G_LaunchApp().MainLoop()
