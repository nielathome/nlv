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
import types
from weakref import ref as MakeWeakRef
import xml.etree.ElementTree as et

# Application imports
from .Theme import GetThemeGallery



## D_Document ##############################################

class D_Document:
    """
    A factory for creating D_* objects which access XML elements in
    the project's underlying document.
    """

    #-------------------------------------------------------
    class D_Value:
        """Base class for persistable objects"""
        pass


    #-------------------------------------------------------
    # document type identifiers, also used as XML element tags
    DocTypeField = "field"
    DocTypeObject = "object"
    DocTypeArray = "array"
    DocTypeNode = "node"

    # map Type* identifiers to matching D_* class
    _DocClasses = {}

    def ValueToDocClass(value):
        """Identify the correct D_* class for the given value"""
        for key, cls in __class__._DocClasses.items():
            if cls._IsHandler(value):
                return cls
        raise TypeError

    def DocTypeToClass(doc_type):
        """Map an XML tag to a D_* class"""
        return __class__._DocClasses[doc_type]

    def RegisterDocClass(doc_type, cls):
        __class__._DocClasses[doc_type] = cls


    #-------------------------------------------------------
    def __new__(cls, element, node):
        # create a class defined by the element's tag ("type") name
        return D_Document.DocTypeToClass(element.tag)(element, MakeWeakRef(node))



## D_Base ##################################################

class D_Base:
    """Base class for document items"""

    #-------------------------------------------------------
    def _Create(parent, replace_existing, at_front, tag, **kwargs):
        """Create a new item in the document tree"""

        # determine element's name
        name = None
        if "name" in kwargs:
            # not all paths through the code result in valid names
            # cleanup here
            name = kwargs["name"]
            if name is None:
                del kwargs["name"]

        # find any existing element
        element = None
        if name is not None:
            xpath = "./*[@name='{}']".format(name)
            element = parent.find(xpath)

        # delete existing element if requested
        if element is None:
            write = True
        else:
            write = False
            if replace_existing:        
                write = True
                parent.remove(element)
                element = None

        # if no existing element, create a new one
        if element is None:
            element = et.Element(tag, **kwargs)
            if at_front:
                parent.insert(0, element)
            else:
                parent.append(element)

        return (write, element)


    #-------------------------------------------------------
    def __init__(self, element, wnode):
        self._Element = element
        self._WNode = wnode


    #-------------------------------------------------------
    def _Reset(self):
        """Reset the document element; only preserves name attribute"""

        element = self._Element
        name = element.get("name")
        element.clear()
        if name is not None:
            element.set("name", name)

        return element


    #-------------------------------------------------------
    def _LookupThemeId(node, theme_cls):
        """(Static) Search upwards in the XML for the theme ID, and return its value"""

        # In fact, the ElementTree API will only search downwards from a given start
        # node, which is why we keep a back reference to the calling node - as we use
        # the explorer tree to navigate upwards

        while node is not None:
            base_element = node.GetDocument().find("./field[@name='ThemeNode'][@theme_cls='{}']".format(theme_cls))

            if base_element is not None:
                gallery_factory_id = base_element.text
                gallery_node = node.FindChildNode(factory_id = gallery_factory_id, recursive = True)

                # document can be null during application shutdown
                document = gallery_node.GetDocument()
                theme_id = None
                if document is not None:
                    theme_id = document.find("./field[@name='CurrentThemeId']").text

                    # map no theme to theme not found
                    if theme_id == "":
                        theme_id = None

                return theme_id

            node = node.GetParentNode()

        return None


    #-------------------------------------------------------
    def _GetThemeInfo(node, element):
        """(Static) Identify the theme associated with a given field"""

        # if the override attribute is not present, the field has no theme
        res = (None, None)
        override = element.get("override")
        if override is None:
            return res

        # where the override is present, but not "0", the value is not currently subject
        # to the theme
        if override != "0":
            return res

        # identify the theme's class
        theme_cls = element.get("theme_cls")
        if theme_cls is None:
            return res

        theme_id = __class__._LookupThemeId(node, theme_cls)
        return (theme_cls, theme_id)


    #-------------------------------------------------------
    def GetThemeValue(node, element):
        """(Static) Fetch the theme value for a given field"""

        (theme_cls, theme_id) = __class__._GetThemeInfo(node, element)

        if theme_id is not None:
            field_id = element.get("field_id")
            return GetThemeGallery(theme_cls)._GetThemeItemValue(theme_id, field_id)

        return None


    #-------------------------------------------------------
    def SetThemeValue(node, element):
        """(Static) Set the theme value for a given field"""

        (theme_cls, theme_id) = __class__._GetThemeInfo(node, element)

        if theme_id is not None:
            field_id = element.get("field_id")
            value = element.text
            GetThemeGallery(theme_cls)._SetThemeItemValue(theme_id, field_id, value)


    #-------------------------------------------------------
    def Add(self, value, name = None, at_front = False, replace_existing = True):
        """Add a new value to the document tree"""

        # identify correct document class
        cls = D_Document.ValueToDocClass(value)

        # add the XML element to the tree
        (write, element) = cls.Create(self._Element, replace_existing, at_front, name, value)

        # set the value into the new XML element
        document = cls(element, self._WNode)
        if write:
            document.Value = value
        return document



## D_Field #################################################

class D_Field(D_Base):
    """Persist a single field in the document tree"""

    #-------------------------------------------------------
    def _ObjToFieldType(value):
        """Map an object to its field type"""

        res = None

        if type(value) is str:
            res = "Str"
        elif type(value) is int:
            res = "Int"
        elif type(value) is bool:
            res = "Bool"

        return res


    #-------------------------------------------------------
    def _IsHandler(value):
        """Return True if this document class manages `value` items"""
        return __class__._ObjToFieldType(value) is not None


    #-------------------------------------------------------
    def Create(parent, replace_existing, at_front, name, value):
        field_type = __class__._ObjToFieldType(value)
        return D_Base._Create(parent, replace_existing, at_front, "field", name = name, type = field_type)


    #-------------------------------------------------------
    def __init__(self, element, wnode):
        super().__init__(element, wnode)


    #-------------------------------------------------------
    def _get_Value_(self):
        """Property getter; fetches field value from the document (or theme)"""

        # check theme first
        str_value = __class__.GetThemeValue(self._WNode(), self._Element)

        if str_value is None:
            str_value = self._Element.text

        if str_value is None:
            str_value = ""

        # interpret the value
        type = self._Element.get("type")
        if type.find("Array") >= 0:
            str_array = str_value.split(";")
            if type.find("Str") >= 0:
                return str_array
            elif type.find("Int") >= 0:
                return [int(elem) for elem in str_array]
            elif type.find("Bool") >= 0:
                return [bool(elem[0] == "T") for elem in str_array]
        else:
            if type.find("Str") >= 0:
                return str_value
            elif type.find("Int") >= 0:
                return int(str_value)
            elif type.find("Bool") >= 0:
                return bool(str_value[0] == "T")


    #-------------------------------------------------------
    def _set_Value_(self, value):
        """Property setter; writes the supplied value into the document"""

        # write the value
        type = self._Element.get("type")
        if type.find("Array") >= 0:
            self._Element.text = ";".join([str(elem) for elem in value])
        else:
            self._Element.text = str(value)

        # theme handling; user has overridden the theme
        if self._Element.get("override") is not None:
            self._Element.set("override", "1")


    #-------------------------------------------------------
    Value = property(_get_Value_, _set_Value_)



## D_Object ################################################

class D_Object(D_Base):
    """Persist an object in the document tree"""

    #-------------------------------------------------------
    def _IsHandler(value):
        """Return True if this document class manages `value` items"""
        return isinstance(value, D_Document.D_Value)


    #-------------------------------------------------------
    def Create(parent, replace_existing, at_front, name, value):
        return D_Base._Create(parent, replace_existing, at_front, "object", name = name)


    #-------------------------------------------------------
    def GetThemeOverrides(self, theme_cls):
        """
        Identify all child elements subject to a theme override. Returns
        a list of pairs of field_id (guid) and element value.
        """
        res = []

        for element in self._Element.findall(".//field[@override='1']"):
            if element.get("theme_cls") == theme_cls:
                res.append([element.get("field_id"), element.text])

        return res


    #-------------------------------------------------------
    def SaveOverridesToTheme(self, theme_cls):
        """Save all themed *field* child elements to the current theme"""
        for element in self._Element.findall(".//field[@override='1']"):
            if element.get("theme_cls") == theme_cls:
                element.set("override", "0")
                __class__.SetThemeValue(self._WNode(), element)


    #-------------------------------------------------------
    def ClearThemeOverrides(self, theme_cls):
        """
        Revert all themed *field* child elements. Returns True if
        any changes were made.
        """
        cleared = False

        for element in self._Element.findall(".//field[@override='1']"):
            if element.get("theme_cls") == theme_cls:
                element.set("override", "0")
                cleared = True

        return cleared


    #-------------------------------------------------------
    def __init__(self, element, wnode):
        super().__init__(element, wnode)


   #-------------------------------------------------------
    def __getattr__(self, name):
        """Fetch object's field by name"""
        element = self._Element.find("./*[@name='{}']".format(name))
        if element is None:
            raise RuntimeError("Unable to find document field '{}'".format(name))
        return D_Document(element, self._WNode())


    #-------------------------------------------------------
    def _get_Value_(self):
        """
        Property getter; fetches whole object from the document. The newly
        created object derives from D_Value, so won't neccessarily have the 
        same methods as an object written to the document via the property
        setter.
        """

        res = D_Document.D_Value()
        for field in self._Element.findall("*"):
            name = field.get("name")
            setattr(res, name, D_Document(field, self._WNode()).Value)

        return res


    #-------------------------------------------------------
    def _set_Value_(self, value):
        """Property setter; over-writes document data with the supplied object"""

        element = self._Reset()
        attr_names = dir(value)
        for attr_name in attr_names:
            attr = getattr(value, attr_name)
            if type(attr) != types.MethodType and attr_name[0] != '_':
                self.Add(attr, attr_name)


    #-------------------------------------------------------
    Value = property(_get_Value_, _set_Value_)



## D_Array #################################################

class D_Array(D_Base):

    #-------------------------------------------------------
    def _IsHandler(value):
        """Return True if this document class manages `value` items"""
        return type(value) is list


    #-------------------------------------------------------
    def Create(parent, replace_existing, at_front, name, value):
        return D_Base._Create(parent, replace_existing, at_front, "array", name = name)


    #-------------------------------------------------------
    def __init__(self, element, wnode):
        super().__init__(element, wnode)


    #-------------------------------------------------------
    def remove(self, idx = -1):
        """Remove an element from the array"""
        element = self._Element
        if idx < 0:
            idx = len(element) - 1
        element.remove(element[idx])


    #-------------------------------------------------------
    def __getitem__(self, idx):
        """Fetch array element by index"""
        element = self._Element[idx]
        return D_Document(element, self._WNode())

    def __len__(self):
        return len(self._Element)


    #-------------------------------------------------------
    def _get_Value_(self):
        """Property getter; fetches whole array from the document"""

        res = []

        for field in self._Element.findall("*"):
            res.append(D_Document(field, self._WNode()).Value)

        return res


    #-------------------------------------------------------
    def _set_Value_(self, value):
        """Property setter; over-writes document data with the supplied array"""

        element = self._Reset()
        for item in value:
            self.Add(item)


    #-------------------------------------------------------
    Value = property(_get_Value_, _set_Value_)



## MODULE ##################################################

D_Document.RegisterDocClass(D_Document.DocTypeField, D_Field)
D_Document.RegisterDocClass(D_Document.DocTypeObject, D_Object)
D_Document.RegisterDocClass(D_Document.DocTypeNode, D_Object)
D_Document.RegisterDocClass(D_Document.DocTypeArray, D_Array)


## GLOBAL ##################################################

def GetThemeId(node, theme_cls):
    return D_Base._LookupThemeId(node, theme_cls)