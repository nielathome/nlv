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
