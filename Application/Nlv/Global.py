#
# Copyright (C) Niel Clausen 2019. All rights reserved.
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
import logging
import os
from pathlib import Path
import sys
import time
import traceback

# wxWidgets imports
import wx

# Content provider interface
import Nlog



## G_FrozenWindow ##########################################

class G_FrozenWindow:
    """Context manager (use with "with")."""

    #-------------------------------------------------------
    def __init__(self, window):
        self._Window = window


    #-------------------------------------------------------
    def __enter__(self):
        self._Window.Freeze()
        return self


    #-------------------------------------------------------
    def __exit__(self, exc_type, exc_value, exc_traceback):
        self._Window.Thaw()



## G_ProgressMeter #########################################

class G_ProgressMeter:
    """Helper class to display progress information for long running activities"""

    Meter = None
    Count = 0


    #-------------------------------------------------------
    def __init__(self, title):
        if G_ProgressMeter.Count == 0:
            G_ProgressMeter.Meter = self
            G_ProgressMeter.Count = 1
        else:
            G_ProgressMeter.Count += 1

        self._StartTime = time.perf_counter()
        self._Title = title
        self._Dlg = None

    @staticmethod
    def Close():
        G_ProgressMeter.Count -= 1
        if G_ProgressMeter.Count == 0:
            G_ProgressMeter.Meter = None


    #-------------------------------------------------------
    def DoPulse(self, message):
        """After half a second, display meter and start showing progress"""

        if self._Dlg is None:
            now = time.perf_counter()
            if now - self._StartTime > 0.5:
                self._Dlg = wx.ProgressDialog(self._Title, message,
                    style = wx.PD_APP_MODAL | wx.PD_AUTO_HIDE | wx.PD_ELAPSED_TIME
                )

        else:
            self._Dlg.Pulse(message)

    @classmethod
    def Pulse(cls, message):
        instance = cls.Meter
        if instance is not None:
            instance.DoPulse(message)



## G_ProgressMeterScope ####################################

class G_ProgressMeterScope:
    """Context manager (use with "with")."""

    #-------------------------------------------------------
    def __init__(self, title):
        self._Title = title


    #-------------------------------------------------------
    def __enter__(self):
        self._Meter = G_ProgressMeter(self._Title)
        return self


    #-------------------------------------------------------
    def __exit__(self, exc_type, exc_value, exc_traceback):
        self._Meter.Close()




## G_PerfTimer #############################################
           
class G_PerfTimer:
    """Support performance timing of call hierarchies"""

    _Last = None


    #-------------------------------------------------------
    @classmethod
    def GetCurrent(cls):
        return cls._Last


    #-------------------------------------------------------
    def __init__(self, description = "", item_count = 0):
        self._Description = description
        self._Arguments = []
        self._ItemCount = item_count
        self._Timer = Nlog.PerfTimer()
        self._Parent = __class__._Last
        self._Children = []
        self._Closed = False

        if self._Parent is not None:
            self._Parent._AddChild(self)

        __class__._Last = self

        G_ProgressMeter.Pulse(description)


    #-------------------------------------------------------
    def _AddChild(self, child):
        self._Children.append(child)


    #-------------------------------------------------------
    def _Report(self, indent = 0):
        if not self._Closed:
            raise RuntimeError("TimeFunction failed")

        args = ", ".join(self._Arguments)

        inclusive = self._Elapsed
        exclusive = inclusive - sum([timer._Elapsed for timer in self._Children])

        # only report "slow" operations to user; currently, greater than 2s
        if indent == 0 and inclusive > 2:
            logging.info("{}({}) took {:.2f}s".format(self._Description, args, inclusive))

        per_item_text = ""
        if self._PerItem != 0:
            per_item_text = "per_item:{:.3f}us ".format(self._PerItem)

        if exclusive != inclusive:
            dur_text = "elapsed(inclusive):{:.2f}s elapsed(exclusive):{:.2f}s".format(inclusive, exclusive)
        else:
            dur_text = "elapsed:{:.2f}s".format(inclusive)

        logging.debug("G_PerfTimer: {}{}({}): {} {}".format("|--" * indent, self._Description, args, dur_text, per_item_text))

        for child in self._Children:
            child._Report(indent + 1)


    #-------------------------------------------------------
    def SetItemCount(self, item_count):
        self._ItemCount = item_count


    #-------------------------------------------------------
    def AddArgument(self, arg):
        self._Arguments.append(arg)


    #-------------------------------------------------------
    def Close(self, item_count = 0):
        if not self._Closed:
            self._Closed = True

            if item_count == 0:
                item_count = self._ItemCount

            self._Elapsed = self._Timer.Overall()
            self._PerItem = self._Timer.PerItem(item_count)
            __class__._Last = self._Parent

            if self._Parent is None:
                self._Report()



## G_PerfTimerScope ########################################

class G_PerfTimerScope:
    """
    Context manager (use with "with").
    Time the execution of something
    """

    #-------------------------------------------------------
    def __init__(self, name, item_count = 0):
        self._Name = name
        self._ItemCount = item_count


    #-------------------------------------------------------
    def __enter__(self):
        self._Timer = G_PerfTimer(self._Name)
        return self


    #-------------------------------------------------------
    def __exit__(self, exc_type, exc_value, exc_traceback):
        self._Timer.Close(self._ItemCount)


    #-------------------------------------------------------
    def SetItemCount(self, item_count):
        self._ItemCount = item_count



## G_ChannelLogFilter ######################################

class G_ChannelLogFilter(logging.Filter):
    """
    Support rudimentary log "channels". Message can be selectively
    sent to the logfile.
    """

    #-------------------------------------------------------
    def __init__(self):
        super().__init__()

        # the list of channels to log
        self._Channels = set(["focus"])


    #-------------------------------------------------------
    def filter(self, record):
        if "_nlv_channel" in record.__dict__:
            if record._nlv_channel in self._Channels:
                record.msg = "Channel({}): {}".format(record._nlv_channel, record.msg)
                return True
            else:
                return False
        else:
            return True



## G_Const #################################################

class G_Const:
    """GUI constants and defaults"""

    #-------------------------------------------------------

    GlobalThemeCls = "global"
    LogThemeCls = "log"
    ViewThemeCls = "view"
    EventThemeCls = "event"


    #-------------------------------------------------------

    # tracker names are hard coded - they were once read from
    # the first logfile in the session; but that makes little sense
    LocalTrackerName = "(L) Local"

    GlobalTrackerNames = [
        "(G) Global/1",
        "(H) Global/2",
        "(J) Global/3",
        "(K) Global/4",
    ]

    # maximum number of global trackers to persist
    NumGlobalTrackers = len(GlobalTrackerNames)


    #-------------------------------------------------------

    # standard border size for items inside a static box sizer
    Sizer_StdBorder = 4

    # border size for a static box sizer in its parent panel
    Sizer_BoxBorder = 5

    # button size
    ButtonSize = (75, -1)
    ButtonSizeSmall = (60, -1)
    ButtonSizeLarge = (110, -1)
    ButtonSpacer = 5

    # default position for the project panel splitter location
    ProjectInitialSplit = 250
    ProjectMinSplit = 150

    # default container node listbox selector control height
    ListBoxH = 110

    # preferred combo box row height
    ComboRowHeight = 24


    #-------------------------------------------------------

    # application commands
    ID_LOGFILE_NEW_VIEW = wx.ID_HIGHEST + 10
    ID_LOGFILE_NEW_EVENTS = wx.ID_HIGHEST + 11

    ID_NODE_DELETE = wx.ID_HIGHEST + 20
    ID_NODE_SHOWHIDE = wx.ID_HIGHEST + 21

    ID_SESSION_SAVE = wx.ID_HIGHEST + 30
    ID_SESSION_SAVE_AS = wx.ID_HIGHEST + 31

    ID_THEME_ACTIVATE = wx.ID_HIGHEST + 42
    ID_THEME_COPY = wx.ID_HIGHEST + 3
    ID_THEME_DELETE = wx.ID_HIGHEST + 44
    ID_THEME_RENAME = wx.ID_HIGHEST + 45

    #-------------------------------------------------------
    
    # log channel "names"
    LogFocus = dict(_nlv_channel = "focus")



## G_Global ################################################

class G_Global:

    #-------------------------------------------------------
    def GetInstallDir():
        return Path( __file__ ).parent


    def GetConfigDir():
        return wx.ConfigBase.Get().Read("/NLV/DataDir")


    #-------------------------------------------------------
    def MakeCacheDir(base_path, subdir = None):
        if not isinstance(base_path, Path):
            base_path = Path(base_path)

        if not base_path.is_dir():
            base_path = base_path.parent

        cachedir = base_path / ".nlvc"
        if subdir is not None:
            cachedir = cachedir / subdir

        if not cachedir.exists():
            cachedir.mkdir(parents = True)

        return cachedir


    #-------------------------------------------------------
    # hack to stamp strings with metadata
    _MarkMagic = "#<->#"
    _MarkNoDisplay = "nodisplay"

    @classmethod
    def MakeMarkPrefix(cls, mark):
        return "{}{}{}".format(cls._MarkMagic, mark, cls._MarkMagic)

    @classmethod
    def MarkString(cls, str, mark = _MarkNoDisplay):
        pfx = cls.MakeMarkPrefix(mark)
        return pfx + str

    @classmethod
    def IsMarked(cls, str, mark = _MarkNoDisplay):
        # zero = "not marked"
        pfx = cls.MakeMarkPrefix(mark)
        sz = len(pfx)
        if str[0:sz] == pfx:
            return sz
        else:
            return 0

    @classmethod
    def UnmarkString(cls, str, mark = _MarkNoDisplay):
        return str[cls.IsMarked(str):]


    #-------------------------------------------------------
    def FormatTraceback(exc_type, exc_value, exc_traceback):
        message = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        return message

    def FormatLastTraceback():
        return __class__.FormatTraceback(*sys.exc_info())


    #-------------------------------------------------------
    def GetCurrentTimer():
        return G_PerfTimer.GetCurrent()

    def TimeFunction(func):
        """
        Decorator to allow function/method execution times to
        be recorded and logged.
        """
        def TimeFunctionWrapper(*args, **kwargs):
            with G_PerfTimerScope(func.__qualname__):
                return func(*args, **kwargs)

        return TimeFunctionWrapper


    #-------------------------------------------------------
    def PulseProgressMeter(message):
        G_ProgressMeter.Pulse(message)

    def ProgressMeter(func):
        """
        Decorator to allow permit a progress meter to be
        displayed if the function runs for more than 0.5s
        """
        def ProgressMeterWrapper(*args, **kwargs):
            with G_ProgressMeterScope("NLV is busy ..."):
                return func(*args, **kwargs)

        return ProgressMeterWrapper


    #-------------------------------------------------------
    def RelPath(path, start = os.curdir):
        # pathlib.relative_to is surprisingly limited; this
        # workaround taken from https://stackoverflow.com/questions/38083555/using-pathlibs-relative-to-for-directories-on-the-same-level
        return Path(os.path.relpath(path, start))



