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

# Python imports
import argparse
from pathlib import Path

# wxWidgets imports
import wx

# Application imports
from Nlv.Logmeta import GetMetaStore


## PRIVATE #################################################

_Border = 5



## G_FileDropTarget ########################################

class G_FileDropTarget(wx.FileDropTarget):

    #-------------------------------------------------------
    def __init__(self, handler):
        wx.FileDropTarget.__init__(self)
        self._Handler = handler


    #-------------------------------------------------------
    def OnDropFiles(self, x, y, files):
        return self._Handler(files)


## G_Action ################################################

class G_Action(wx.StaticBoxSizer):

    def __init__(self, parent, path):
        super().__init__(wx.VERTICAL, parent, label = path)

        action_ctrl = wx.StaticText(self.GetStaticBox(), label = "None")
        self.Add(action_ctrl, flag = wx.ALL | wx.EXPAND, border = _Border)



        #self.SetBackgroundColour(wx.Colour(255,255,255))

        #static = wx.StaticText(self, -1, "Label", pos=(10, 10))



class G_StdLauncher:

    #-------------------------------------------------------
    def __init__(self, schema):
        self._Schema = schema



## G_LaunchFrame ###########################################

class G_LaunchFrame(wx.Frame):

    #-------------------------------------------------------
    def __init__(self, parent, title, schemata):
        super().__init__(
            parent, -1, title,
            size = (970, 720),
            style = wx.DEFAULT_FRAME_STYLE
                | wx.NO_FULL_REPAINT_ON_RESIZE
        )

        self._Schemata = schemata
        self.SetupUI()

        global _Args
        if _Args.launch is not None:
            self.SetupActions([_Args.launch])


    #-------------------------------------------------------
    def SetupUI(self):
        frame_sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(frame_sizer)
        self.SetBackgroundColour(wx.Colour(255, 255, 255))

        dropper = self._FileDropperPane = wx.StaticBoxSizer(wx.VERTICAL, self, label = "File(s) to launch")
        frame_sizer.Add(dropper, flag = wx.ALL | wx.EXPAND, border = _Border)

        path_ctrl = self._PathCtrl = wx.StaticText(dropper.GetStaticBox(), label = "Drop file(s) here")
        path_ctrl.SetDropTarget(G_FileDropTarget(self.OnDropFiles))
        dropper.Add(path_ctrl, flag = wx.ALL | wx.EXPAND, border = _Border)

        actions = self._Actions = wx.BoxSizer(wx.VERTICAL)
        frame_sizer.Add(actions, flag = wx.ALL | wx.EXPAND, border = _Border)

        reset_btn = wx.Button(self, label = "Reset")
        reset_btn.Bind(wx.EVT_BUTTON, self.OnReset)

        commands = self.Commands = wx.BoxSizer(wx.HORIZONTAL)
        commands.Add(reset_btn)
        frame_sizer.Add(commands, flag = wx.ALL | wx.EXPAND, border = _Border)


        #action_sizer = self._ActionPane = wx.StaticBoxSizer(wx.VERTICAL, self, label = "Action")
        #frame_sizer.Add(action_sizer, flag = wx.ALL | wx.EXPAND, border = _Border)
        #action_ctrl = self._ActionCtrl = wx.StaticText(action_sizer.GetStaticBox(), label = "None")
        #action_sizer.Add(action_ctrl, flag = wx.ALL | wx.EXPAND, border = _Border)
        #frame_sizer.Hide(action_sizer)

        #book = self._LabelBook = wx.lib.agw.labelbook.LabelBook(self,
        #    style = wx.BORDER_THEME,
        #    agwStyle = INB_LEFT
        #    | INB_SHOW_ONLY_TEXT
        #    | INB_BORDER
        #    | INB_WEB_HILITE
        #    | INB_FIT_LABELTEXT
        #)
        #book.AddPage(G_ActionStep(book), "Hello1")
        #book.AddPage(G_ActionStep(book), "Hello2")

        #frame_sizer.Add(book, proportion = 1, flag = wx.ALL | wx.EXPAND, border = border)
        #frame_sizer.Hide(book)

        self.CenterOnScreen()


    #-------------------------------------------------------
    def Reset(self):
        frame_sizer = self.GetSizer()

        for sizer_item in self._Actions:
            sizer_item.GetSizer().GetStaticBox().DestroyChildren()
        frame_sizer.Remove(self._Actions)

        actions = self._Actions = wx.BoxSizer(wx.VERTICAL)
        frame_sizer.Insert(1, actions, flag = wx.ALL | wx.EXPAND, border = _Border)
        frame_sizer.Show(self._FileDropperPane)


    def OnReset(self, event):
        self.Reset()
        self.GetSizer().Layout()


    #-------------------------------------------------------
    def AddAction(self, action):
        self._Actions.Add(action, flag = wx.EXPAND)


    #-------------------------------------------------------
    def SetupActions(self, paths):
        self.Reset()
        for path in paths:
            self.AddAction(G_Action(self, path))

        self.GetSizer().Hide(self._FileDropperPane)


    def OnDropFiles(self, paths):
        self.SetupActions(paths)
        self.GetSizer().Layout()
        return True



## G_LaunchApp #############################################

class G_LaunchApp(wx.App):

    #-------------------------------------------------------
    def OnInit(self):
        # have to manually set the Posix locale
        self._Locale = wx.Locale(wx.LANGUAGE_DEFAULT)

        self.SetAppName("NLV")
        user_dir = Path(wx.StandardPaths.Get().GetUserDataDir())

        appname = "NlvLaunch"
        self.SetAppName(appname)

        self.SetupMetaData(user_dir)
        self.SetupExtensions()
        schemata = self.SetupLaunchers()

        # startup the GUI window
        G_LaunchFrame(None, appname, schemata).Show()
        return True


    #-------------------------------------------------------
    def SetupMetaData(self, user_dir):
        from Nlv.Logmeta import InitMetaStore
        InitMetaStore(user_dir, 0)


    #-------------------------------------------------------
    def SetupExtensions(self):
        from Nlv.Logmeta import GetMetaStore

        # Interface between NLV plugins (extensions) and the application
        class Context:
            def __init__(self, info):
                self._Info = info

            def RegisterLogSchemata(self, install_dir):
                GetMetaStore().RegisterLogSchemata(install_dir)

            def RegisterThemeDirectory(self, install_dir):
                pass

        # load site specific extensions
        from Nlv.Extension import LoadExtensions
        LoadExtensions(Context)


    #-------------------------------------------------------
    def SetupLaunchers(self):
        meta_store = GetMetaStore()
        schema_list = [meta_store.GetLogSchema(guid) for (name, guid) in meta_store.GetLogSchemataNames()]

        schemata = dict()
        for schema in schema_list:
            schemata.setdefault(schema.GetExtension(), []).append(schema)

        return schemata



## COMMAND LINE ############################################

_Parser = argparse.ArgumentParser( prog = "launch", description = "NlvLaunch" )
_Parser.add_argument( "-l", "--launch", type = str, default = None, help = "Launch file" )
_Args = _Parser.parse_args()



## MODULE ##################################################

G_LaunchApp().MainLoop()
