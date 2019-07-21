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
import glob
from pathlib import Path
import re
import xml.etree.ElementTree as et

# wxWidgets imports
import wx

# Application imports
import Nlog
from .Project import G_Global



## G_Builder ################################################

class G_Builder:

    #-------------------------------------------------------
    def __init__(self, element):
        self._Name = element.get("name")
        self._LogTheme = element.find("./theme[@theme_cls='log']").text
        self._ViewThemes = [(e.get("factory"), e.get("theme_cls"), e.text) for e in element.iterfind("./theme[@factory]")]


    #-------------------------------------------------------
    def GetLogTheme(self):
        return self._LogTheme

    def GetViewThemes(self):
        # return factory guid, theme-id pairs
        return self._ViewThemes



## G_FieldSchema ############################################

class G_FieldSchema:
    """
    Schema for a logfile field
    """

    #-------------------------------------------------------
    def __init__(self, element):
        # description of the type (e.g. "uint08"), mainly used by the indexer
        self.Type = element.get("type")

        # the field's name; used in the UI and by the filter language
        self.Name = element.get("name")

        # character sequence following the field, and separating it from
        # the next field
        self.Separator = element.get("separator")
        self.SeparatorCount = 1
        self.MinWidth = 0
        self.Available = True

        # number of repeats of separator and/or minimum number of characters in
        # the field, two solutions for use when the field includes character(s)
        # the same as the separator
        sc = element.get("count")
        if sc is not None:
            self.SeparatorCount = int(sc)

        mw = element.get("minwidth")
        if mw is not None:
            self.MinWidth = int(mw)


## G_FieldList ##############################################

class G_FieldList(list):
    """A list of field schemata"""

    #-------------------------------------------------------
    def Append(self, field_schema):
        idx = len(self)
        self.append(field_schema)
        return idx



## G_FieldSchemata ##########################################

class G_FieldSchemata(G_FieldList):
    """
    A list of G_FieldSchema-like objects; with an Nlog compatible interface.
    """

    #-------------------------------------------------------
    def __init__(self, accessor_name, guid = ""):
        super().__init__()

        self._AccessorName = accessor_name
        self._Guid = guid
        self._RegexText = ""
        self._FormatterGuid = None

    def _SetTextOffsetSize(self, size):
        self._TextOffsetSize = size


    #-------------------------------------------------------
    def GetFormatter(self):
        if self._FormatterGuid is None:
            return G_Formatter()
        else:
            return GetFormatter(self._FormatterGuid)

    def MakeLogAccessor(self):
        """Make a LogAccessor, needed by NLog to read/interpret a logfile"""
        return Nlog.MakeLogAccessor(self, self.GetFormatter())


    #-------------------------------------------------------
    def GetFieldNames(self):
        return [fs.Name for fs in self if fs.Available]


    #-------------------------------------------------------
    # Nlog callback interface

    def GetAccessorName(self):
        return self._AccessorName

    def GetGuid(self):
        return self._Guid

    def GetMatchDesc(self):
        return self._RegexText

    def GetTextOffsetSize(self):
        return self._TextOffsetSize


    
## G_LogSchema ##############################################

class G_LogSchema(G_FieldSchemata):
    """
    Schema for a logfile
    """

    #-------------------------------------------------------
    # an extractor fetches a regular expression defined excerpt from a string
    class Extractor:
        def __init__(self, element):
            self._RE = None

            re_text = element.text
            if re_text:
                self._RE = re.compile(re_text)


        # extract/convert locator information from the emitter field value
        # returns the last matched group in the regular expression, or, where no
        # group was defined (i.e. no parenthesis), returns the whole match
        def Apply(self, text):
            if self._RE is None:
                return "-"
            
            match = self._RE.search(text)
            if not match:
                return "?"

            group = match.lastindex
            if group is None:
                group = 0

            return match.group(group)


    #-------------------------------------------------------
    # think really simple "sed"
    class Substitutor:
        def __init__(self, element):
            self._RE = re.compile(element.get("from"))
            self._To = element.get("to")

        def Apply(self, text):
            return re.sub(self._RE, self._To, text)


    #-------------------------------------------------------
    def __init__(self, element):
        super().__init__("map")

        self._Name = element.get("name")
        self._Guid = element.get("guid")
        self._Desc = element.find("description").text
        self._Ext = element.find("extension").text

        offsetsize = 8
        elem = element.find("textoffsetsize")
        if elem is not None:
            offsetsize = int(elem.text)
        self._SetTextOffsetSize(offsetsize)

        self._ChannelGuid = None
        elem = element.find("channel")
        if elem is not None:
            self._ChannelGuid = elem.text

        self._FormatterGuid = None
        elem = element.find("formatter")
        if elem is not None:
            self._FormatterGuid = elem.text

        self._DefaultThemes = {}
        for t in element.iterfind("theme"):
            self._DefaultThemes.update([(t.get("theme_cls"), t.text)])

        self._Builders = None
        elem = element.find("builders")
        if elem is not None:
            builders = self._Builders = G_XmlStore("builder", G_Builder)
            builders.AppendXml(elem)

        self._RegexText = ""
        match = element.find("regex")
        if match is not None:
            self._RegexText = match.text

        for f in element.iterfind("field"):
            self.append(G_FieldSchema(f))

        # determine whether the schema includes emitter information
        self._EmitterId = -1
        for (idx, field_schema) in enumerate(self):
            if field_schema.Type == "emitter":
                self._EmitterId = idx
                break

        if self._EmitterId < 0:
            return

        # if an emitter field exists, fetch the extractors which convert the
        # raw emitter data into a (possibly partial) source locator
        self._Substitutions = [__class__.Substitutor(f) for f in element.iterfind("source_subst")]

        self.ExtractorPathRE = __class__.Extractor(element.find("source_path"))
        self.ExtractorLineRE = __class__.Extractor(element.find("source_line"))


    #-------------------------------------------------------
    def GetBuilders(self):
        # builders are optional, so this routine can return None
        return self._Builders

    def GetBuildersNameGuidList(self):
        builders = self.GetBuilders()
        if builders is None:
            return []
        else:
            return builders.GetNameGuidList()

    def GetChannelGuid(self):
        return self._ChannelGuid
            
    def GetEffectiveChannelGuid(self):
        if self._ChannelGuid is not None:
            return self._ChannelGuid
        else:
            return "8C8F999F-6448-4482-84C4-31DFAFFF7EE4"

    def GetDefaultTheme(self, theme_cls):
        if theme_cls in self._DefaultThemes:
            return self._DefaultThemes[theme_cls]
        else:
            return None

    def GetExtension(self):
        return self._Ext

    def GetName(self):
        return self._Name

    def GetEmitterId(self):
        """Fetch the field ID of any 'emitter' field; -1 if none found"""
        return self._EmitterId

    #-------------------------------------------------------
    def GetUserDescription(self):
        """Fetch a human readable description of the log Schema"""
        desc = self._Desc + ". Field names and types are:\n"
        for field in self._FieldSchemata:
            fld = ". " + field.Name + " (" + field.Type + ")\n"
            desc = desc + fld
        return desc


    #-------------------------------------------------------
    def CreateLineNotificationMessage(self, log_line, emitter_text):
        """Create a channel notification message for the supplied log line"""

        # build the message
        for s in self._Substitutions:
            emitter_text = s.Apply(emitter_text)

        root = et.Element("root")
        et.SubElement(root, "path").text = self.ExtractorPathRE.Apply(emitter_text)
        et.SubElement(root, "line").text = self.ExtractorLineRE.Apply(emitter_text)
        et.SubElement(root, "log").text = log_line
        et.SubElement(root, "emitter").text = emitter_text

        return et.tostring(root, encoding="unicode")



## G_NumGenerator ###########################################

class G_NumGenerator:
    # simple class to allocate a series of style numbers

    def __init__(self, start):
        self._Count = start

    def Get(self):
        self._Count += 1
        return self._Count



## G_Style ##################################################

class G_Style:
    #-------------------------------------------------------
    def __init__(self, generator, element):
        self._StyleNumber = generator.Get()
        self._Bold = self._Italic = self._Underline = 0
        self._ForeColour = "BLACK"

        elem = element.find("bold")
        if elem is not None:
            self._Bold = int(elem.text)

        elem = element.find("italic")
        if elem is not None:
            self._Italic = int(elem.text)

        elem = element.find("underline")
        if elem is not None:
            self._Underline = int(elem.text)

        elem = element.find("fore")
        if elem is not None:
            self._ForeColour = elem.text


    #-------------------------------------------------------
    def GetStyleNumber(self):
        return self._StyleNumber

    def IsBold(self):
        return self._Bold != 0

    def IsItalic(self):
        return self._Italic != 0

    def IsUnderline(self):
        return self._Underline != 0

    def ForeColour(self):
        from .StyleNode import G_ColourTraits
        return G_ColourTraits.GetColour(self._ForeColour)



## G_StyleSet ###############################################

class G_StyleSet:
    #-------------------------------------------------------
    def __init__(self, element):
        
        g = G_NumGenerator(50)

        self._Styles = dict(
            [(s.get("name"), G_Style(g, s)) for s in element.iterfind("style")]
        )


    #-------------------------------------------------------
    def GetStyles(self):
        return self._Styles.values()

    def GetStyleByName(self, name):
        return self._Styles[name]



## G_Format #################################################

class G_Format:
    #-------------------------------------------------------
    def __init__(self, element, styleset):
        self.RegexText = element.find("regex").text
        self.StyleNumbers = [styleset.GetStyleByName(e.text).GetStyleNumber() for e in element.findall("style")]



## G_Formatter ##############################################

class G_Formatter(list):

    #-------------------------------------------------------
    def __init__(self, element = None):
        self._StyleSet = None
        if element is None:
            return

        styleset = self._StyleSet = GetStyleSet(element.find("styleset").text)
        for f in element.iterfind("format"):
            self.append(G_Format(f, styleset))


    #-------------------------------------------------------
    def GetStyleSet(self):
        return self._StyleSet



## G_XmlStore ###############################################

class G_XmlStore:
    """
    Storage for holding and collecting read-only data, potentially
    supplied via one or more XML files distributed accross one
    or more directories.
    """

    #-------------------------------------------------------
    def __init__(self, store_name, factory):
        # cached list of objects corresponding to XML elements
        self._Objects = dict()

        # the store_name is both the root of the filename and the
        # top level XML element name within the file
        self._StoreName = store_name

        # factory (class) for building objects from XML elements
        self._Factory = factory

        # XML tree for the collected data
        self._XmlTree = None


    #-------------------------------------------------------
    def AppendDir(self, directory):
        """
        Add XML files to the stored XML 'database'. Scans all qualifying
        files in the supplied directory, collecting all relevent top-
        level XML elements into the store.
        """

        store = self._GetStore()
        store_name = self._StoreName
        file_glob = store_name + "*.xml"

        for file in glob.glob(str(directory / file_glob)):
            store.extend(et.parse(file).getroot().findall(store_name))


    #-------------------------------------------------------
    def AppendXml(self, element):
        """
        Add an XML element from some other XML file to this store
        """
        self._MakeStore()
        store = self._XmlTree
        store_name = self._StoreName
        store.extend(element.findall(store_name))


    #-------------------------------------------------------
    def _MakeStore(self):
        if self._XmlTree is None:
            self._XmlTree = et.Element("root")
            return True
        else:
            return False

    def _GetStore(self):
        """ Fetch the initialised store """

        # If required, initialise the store by scanning XML files in the default
        # data directory; can't be done earlier, as the wx.ConfigBase lookup
        # requires wx.App to exist
        if self._MakeStore():
            self.AppendDir(Path(G_Global.GetConfigDir()))

        return self._XmlTree


    #-------------------------------------------------------
    def GetElementByGuid(self, guid):
        xpath = "./{}[@guid='{}']".format(self._StoreName, guid)
        return self._GetStore().find(xpath)
 

   #-------------------------------------------------------
    def GetObjectByGuid(self, guid):
        """Fetch an object describing an XML element"""
    
        if not guid in self._Objects:
            object = None
            element = self.GetElementByGuid(guid)
            if element is not None:
                object = self._Factory(element)

            self._Objects.update([(guid, object)])

        return self._Objects[guid]


   #-------------------------------------------------------
    def GetNameGuidList(self):
        """Fetch list of pairs (name, guid), sorted by name"""
        def Key(element):
            return element.get("name")

        return [(e.get("name"), e.get("guid"))
             for e in sorted(self._GetStore().iterfind(self._StoreName), key = Key)]



## PRIVATE ##################################################

_XmlDb = {
    "schema": G_XmlStore("schema", G_LogSchema),
    "styleset": G_XmlStore("styleset", G_StyleSet),
    "formatter": G_XmlStore("formatter", G_Formatter)
}



## MODULE ##################################################

def RegisterLogSchemata(directory):
    global _XmlDb
    for store in _XmlDb.values():
        store.AppendDir(directory)


def GetLogSchemataNames():

    global _XmlDb
    return _XmlDb["schema"].GetNameGuidList()


def GetLogSchema(guid):
    """Fetch a G_LogSchema object describing the schema"""

    global _XmlDb
    return _XmlDb["schema"].GetObjectByGuid(guid)
    

def GetFormatterNames():

    global _XmlDb
    return _XmlDb["formatter"].GetNameGuidList()

def GetFormatter(guid):
    global _XmlDb
    return _XmlDb["formatter"].GetObjectByGuid(guid)


def GetStyleSetNames():

    global _XmlDb
    return _XmlDb["styleset"].GetNameGuidList()

def GetStyleSet(guid):
    global _XmlDb
    return _XmlDb["styleset"].GetObjectByGuid(guid)
