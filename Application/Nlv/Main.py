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
import argparse
from pathlib import Path
import sys

# wxWidgets imports
import wx
import wx.lib.agw.aui as aui

# Application imports
import Nlv.Session
import Nlv.Logfile
import Nlv.View
import Nlv.EventView
from Nlv.Extension import LoadExtensions
from Nlv.Project import G_Project
from Nlv.Project import G_Global
from Nlv.Project import G_PerfTimerScope
from Nlv.Shell import G_Shell
from Nlv.Version import NLV_VERSION

# System imports
import logging

# Enable/disable profiling (VisualStudio tools not working ...)
_G_WantProfiling = False
_G_Profiler = None

if _G_WantProfiling:
    import cProfile
    _G_Profiler = cProfile.Profile()



## G_ExceptionDialog #######################################

class G_ExceptionDialog(wx.Dialog):
 
    #-------------------------------------------------------
    def __init__(self):
        super().__init__(
            None, 
            title = "Application Error",
            size = (800, 600),
            style = wx.DEFAULT_DIALOG_STYLE
            | wx.CAPTION
            | wx.RESIZE_BORDER
            | wx.CLOSE_BOX
            | wx.MAXIMIZE_BOX
        )

        sizer = wx.BoxSizer(wx.VERTICAL)
        text = wx.StaticText(self, label = "A Python exception was not caught:")
        sizer.Add(text, flag = wx.TOP | wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, border = 5)

        self._Message = wx.TextCtrl(self, style = wx.TE_READONLY | wx.TE_MULTILINE)
        sizer.Add(self._Message, proportion = 1, flag = wx.BOTTOM | wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, border = 5)

        self.SetSizer(sizer)
#        sizer.Fit(self)


    #-------------------------------------------------------
    def Display(self, message):
        self._Message.SetLabelText(message)
        self.ShowModal()



## G_ExceptionHook #########################################

def G_ExceptionHook(exc_type, exc_value, exc_traceback):
    """
    Process all unhandled exceptions.
 
    :param `exc_type`: the exception type (`SyntaxError`, `ZeroDivisionError`, etc...);
    :type `etype`: `Exception`
    :param string `exc_value`: the exception error message;
    :param string `exc_traceback`: the traceback header, if any (otherwise, it prints the
     standard Python header: ``Traceback (most recent call last)``.
    """

    message = G_Global.FormatTraceback(exc_type, exc_value, exc_traceback)
    G_ExceptionDialog().Display(message.replace("\n", "\r\n"))



## G_ConsoleLog ############################################

class G_ConsoleLog(wx.Log):

    #-------------------------------------------------------
    def __init__(self, parent):
        """Setup wxWidgets and Python logging"""
        wx.Log.__init__(self)

        # setup a log window
        self.TextCtrl = wx.TextCtrl(
            parent, -1,
            style = wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL
        )
        self.TextCtrl.SetFont(wx.Font(wx.FontInfo(8).FaceName("Consolas")))

        # setup wxWindows logging
        wx.Log.SetActiveTarget(self)

        # send Python info logging and above to the console
        self._LogHandler = logconsole_handler = logging.StreamHandler(self)
        logconsole_handler.setLevel(logging.INFO)
        logconsole_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        _Logger.addHandler(logconsole_handler)

        # put a start marker in the log
        logging.debug( "" )
        logging.debug( "======================================================================" )
        logging.debug( "===                          NLV                                ======" )
        logging.debug( "======================================================================" )
        logging.debug( "" )
        logging.info( "NLV Version: {}".format(NLV_VERSION) )


    #-------------------------------------------------------
    def Close(self):
        _Logger.removeHandler(self._LogHandler)
        wx.Log.SetActiveTarget(None)


    #-------------------------------------------------------
    def _LogMessage(self, message):
        if self.TextCtrl:
            self.TextCtrl.AppendText(message)


    #-------------------------------------------------------
    def write(self, data):
        """Python log interface"""
        self._LogMessage(data)

    def flush( self ):
        pass


    #-------------------------------------------------------
    def DoLogText(self, message):
        """wxWindows log interface"""
        self._LogMessage(message + '\n')



## G_LogViewFrame ##########################################

@G_Global.TimeFunction
class G_LogViewFrame(wx.Frame):

    #-------------------------------------------------------
    def __init__(self, parent, title):
        wx.Frame.__init__(
            self, parent, -1, title,
            size = (970, 720),
            style = wx.DEFAULT_FRAME_STYLE
                | wx.NO_FULL_REPAINT_ON_RESIZE
                | wx.MAXIMIZE
        )

        # https://www.blog.pythonlibrary.org/2014/03/14/wxpython-catching-exceptions-from-anywhere/
        sys.excepthook = G_ExceptionHook

        self.SetMinSize((640,480))
        self.Centre(wx.BOTH)

        icon_path = Path( __file__ ).parent.joinpath("if_puzzle_yellow_10505.ico")
        if icon_path.exists():
            self.SetIcons(wx.IconBundle(str(icon_path)))

        # fill the frame with a panel - needed for sizers to work
        self._FramePanel = wx.Panel(self)
        self._InfoPanel = wx.Notebook(self._FramePanel, style = wx.NB_TOP)

        # initialise console logger display
        self._ConsoleLog = G_ConsoleLog(self._InfoPanel)
        self._InfoPanel.AddPage(self._ConsoleLog.TextCtrl, "Console")

        # frame panel is entirely managed by an AuiManager
        self._AuiManager = aui.AuiManager()
        self._AuiManager.SetManagedWindow(self._FramePanel)

        # create and initialise child panels

        self._NoteBook = aui.AuiNotebook(self._FramePanel,
            agwStyle = aui.AUI_NB_TOP
             | aui.AUI_NB_TAB_SPLIT
             | aui.AUI_NB_TAB_MOVE
             | aui.AUI_NB_DRAW_DND_TAB
             | aui.AUI_NB_WINDOWLIST_BUTTON
        )
        self._NoteBook.SetArtProvider(aui.tabart.VC8TabArt())

        self._Project = G_Project(self._FramePanel, self)

        # event handlers
        self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)

        # Use the aui manager to set up everything
        self._AuiManager.AddPane(
            self._NoteBook,
            aui.AuiPaneInfo().CenterPane().Name("Notebook")
        )
        self._AuiManager.AddPane(
            self._Project,
            aui.AuiPaneInfo().
                Left().Layer(2).BestSize((300, 700)).
                MinSize((240, -1)).
                Floatable(True).FloatingSize((300, 700)).
                Gripper(True).GripperTop(True).
                CaptionVisible(False).
                Name("Control")
        )
        self._AuiManager.AddPane(
            self._InfoPanel,
            aui.AuiPaneInfo().
                Left().Layer(2).BestSize((-1, 150)).
                MinSize((-1, 140)).
                Floatable(True).FloatingSize((500, 160)).
                Gripper(True).GripperTop(True).
                CaptionVisible(False).
                Name("Info")
        )

        self._AuiManager.SetAGWFlags(
            aui.AUI_MGR_ALLOW_FLOATING
            | aui.AUI_MGR_ALLOW_ACTIVE_PANE
            | aui.AUI_MGR_TRANSPARENT_DRAG
            | aui.AUI_MGR_TRANSPARENT_HINT
            | aui.AUI_MGR_HINT_FADE
            | aui.AUI_MGR_NO_VENETIAN_BLINDS_FADE
            | aui.AUI_MGR_LIVE_RESIZE
            | aui.AUI_MGR_WHIDBEY_DOCKING_GUIDES
            | aui.AUI_MGR_SMOOTH_DOCKING
        )

        # open session document
        global _Args
        self._Project.OpenSession(_Args)

        # layout and display
        self._AuiManager.Update()


    #-------------------------------------------------------
    def GetAuiManager(self):
        return self._AuiManager

    def GetNotebook(self):
        return self._NoteBook

    def GetInfoPanel(self):
        return self._InfoPanel


    #-------------------------------------------------------
    def OnCloseWindow(self, event):
        global _G_Profiler
        if _G_Profiler is not None:
            _G_Profiler.disable()
            _G_Profiler.create_stats()
            _G_Profiler.dump_stats("cprofile.dat")

        self.Freeze()
        self._ConsoleLog.Close()
        self._Project.Close()
        self._AuiManager.UnInit()
        self.Destroy()



## G_LogViewApp ############################################

class G_LogViewApp(wx.App):

    #-------------------------------------------------------
    @G_Global.ProgressMeter
    @G_Global.TimeFunction
    def OnInit(self):
        # have to manually set the Posix locale
        self._Locale = wx.Locale(wx.LANGUAGE_DEFAULT)

        appname = "NLV"
        self.SetAppName(appname)

        # currently, neither the theme files, nor the "channel" (pipe to VisualStudio)
        # can be shared between application instances; so prevent that here
        self._ApplicationLock = wx.SingleInstanceChecker()
        if self._ApplicationLock.IsAnotherRunning():
            wx.MessageBox(
                "Another instance of the program is already running. This instance will Quit", appname,
                wx.OK | wx.ICON_INFORMATION | wx.STAY_ON_TOP | wx.CENTRE )

            return False

        # setup application configuration
        path = Path(wx.StandardPaths.Get().GetUserDataDir())
        path.mkdir(exist_ok = True)
        config = wx.FileConfig(localFilename = str(path / "nlv.ini"))
        config.Write("/NLV/DataDir", str(path))
        wx.ConfigBase.Set(config)

        # setup logging
        global _Logger
        logfile = open(str(path / "nlv.log"), "a")

        _Logger = logging.getLogger('')
        _Logger.setLevel(logging.DEBUG)

        # send debug and above to the logfile
        def FilterNoisyChartFindFontLines(record):
            if record.levelno == logging.DEBUG and record.msg.find("findfont: score") >= 0:
                return False
            else:
                return True

        logfile_handler = logging.StreamHandler(logfile)
        logfile_handler.addFilter(FilterNoisyChartFindFontLines)
        logfile_handler.setLevel(logging.DEBUG)
        logfile_handler.setFormatter(logging.Formatter( "%(asctime)s: %(levelname)s: %(message)s" ))
        _Logger.addHandler(logfile_handler)

        # the text window display for logging is setup once the frame is created
        # see G_ConsoleLog

        # load site specific extensions
        with G_PerfTimerScope("LoadExtensions"):
            LoadExtensions()

        # startup the GUI window
        frame = G_LogViewFrame(None, appname)

        with G_PerfTimerScope("G_LogViewFrame.Show"):
            frame.Show()

        return True



## COMMAND LINE ############################################

_Parser = argparse.ArgumentParser( prog = "nlv", description = "NLV" )
_Parser.add_argument( "-i", "--integration", action = "store_true", help = "integrate NLV into the shell" )
_Parser.add_argument( "-l", "--log", action = "append", help = "add a logfile to the session; log specified as 'path@schema'" )
_Parser.add_argument( "-r", "--recent", action = "store_true", help = "open most recently accessed session" )
_Parser.add_argument( "-s", "--session", type = str, default = None, help = "open session document" )
_Args = _Parser.parse_args()



## MODULE ##################################################

# create and run the application
_Logger = None

def main():
    if _Args.integration:
        G_Shell().SetupIntegration()
    else:
        G_LogViewApp().MainLoop()

if _G_Profiler is not None:
    _G_Profiler.enable()

if __name__ == "__main__":
    main()
