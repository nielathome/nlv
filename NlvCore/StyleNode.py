#
# Copyright (C) Niel Clausen 2017-2019. All rights reserved.
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
import wx.adv
import wx.lib.colourdb
from wx.lib.expando import ExpandoTextCtrl
from wx.lib.scrolledpanel import ScrolledPanel

# Application imports
from .Global import G_Const
from .Global import G_FrozenWindow
from .Project import G_WindowInfo



## PRIVATE #################################################

#-----------------------------------------------------------
def ListToNames(list):
    """
    For a list of sub-lists, build a new list which is the first
    entry of each sub-list.
    """

    names = []
    for sublist in list:
        names.append(sublist[0])
    return names


#-----------------------------------------------------------
def GetListIndex(list, name):
    """
    For a list of sub-lists, fetch the index of the sub-list
    whose first entry is the supplied name. If the name is not
    found, returns 0.
    """

    idx = 0
    for sublist in list:
        if sublist[0] == name:
            return idx
        idx += 1

    return 0
            


## G_ColourTraits ##########################################

class G_ColourTraits:
    """Colour traits - fully static class"""

    _Colours = []


    #-------------------------------------------------------
    def _Init():
        duplicates = set()
        clist = wx.lib.colourdb.getColourInfoList()
        for centry in clist:
            # truncate at SNOW1; thats 129 colours already, don't need 250 more
            if centry[0] == "SNOW1":
                break

            # filter out duplicates
            col = wx.Colour(centry[1], centry[2], centry[3])
            rgb = col.GetRGB()

            if rgb in duplicates:
                continue
            duplicates.add(rgb)

            # keep colour (name, colour pairs)
            __class__._Colours.append([centry[0], col])


    #-------------------------------------------------------
    def CalcTextColour(colour_idx):
        # identify a suitable contrasting colour for the background
        # invert = True swaps the contrast (equivalent to "don't contrast")
        bc = __class__._Colours[colour_idx][1]

        # calculate an average "intensity"
        import math as m
        ss = m.pow(bc.Red(),2) + m.pow(bc.Green(),2) + m.pow(bc.Blue(),2)
        want_light = (m.sqrt(ss) / 3) < 80

        if want_light:
            return wx.Colour(192, 192, 192)
        else:
            return wx.Colour(64, 64, 64)


    #-------------------------------------------------------
    def GetColourByIndex(index):
        return __class__._Colours[index][1]

    def GetColourNames():
        return ListToNames(__class__._Colours)


    #-------------------------------------------------------
    def GetColourIndex(colour_name):
        return GetListIndex(__class__._Colours, colour_name)

    def GetColour(colour_name):
        return __class__.GetColourByIndex(__class__.GetColourIndex(colour_name))


    #-------------------------------------------------------
    def MakeColour(colour_id):
        """Create a wxColour instance by name of BGR"""
        if isinstance(colour_id, int):
            return wx.Colour(colour_id)
        elif isinstance(colour_id, str):
            return __class__.GetColour(colour_id)
        elif isinstance(colour_id, wx.Colour):
            return colour_id
        else:
            raise RuntimeError("Unrecognised colour ID")


G_ColourTraits._Init()



## G_ColourCombo ###########################################

class G_ColourCombo(wx.adv.OwnerDrawnComboBox):

    #-------------------------------------------------------
    def __init__(self, parent, id = wx.ID_HIGHEST):
        col_names = G_ColourTraits.GetColourNames()
        super().__init__(parent, choices = col_names, style = wx.CB_READONLY, size = (150, -1), id = id)


    #-------------------------------------------------------
    def OnDrawBackground(self, dc, rect, item, flags):
        colour = G_ColourTraits.GetColourByIndex(item)
        dc.SetBrush(wx.Brush(colour))

        if flags & wx.adv.ODCB_PAINTING_SELECTED:
            dc.SetPen(wx.BLACK_PEN)
        else:
            dc.SetPen(wx.Pen(colour))

        dc.DrawRectangle(rect)


    #-------------------------------------------------------
    def OnDrawItem(self, dc, rect, item, flags):
        if item == wx.NOT_FOUND:
            return

        xoffset = G_Const.Sizer_StdBorder
        yoffset = (rect.height - dc.GetCharHeight()) / 2
        dc.SetTextForeground(G_ColourTraits.CalcTextColour(item))
        dc.DrawText(self.GetString( item ), rect.x + xoffset, rect.y + yoffset)


    #-------------------------------------------------------
    def OnMeasureItem(self, item):
        return G_Const.ComboRowHeight # Item height



## G_ColourNode ############################################

class G_ColourNode:
    """Helper class to extend nodes with UI support for colour selection"""

    #-------------------------------------------------------
    def BuildColour(me, page):
        # class static function
        me._ColourCombo = G_ColourCombo(page.GetWindow())
        me.BuildLabelledRow(page, "Colour:", me._ColourCombo)


    #-------------------------------------------------------
    def PostInitColour(self):
        self.OnColour(False)


    #-------------------------------------------------------
    def ActivateColour(self):
        combo = self._ColourCombo
        combo.Unbind(wx.EVT_COMBOBOX)
        combo.SetSelection(G_ColourTraits.GetColourIndex(self._Field.ColourName.Value))
        combo.Bind(wx.EVT_COMBOBOX, self.OnColourCombo)


    #-------------------------------------------------------
    def OnColourCombo(self, event):
        """Action the colour selection; derived class must implement OnColour"""
        self._Field.ColourName.Value = self._ColourCombo.GetValue()
        self.OnColour(True)

    def GetColour(self):
        return G_ColourTraits.GetColour(self._Field.ColourName.Value)


    #-------------------------------------------------------
    def SetColourTheme(self):
        """Set the colour programatically"""
        self.PostInitColour()



## G_EnabledColourRow ######################################

class G_EnabledColourRow:
    """
    Single "row" in a G_EnabledColourNode. This is either a
    checkbox (show) colour pair, or the pair supplemented
    with the field's full description.
    """

    #-------------------------------------------------------
    def __init__(self, cls, panel, bg_colour, show_id):
        self._Label = ""
        window = panel.GetWindow()
        sizer = panel.GetSizer()

        line = self._StaticLine = wx.StaticLine(window)
        sizer.Add(line, flag = wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, border = G_Const.Sizer_StdBorder)

        checkbox = self._ShowColumnCheckBox = wx.CheckBox(window, id = show_id)
        combo = self._ColumnColourCombo = G_ColourCombo(window, show_id)
        self._RowSizer = cls.BuildRow(panel, checkbox, combo, "enabled-colour-row-{}".format(show_id))

        description = self._DescriptionCtrl = ExpandoTextCtrl(window, style = wx.TE_MULTILINE
            | wx.TE_NO_VSCROLL
            | wx.TE_READONLY
            | wx.TE_RICH2
            | wx.BORDER_NONE)
    
        description.SetBackgroundColour(bg_colour)
        sizer.Add(description, flag = wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, border = G_Const.Sizer_StdBorder, userData = "enabled-colour-description-{}".format(show_id))


    #-------------------------------------------------------
    def Bind(self, onshow, description_text, visible, oncolour, colour_name, title_attr, normal_attr):
        label, desc = description_text
        if desc is None:
            desc = "The plugin creator has not provided a description for this field"

        self._Label = label
        checkbox = self._ShowColumnCheckBox
        checkbox.Unbind(wx.EVT_CHECKBOX)
        checkbox.SetValue(visible)
        checkbox.Bind(wx.EVT_CHECKBOX, onshow)

        combo = self._ColumnColourCombo
        combo.SetSelection(G_ColourTraits.GetColourIndex(colour_name))
        combo.Bind(wx.EVT_COMBOBOX, oncolour)

        description = self._DescriptionCtrl
        description.SetDefaultStyle(title_attr)
        description.SetValue("")
        description.WriteText(label)
        description.SetDefaultStyle(normal_attr)
        description.WriteText(" - " + desc)

    def Unbind(self):
        self._ShowColumnCheckBox.Unbind(wx.EVT_CHECKBOX)
        self._ColumnColourCombo.Unbind(wx.EVT_COMBOBOX)


    #-------------------------------------------------------
    def Show(self, parent_sizer, show, with_description):
        label = "Show"
        if not with_description:
            label = self._Label
        self._ShowColumnCheckBox.SetLabel(label)

        parent_sizer.Show(self._StaticLine, show and with_description)
        parent_sizer.Show(self._RowSizer, show)
        parent_sizer.Show(self._DescriptionCtrl, show and with_description)



## G_EnabledColourNode #####################################

class G_EnabledColourNode:
    """Helper class to extend nodes with UI support for enabling and colour selection"""

    cMaxNumRows = 20

    #-------------------------------------------------------
    def BuildEnabledColour(me, page):
        # class static function
        me._ShowDescriptionsCheckBox = wx.CheckBox(page.GetWindow())
        me.BuildLabelledRow(page, "Show Descriptions", me._ShowDescriptionsCheckBox)
        
        scroll_panel = G_WindowInfo.MakePane(page.GetWindow(), ScrolledPanel)
        me._ScrollPanelSizer = sizer = scroll_panel.GetSizer()
        window = scroll_panel.GetWindow()
        page.GetSizer().Add(window, proportion = 1, flag = wx.EXPAND, userData = "G_EnabledColourNode")

        me._Rows = []
        bg_colour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)    
        for i in range(0, me.cMaxNumRows):
            row = G_EnabledColourRow(me, scroll_panel, bg_colour, wx.ID_HIGHEST + i)
            me._Rows.append(row)
    
        window.SetupScrolling()


    #-------------------------------------------------------
    def PostInitColour(self):
        self._Field.Add(__class__.cMaxNumRows, "NumActive", replace_existing = False)
        self._Field.Add(True, "ShowDescriptions", replace_existing = False)
        self.OnColours()
        self.OnEnable()


    #-------------------------------------------------------
    def OverrideSettings(self, settings):
        """Allow programmatic update of colours and visibility"""
        for field_id, setting in enumerate(settings):
            visibility, colour = setting
            self.UpdateColour(field_id, colour)
            self.UpdateVisibility(field_id, visibility)

        self.OnColours()
        self.OnEnable()

        
    #-------------------------------------------------------
    def BindEnabledColour(self, num_controls, visibility, colour_names, descriptions):
        # ensure control width's are set, before text controls resize
        self._Sizer.Layout()

        title_attr = wx.TextAttr()
        title_attr.SetFontFaceName(G_Const.FontFaceName)
        title_attr.SetFontStyle(wx.FONTSTYLE_ITALIC)
        title_attr.SetFontPointSize(9)

        normal_attr = wx.TextAttr()
        normal_attr.SetFontFaceName(G_Const.FontFaceName)
        normal_attr.SetFontStyle(wx.FONTSTYLE_NORMAL)
        normal_attr.SetFontPointSize(9)

        for i in range(0, num_controls):
            self._Rows[i].Bind(self.OnCheckBox, descriptions[i], visibility[i], self.OnColourCombo, colour_names[i], title_attr, normal_attr)

        for i in range(num_controls, __class__.cMaxNumRows):
            self._Rows[i].Unbind()


    def ShowEnabledColour(self, num_controls, show_descriptions):
        # handle visible controls
        for i in range(0, num_controls):
            self._Rows[i].Show(self._ScrollPanelSizer, True, show_descriptions)

        # hide excess controls
        for i in range(num_controls, __class__.cMaxNumRows):
            self._Rows[i].Show(self._ScrollPanelSizer, False, False)

        # ensure revisions to text control sizes are correct, and
        # fed back into the scroll pane
        self._Sizer.Layout()


    def ActivateEnabledColour(self, descriptions):
        num_controls = self._Field.NumActive.Value = len(descriptions)
        show_descriptions = self._Field.ShowDescriptions.Value
        visibility = self._Field.Visibility.Value
        colour_names = self._Field.ColourNames.Value

        check = self._ShowDescriptionsCheckBox
        check.Unbind(wx.EVT_CHECKBOX)
        check.SetValue(show_descriptions)
        check.Bind(wx.EVT_CHECKBOX, self.OnShowDescriptions)

        self.BindEnabledColour(num_controls, visibility, colour_names, descriptions)
        self.ShowEnabledColour(num_controls, show_descriptions)


    #-------------------------------------------------------
    def UpdateVisibility(self, field_id, value):
        visibility = self._Field.Visibility.Value
        visibility[field_id] = value
        self._Field.Visibility.Value = visibility

    def OnCheckBox(self, event):
        """Action the enable box; derived class must implement OnEnable"""
        self.UpdateVisibility(event.GetId() - wx.ID_HIGHEST, event.IsChecked())
        self.OnEnable()

    def UpdateColour(self, field_id, colour_name):
        colour_names = self._Field.ColourNames.Value
        colour_names[field_id] = colour_name
        self._Field.ColourNames.Value = colour_names

    def OnColourCombo(self, event):
        """Action the colour selection; derived class must implement OnColour"""
        field_id = event.GetId() - wx.ID_HIGHEST
        self.UpdateColour(field_id, event.EventObject.GetValue())
        self.OnColour(field_id)

    def OnColours(self):
        for i in range(0, self.GetNumActive()):
            self.OnColour(i)

    def OnShowDescriptions(self, event):
        """Show/hide the field descriptions"""
        num_controls = self._Field.NumActive.Value
        show_descriptions = self._Field.ShowDescriptions.Value = event.IsChecked()

        # the freeze seems to be needed to prevent unwanted
        # drawing artefacts splattered over the display when the scroll
        # bar is not at the top of its travel
        with G_FrozenWindow(self._ScrollPanelSizer.GetContainingWindow()):
            self.ShowEnabledColour(num_controls, show_descriptions)


    #-------------------------------------------------------
    def GetColour(self, field_id):
        colour_names = self._Field.ColourNames.Value
        if field_id >= len(colour_names):
            field_id = 0
        return G_ColourTraits.GetColour(colour_names[field_id])
    

    def GetEnabledAsMask(self):
        field_mask = 0
        field_bit = 1
        visibility = self._Field.Visibility.Value

        for i in range(0, self.GetNumActive()):
            if visibility[i]:
                field_mask |= field_bit
            field_bit <<= 1

        return field_mask


    def GetNumActive(self):
        return self._Field.NumActive.Value


    #-------------------------------------------------------
    def SetEnabledColourTheme(self):
        self.PostInitColour()



## G_StyleTraits ###########################################

class G_StyleTraits:
    """Style traits"""

    #-------------------------------------------------------
    #_Styles =
    #   [
    #      0 = name,
    #      1 = pen_style,
    #      2 = Scintilla data or style,
    #      3 = foreground colour (optional, defaults to black)
    #      4 = background colour (optional, defaults to white)
    #   ]

    #-------------------------------------------------------
    def __init__(self, styles):
        self._Styles = styles


    #-------------------------------------------------------
    def GetNumStyles(self):
        return len(self._Styles)

    def GetStyleNames(self):
        return ListToNames(self._Styles)

    def GetStyleIndex(self, style_name):
        return GetListIndex(self._Styles, style_name)

    def GetDataByIndex(self, index):
        return self._Styles[index][2]
    def GetIndexByData(self, data):
        for index in range(len(self._Styles)):
            if self._Styles[index][2] == data:
                return index
        return -1

    def GetPenByIndex(self, index):
        return self._Styles[index][1]

    def GetForegroundColourByIndex(self, index):
        style = self._Styles[index]
        if len(style) <= 3:
            return wx.BLACK
        else:
            return style[3]

    def GetBackgroundColourByIndex(self, index):
        style = self._Styles[index]
        if len(style) <= 4:
            return wx.WHITE
        else:
            return style[4]


    #-------------------------------------------------------
    def GetData(self, style_name):
        return self.GetDataByIndex(self.GetStyleIndex(style_name))



## G_StyleCombo ############################################

class G_StyleCombo(wx.adv.OwnerDrawnComboBox):

    #-------------------------------------------------------
    def __init__(self, parent, traits):
        self._Traits = traits
        style_names = traits.GetStyleNames()
        super().__init__(parent, choices = style_names, style = wx.CB_READONLY, size = (150, -1))


    #-------------------------------------------------------
    def OnDrawBackground(self, dc, rect, item, flags):
        outline_colour = bg_colour = self._Traits.GetBackgroundColourByIndex(item)
        if flags & wx.adv.ODCB_PAINTING_SELECTED:
            outline_colour = wx.BLACK

        dc.SetPen(wx.Pen(outline_colour))
        dc.SetBrush(wx.Brush(bg_colour))
        dc.DrawRectangle(rect)


    #-------------------------------------------------------
    def OnDrawItem(self, dc, rect, item, flags):
        if item == wx.NOT_FOUND:
            # no item selected yet
            return

        text = self.GetString(item)
        extent = dc.GetTextExtent(text)

        centre = rect.height / 2
        xoffset = G_Const.Sizer_StdBorder
        yoffset = centre - extent.y / 2
        dc.SetTextForeground(self._Traits.GetForegroundColourByIndex(item))
        dc.DrawText(text, rect.x + xoffset, rect.y + yoffset)

        pen_style = self._Traits.GetPenByIndex(item)
        if pen_style == wx.PENSTYLE_TRANSPARENT:
            return

        y = rect.y + centre
        xgap = 10
        dc.SetPen(wx.Pen(wx.BLACK, 3, pen_style))
        dc.DrawLine(rect.x + xoffset + extent.x + xgap, y, rect.x + rect.width - xoffset, y)


    #-------------------------------------------------------
    def OnMeasureItem(self, item):
        return G_Const.ComboRowHeight # Item height



## G_StyleNode #############################################

class G_StyleNode:
    """Helper class to extend nodes with UI support for line/box style selection"""

    #-------------------------------------------------------
    def __init__(self, style_traits):
        self._StyleTraits = style_traits

    def PostInitStyle(self):
        self.OnStyle(False)


    #-------------------------------------------------------
    def GetStyle(self):
        return self._StyleTraits.GetData(self._Field.StyleName.Value)

    def GetStyleIndex(self):
        return self._StyleTraits.GetStyleIndex(self._Field.StyleName.Value)


    #-------------------------------------------------------
    def ActivateStyle(self):
        combo = self._StyleCombo
        combo.Unbind(wx.EVT_COMBOBOX)
        combo.SetSelection(self.GetStyleIndex())
        combo.Bind(wx.EVT_COMBOBOX, self.OnStyleCombo)


    #-------------------------------------------------------
    def OnStyleCombo(self, event):
        """Action the style selection; derived class must implement OnStyle"""
        self._Field.StyleName.Value = self._StyleCombo.GetValue()
        self.OnStyle(True)


    #-------------------------------------------------------
    def SetStyleByData(self, data):
        """Set the style to match the supplied data value, do not issue a style event"""
        traits = self._StyleTraits
        index = traits.GetIndexByData(data)
        self._Field.StyleName.Value = traits.GetStyleNames()[index]
        self.ActivateStyle()
        

    #-------------------------------------------------------
    def SetStyleTheme(self):
        """Set the style programatically"""
        self.PostInitStyle()



## G_HiliteStyleNode #######################################

class G_HiliteStyleNode(G_StyleNode):

    #-------------------------------------------------------
    _Styles = [
        # [ 0 = name, 1 = pen_style, 2 = Scintilla indicator style]
        ["Box", wx.PENSTYLE_TRANSPARENT, wx.stc.STC_INDIC_ROUNDBOX],
        ["Strike", wx.PENSTYLE_SOLID, wx.stc.STC_INDIC_STRIKE],
        ["Dash", wx.PENSTYLE_SHORT_DASH, wx.stc.STC_INDIC_DASH],
        ["Diagonal", wx.PENSTYLE_BDIAGONAL_HATCH, wx.stc.STC_INDIC_DIAGONAL],
        ["Squiggle", wx.PENSTYLE_CROSSDIAG_HATCH, wx.stc.STC_INDIC_SQUIGGLEPIXMAP]
    ]

    _Traits = G_StyleTraits(_Styles)


    #-------------------------------------------------------
    def __init__(self):
        super().__init__(__class__._Traits)


    #-------------------------------------------------------
    def BuildStyle(me, page):
        # class static function
        me._StyleCombo = G_StyleCombo(page.GetWindow(), __class__._Traits)
        me.BuildLabelledRow(page, "Style:", me._StyleCombo)



## G_MarkerStyleNode #######################################

class G_MarkerStyleNode(G_StyleNode):

    #-------------------------------------------------------
    _Styles = [
        # [ 0 = name, 1 = pen_style, 2 = Scintilla marker symbol]
        ["Bookmark", wx.PENSTYLE_TRANSPARENT, wx.stc.STC_MARK_BOOKMARK],
        ["Left Rectangle", wx.PENSTYLE_TRANSPARENT, wx.stc.STC_MARK_LEFTRECT],
        ["Small Rectangle", wx.PENSTYLE_TRANSPARENT, wx.stc.STC_MARK_SMALLRECT],
        ["Plus (+)", wx.PENSTYLE_TRANSPARENT, wx.stc.STC_MARK_PLUS],
        ["Minus (-)", wx.PENSTYLE_TRANSPARENT, wx.stc.STC_MARK_MINUS]
    ]

    _Traits = G_StyleTraits(_Styles)


    #-------------------------------------------------------
    def __init__(self):
        super().__init__(__class__._Traits)


    #-------------------------------------------------------
    def BuildStyle(me, page):
        # class static function
        me._StyleCombo = G_StyleCombo(page.GetWindow(), __class__._Traits)
        me.BuildLabelledRow(page, "Style:", me._StyleCombo)



## G_TrackerStyleNode ######################################

class G_TrackerStyleNode(G_StyleNode):

    #-------------------------------------------------------
    _Styles = [
        # [ 0 = name, 1 = pen_style, 2 = Scintilla marker symbol]
        ["Arrow Head", wx.PENSTYLE_TRANSPARENT, wx.stc.STC_MARK_ARROW],
        ["Arrow", wx.PENSTYLE_TRANSPARENT, wx.stc.STC_MARK_SHORTARROW],
        ["Chevron (>>>)", wx.PENSTYLE_TRANSPARENT, wx.stc.STC_MARK_ARROWS],
        ["Ellipses (...)", wx.PENSTYLE_TRANSPARENT, wx.stc.STC_MARK_DOTDOTDOT],
        ["Arrow Down", wx.PENSTYLE_TRANSPARENT, wx.stc.STC_MARK_ARROWDOWN]
    ]

    _Traits = G_StyleTraits(_Styles)


    #-------------------------------------------------------
    def __init__(self):
        super().__init__(__class__._Traits)


    #-------------------------------------------------------
    def BuildStyle(me, page):
        # class static function
        me._StyleCombo = G_StyleCombo(page.GetWindow(), __class__._Traits)
        me.BuildLabelledRow(page, "Style:", me._StyleCombo)
