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
import keyword

# wxWidgets imports
import wx
import wx.stc as stc

# Application imports 
from .Logfile import G_DisplayControl
from .Logfile import G_PanelDisplayControl
from .StyleNode import G_ColourTraits


## G_PythonTextCtrl ########################################

faces = {
    'times': 'Times New Roman',
    'mono' : 'Courier New',
    'helv' : 'Segoe UI',
    'other': 'Comic Sans MS',
    'size' : 9,
    'size2': 8,
}


class G_PythonTextCtrl(stc.StyledTextCtrl, G_DisplayControl):
    """See wxPython StyledTextCtrl_2 demo"""

    #-------------------------------------------------------
    def __init__(self, parent, ID = -1,
                 pos=wx.DefaultPosition, size=wx.DefaultSize,
                 style=0):
        stc.StyledTextCtrl.__init__(self, parent, ID, pos, size, style)

        self.CmdKeyAssign(ord('B'), stc.STC_KEYMOD_CTRL, stc.STC_CMD_ZOOMIN)
        self.CmdKeyAssign(ord('N'), stc.STC_KEYMOD_CTRL, stc.STC_CMD_ZOOMOUT)

        self.SetLexer(stc.STC_LEX_PYTHON)
        self.SetKeyWords(0, " ".join(keyword.kwlist))

        self.SetProperty("fold", "1")
        self.SetProperty("tab.timmy.whinge.level", "1")
        self.SetMargins(0, 0)

        self.SetViewWhiteSpace(False)
        self.SetTabWidth(4)
        self.SetUseTabs(False)

        self.SetEdgeMode(stc.STC_EDGE_NONE)
        self.SetEdgeColumn(78)

        # Setup a margin to hold fold markers
        self.SetMarginType(2, stc.STC_MARGIN_SYMBOL)
        self.SetMarginMask(2, stc.STC_MASK_FOLDERS)
        self.SetMarginSensitive(2, True)
        self.SetMarginWidth(2, 12)

        # Folding: Like a flattened tree control using square headers
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN,    stc.STC_MARK_BOXMINUS,          "white", "#808080")
        self.MarkerDefine(stc.STC_MARKNUM_FOLDER,        stc.STC_MARK_BOXPLUS,           "white", "#808080")
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB,     stc.STC_MARK_VLINE,             "white", "#808080")
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL,    stc.STC_MARK_LCORNER,           "white", "#808080")
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEREND,     stc.STC_MARK_BOXPLUSCONNECTED,  "white", "#808080")
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID, stc.STC_MARK_BOXMINUSCONNECTED, "white", "#808080")
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL, stc.STC_MARK_TCORNER,           "white", "#808080")

        # Make some styles,  The lexer defines what each style is used for, we
        # just have to define what each style looks like.  This set is adapted from
        # Scintilla sample property files.

        # Global default styles for all languages
        self.StyleSetSpec(stc.STC_STYLE_DEFAULT,     "face:%(helv)s,size:%(size)d" % faces)
        self.StyleClearAll()  # Reset all to be like the default

        # Global default styles for all languages
        self.StyleSetSpec(stc.STC_STYLE_DEFAULT,     "face:%(helv)s,size:%(size)d" % faces)
        self.StyleSetSpec(stc.STC_STYLE_LINENUMBER,  "back:#C0C0C0,face:%(helv)s,size:%(size2)d" % faces)
        self.StyleSetSpec(stc.STC_STYLE_CONTROLCHAR, "face:%(other)s" % faces)
        self.StyleSetSpec(stc.STC_STYLE_BRACELIGHT,  "fore:#FFFFFF,back:#00007F,bold")
        self.StyleSetSpec(stc.STC_STYLE_BRACEBAD,    "fore:#000000,back:#7F0000,bold")

        # Python styles
        self.StyleSetSpec(stc.STC_P_DEFAULT,         "fore:#000000,size:%(size)d,face:%(helv)s" % faces)
        self.StyleSetSpec(stc.STC_P_COMMENTLINE,     "fore:#005F00,size:%(size)d,face:%(other)s" % faces)
        self.StyleSetSpec(stc.STC_P_NUMBER,          "fore:#007F7F,size:%(size)d" % faces)
        self.StyleSetSpec(stc.STC_P_STRING,          "fore:#7F007F,size:%(size)d,face:%(helv)s" % faces)
        self.StyleSetSpec(stc.STC_P_CHARACTER,       "fore:#7F007F,size:%(size)d,face:%(helv)s" % faces)
        self.StyleSetSpec(stc.STC_P_WORD,            "fore:#00007F,size:%(size)d,bold" % faces)
        self.StyleSetSpec(stc.STC_P_TRIPLE,          "fore:#7F0000,size:%(size)d" % faces)
        self.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE,    "fore:#7F0000,size:%(size)d" % faces)
        self.StyleSetSpec(stc.STC_P_CLASSNAME,       "fore:#007F7F,size:%(size)d,bold" % faces)
        self.StyleSetSpec(stc.STC_P_DEFNAME,         "fore:#007F7F,size:%(size)d,bold" % faces)
        self.StyleSetSpec(stc.STC_P_OPERATOR,        "fore:#000000,size:%(size)d,bold" % faces)
        self.StyleSetSpec(stc.STC_P_IDENTIFIER,      "fore:#000000,size:%(size)d,face:%(helv)s" % faces)
        self.StyleSetSpec(stc.STC_P_COMMENTBLOCK,    "fore:#7F7F7F,size:%(size)d" % faces)
        self.StyleSetSpec(stc.STC_P_STRINGEOL,       "fore:#000000,size:%(size)d,face:%(mono)s,back:#E0C0E0,eol" % faces)

        self.SetCaretForeground("DARK SLATE BLUE")

        self.Bind(stc.EVT_STC_UPDATEUI, self.OnUpdateUI)
        self.Bind(stc.EVT_STC_MARGINCLICK, self.OnMarginClick)


    #-------------------------------------------------------
    def OnUpdateUI(self, evt):
        # check for matching braces
        braceAtCaret = -1
        braceOpposite = -1
        charBefore = None
        caretPos = self.GetCurrentPos()

        if caretPos > 0:
            charBefore = self.GetCharAt(caretPos - 1)
            styleBefore = self.GetStyleAt(caretPos - 1)

        # check before
        if charBefore and chr(charBefore) in "[]{}()" and styleBefore == stc.STC_P_OPERATOR:
            braceAtCaret = caretPos - 1

        # check after
        if braceAtCaret < 0:
            charAfter = self.GetCharAt(caretPos)
            styleAfter = self.GetStyleAt(caretPos)

            if charAfter and chr(charAfter) in "[]{}()" and styleAfter == stc.STC_P_OPERATOR:
                braceAtCaret = caretPos

        if braceAtCaret >= 0:
            braceOpposite = self.BraceMatch(braceAtCaret)

        if braceAtCaret != -1  and braceOpposite == -1:
            self.BraceBadLight(braceAtCaret)
        else:
            self.BraceHighlight(braceAtCaret, braceOpposite)


    #-------------------------------------------------------
    def OnMarginClick(self, evt):
        # fold and unfold as needed
        if evt.GetMargin() == 2:
            if evt.GetShift() and evt.GetControl():
                self.FoldAll()
            else:
                lineClicked = self.LineFromPosition(evt.GetPosition())

                if self.GetFoldLevel(lineClicked) & stc.STC_FOLDLEVELHEADERFLAG:
                    if evt.GetShift():
                        self.SetFoldExpanded(lineClicked, True)
                        self.Expand(lineClicked, True, True, 1)
                    elif evt.GetControl():
                        if self.GetFoldExpanded(lineClicked):
                            self.SetFoldExpanded(lineClicked, False)
                            self.Expand(lineClicked, False, True, 0)
                        else:
                            self.SetFoldExpanded(lineClicked, True)
                            self.Expand(lineClicked, True, True, 100)
                    else:
                        self.ToggleFold(lineClicked)


    def FoldAll(self):
        lineCount = self.GetLineCount()
        expanding = True

        # find out if we are folding or unfolding
        for lineNum in range(lineCount):
            if self.GetFoldLevel(lineNum) & stc.STC_FOLDLEVELHEADERFLAG:
                expanding = not self.GetFoldExpanded(lineNum)
                break

        lineNum = 0

        while lineNum < lineCount:
            level = self.GetFoldLevel(lineNum)
            if level & stc.STC_FOLDLEVELHEADERFLAG and \
               (level & stc.STC_FOLDLEVELNUMBERMASK) == stc.STC_FOLDLEVELBASE:

                if expanding:
                    self.SetFoldExpanded(lineNum, True)
                    lineNum = self.Expand(lineNum, True)
                    lineNum = lineNum - 1
                else:
                    lastChild = self.GetLastChild(lineNum, -1)
                    self.SetFoldExpanded(lineNum, False)

                    if lastChild > lineNum:
                        self.HideLines(lineNum+1, lastChild)

            lineNum += 1



    def Expand(self, line, doExpand, force=False, visLevels=0, level=-1):
        lastChild = self.GetLastChild(line, level)
        line += 1

        while line <= lastChild:
            if force:
                if visLevels > 0:
                    self.ShowLines(line, line)
                else:
                    self.HideLines(line, line)
            else:
                if doExpand:
                    self.ShowLines(line, line)

            if level == -1:
                level = self.GetFoldLevel(line)

            if level & stc.STC_FOLDLEVELHEADERFLAG:
                if force:
                    if visLevels > 1:
                        self.SetFoldExpanded(line, True)
                    else:
                        self.SetFoldExpanded(line, False)

                    line = self.Expand(line, doExpand, force, visLevels-1)

                else:
                    if doExpand and self.GetFoldExpanded(line):
                        line = self.Expand(line, True, force, visLevels-1)
                    else:
                        line = self.Expand(line, False, force, visLevels-1)
            else:
                line += 1

        return line



## G_AnalyserScriptCtrl ####################################

_Message = """
The analyser script is currently being edited in an external editor.\r
The file name is '{}'.\r
To switch back to the internal editor, navigate to 'Event Name' -> Script and select Load.\r
You do not need to switch to the iternal editor in order to run the analyser.
"""
class G_AnalyserScriptCtrl(wx.SplitterWindow, G_DisplayControl):

    #-------------------------------------------------------
    def __init__(self, parent):
        # build a panel with the Python editor and a message window
        super().__init__(parent, style = wx.SP_LIVE_UPDATE)

        panel = G_PanelDisplayControl(self)
        sizer = self._Sizer = wx.BoxSizer(wx.VERTICAL)

        self._Editor = G_PythonTextCtrl(panel)
        sizer.Add(self._Editor, 1, wx.EXPAND)
        sizer.Show(self._Editor, False, recursive = True)

        self._Message = wx.TextCtrl(panel, style = wx.TE_MULTILINE | wx.TE_READONLY)
        sizer.Add(self._Message, 1, wx.EXPAND)
        
        panel.SetSizer(sizer)

        # now add the error window
        self._ErrorDisplay = wx.TextCtrl(self, style = wx.TE_MULTILINE | wx.TE_READONLY)

        preferred_sash = 150
        self.SetMinimumPaneSize(preferred_sash)
        self.SetSashGravity(1.0)

        self.SplitHorizontally(panel, self._ErrorDisplay, -preferred_sash)


    #-------------------------------------------------------
    def SetErrorText(self, new_text, is_error_msg):
        cur_text = ""

        fg_colour = G_ColourTraits.MakeColour(0)

        if is_error_msg:
            fg_colour = G_ColourTraits.MakeColour("FIREBRICK")
            cur_text = self._ErrorDisplay.GetLabel() + "================================================================================\r\n"

        text = cur_text + new_text.replace("\n", "\r\n")
        self._ErrorDisplay.SetLabel(text)
        self._ErrorDisplay.SetForegroundColour(fg_colour)


    #-------------------------------------------------------
    def SetMode(self, use_internal, filename):
        sizer = self._Sizer
        if use_internal:
            if sizer.IsShown(self._Editor):
                return
            else:
                sizer.Show(self._Editor, True, recursive = True)
                sizer.Show(self._Message, False, recursive = True)

        else:
            self._Message.SetLabelText(_Message.format(filename))
            if sizer.IsShown(self._Editor):
                sizer.Show(self._Editor, False, recursive = True)
                sizer.Show(self._Message, True, recursive = True)
            else:
                return

        sizer.Layout()


    #-------------------------------------------------------
    def GetEditor(self):
        return self._Editor

    def GetPythonText(self):
        return self._Editor.GetText()

    def SetPythonText(self, text):
        editor = self._Editor
        editor.SetText(text)
        editor.SetModified(False)

        editor.EmptyUndoBuffer()
        editor.Colourise(0, -1)

        editor.SetMarginType(1, stc.STC_MARGIN_NUMBER)
        editor.SetMarginWidth(1, 25)
   