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
_Spacer = 10



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

    #-------------------------------------------------------
    def __init__(self, parent, path, schemata):
        super().__init__(wx.VERTICAL, parent, label = path)

        self._Schemata = schemata
        self._SchemaIdx = 0
        self._BuilderIdx = wx.NOT_FOUND 
        window = self.GetStaticBox()
        
        schemata_combo = wx.ComboBox(window,
            choices = [schema.GetName() for schema in schemata],
            style = wx.CB_DROPDOWN
                | wx.CB_READONLY
        )
        schemata_combo.SetSelection(self._SchemaIdx)
        schemata_combo.Bind(wx.EVT_COMBOBOX, self.OnSchema)
        self.BuildLabelledRow("Schema", schemata_combo)

        builder_combo = self.BuilderCombo = wx.ComboBox(window,
            style = wx.CB_DROPDOWN
                | wx.CB_READONLY
        )
        builder_combo.Bind(wx.EVT_COMBOBOX, self.OnBuilder)
        self.SetupBuilderCombo()
        self.BuildLabelledRow("Initial view(s)", builder_combo)


    #-------------------------------------------------------
    def BuildRow(self, left, right):
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.Add(hsizer, flag = wx.ALL | wx.EXPAND, border = _Border)

        hsizer.Add(left, flag = wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
        hsizer.AddSpacer(_Spacer)
        hsizer.Add(right, flag = wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
        hsizer.AddStretchSpacer(1)


    #-------------------------------------------------------
    def BuildLabelledRow(self, name, control):
        label = wx.StaticText(self.GetStaticBox(), label = name)
        return self.BuildRow(label, control)


    #-------------------------------------------------------
    def OnSchema(self, event):
        idx = event.GetSelection()
        if idx != self._SchemaIdx:
            self._SchemaIdx = idx
            self.SetupBuilderCombo()


    #-------------------------------------------------------
    def SetupBuilderCombo(self):
        builders = [name for (name, guid) in self._Schemata[self._SchemaIdx].GetBuildersNameGuidList()]
        if len(builders) == 0:
            self.BuilderCombo.Clear()
            self._BuilderIdx = wx.NOT_FOUND 
        else:
            self.BuilderCombo.SetItems(builders)
            self._BuilderIdx = 0

        self.BuilderCombo.SetSelection(self._BuilderIdx)

    def OnBuilder(self, event):
        idx = event.GetSelection()
        if idx != self._BuilderIdx:
            self._BuilderIdx = idx



class G_StdLauncher:

    #-------------------------------------------------------
    def __init__(self, schema):
        self._Schema = schema



## G_LaunchFrame ###########################################

class G_LaunchFrame(wx.Frame):

    _DropperText = "Drop log file(s) here"


    #-------------------------------------------------------
    def __init__(self, parent, title, schemata):
        super().__init__(
            parent, -1, title,
            size = (720, 970),
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

        dropper_sizer = wx.StaticBoxSizer(wx.VERTICAL, self, label = "File(s) to launch")
        frame_sizer.Add(dropper_sizer, flag = wx.ALL | wx.EXPAND, border = _Border)
        dropper_window = dropper_sizer.GetStaticBox()

        path_ctrl = self._PathCtrl = wx.StaticText(dropper_window, label = self._DropperText)
        path_ctrl.SetDropTarget(G_FileDropTarget(self.OnDropFiles))
        dropper_sizer.Add(path_ctrl, flag = wx.ALL | wx.EXPAND, border = _Border)

        actions = self._Actions = wx.BoxSizer(wx.VERTICAL)
        frame_sizer.Add(actions, flag = wx.ALL | wx.EXPAND, border = _Border)

        action_sizer = wx.StaticBoxSizer(wx.HORIZONTAL, self, label = "Action")
        frame_sizer.Add(action_sizer, flag = wx.ALL | wx.EXPAND, border = _Border)
        action_window = action_sizer.GetStaticBox()

        self._CloseAfterLaunch = True
        close_chkbox = wx.CheckBox(action_window, label = "Close after launch")
        close_chkbox.SetValue(self._CloseAfterLaunch)
        close_chkbox.Bind(wx.EVT_CHECKBOX, self.OnCloseCheck)
        action_sizer.Add(close_chkbox, flag = wx.ALL | wx.ALIGN_CENTER_VERTICAL, border = _Border)

        launch_btn = wx.Button(action_window, label = "Launch")
        launch_btn.Bind(wx.EVT_BUTTON, self.OnLaunch)
        action_sizer.Add(launch_btn, flag = wx.ALL | wx.ALIGN_CENTER_VERTICAL, border = _Border)

        self.CenterOnScreen()


    #-------------------------------------------------------
    def GetActions(self):
        return [sizer_item.GetSizer() for sizer_item in self._Actions]


    #-------------------------------------------------------
    def Reset(self):
        frame_sizer = self.GetSizer()

        # seem to have to remove child window(s) manually
        for action in self.GetActions():
            action.GetStaticBox().DestroyChildren()
        frame_sizer.Remove(self._Actions)

        actions = self._Actions = wx.BoxSizer(wx.VERTICAL)
        frame_sizer.Insert(1, actions, flag = wx.ALL | wx.EXPAND, border = _Border)
        self._PathCtrl.SetLabel(self._DropperText)


    #-------------------------------------------------------
    def OnCloseCheck(self, event):
        self._CloseAfterLaunch = event.GetInt()


    #-------------------------------------------------------
    def OnLaunch(self, event):
        pass


    #-------------------------------------------------------
    def SetupActions(self, paths):
        self.Reset()

        actionable_paths = []
        for path in paths:
            suffix = Path(path).suffix[1:]
            schemata = self._Schemata.get(suffix)
            if schemata is not None:
                actionable_paths.append(path)
                action = G_Action(self, path, schemata)
                self._Actions.Add(action, flag = wx.TOP | wx.BOTTOM | wx.EXPAND, border = _Border)

        label = self._DropperText
        if len(actionable_paths) != 0:
            label = ",\n".join(actionable_paths)
        self._PathCtrl.SetLabel(label)


    #-------------------------------------------------------
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
