#
# Copyright (C) Niel Clausen 2018-2020. All rights reserved.
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

# System imports
from pkg_resources import iter_entry_points

# NLV imports
import Nlv.Logmeta as Schema
from Nlv.Theme import GetThemeStore



## G_ExtensionInfo #########################################

class G_ExtensionInfo:

    _ExtensionsValid = False
    _Extensions = []

    #-------------------------------------------------------
    def __init__(self, name):
        self._Name = name


    #-------------------------------------------------------
    @classmethod
    def LoadExtensions(cls):

        #
        # references:
        # http://setuptools.readthedocs.io/en/latest/pkg_resources.html
        # https://docs.pylonsproject.org/projects/pylons-webframework/en/latest/advanced_pylons/entry_points_and_plugins.html
        #

        if cls._ExtensionsValid:
            return

        # Interface between NLV plugins (extensions) and the application
        class Context:
            def __init__(self, name):
                self._Info = G_ExtensionInfo(name)

            def RegisterLogSchemata(self, install_dir):
                Schema.RegisterLogSchemata(install_dir)

            def RegisterThemeDirectory(self, install_dir):
                GetThemeStore().RegisterDirectory(install_dir)


        cls._ExtensionsValid = True
        for entry_point in iter_entry_points(group = "nlv.extensions", name = None):
            context = Context(entry_point.name)
            extension_func = entry_point.load()
            extension = extension_func(context)
            cls._Extensions.append(context._Info)


    #-------------------------------------------------------
    @classmethod
    def GetExtensionNames(cls):
        cls.LoadExtensions()
        return [ext.GetName() for ext in cls._Extensions]



## MODULE ##################################################

def LoadExtensions():
    G_ExtensionInfo.LoadExtensions()

def GetExtensionNames():
    return G_ExtensionInfo.GetExtensionNames()
