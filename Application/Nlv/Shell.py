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

# Python imports
from pathlib import Path
import os
import pythoncom
from win32com.shell import shellcon, shell
import win32api
import win32con
import winnt

# Application imports
from Nlv.Version import NLV_VERSION



## G_Shell #################################################

class G_Shell:

    #-------------------------------------------------------

    # overall document version; change this when non-backwards
    # compatible changes are made to the document structure or
    # application
    _PublicVersion = 3

    _VersionData = {
        # document-public-version : document-internal-version, icon-file
        1 : [4, "if_puzzle_yellow_10505.ico"],
        2 : [5, "if_puzzle_yellow_10505.ico"],
        3 : [6, "if_puzzle_red_10504.ico"]
    }


    #-------------------------------------------------------
    @staticmethod
    def GetPackageDir():
        return Path( __file__ ).parent


    @classmethod
    def GetDocumentVersion(cls):
        return cls._VersionData[cls._PublicVersion][0]


    @classmethod
    def GetIconPath(cls):
        filename = cls._VersionData[cls._PublicVersion][1]
        return cls.GetPackageDir() / filename


    @classmethod
    def GetScriptPath(cls):
        return cls.GetPackageDir().parent.parent.parent / "Scripts" / "nlvw.exe"


    #-------------------------------------------------------
    @classmethod
    def Extension(cls):
        if cls._PublicVersion == 1:
            return ".nlv"
        else:
            return ".nlv{}".format(cls._PublicVersion)


    #-------------------------------------------------------
    def __init__(self):
        self._Changed = False
        self._HKEY_CLASSES_ROOT = win32api.RegOpenKeyEx(
            win32con.HKEY_CURRENT_USER,
            r"Software\Classes",
            0,
            win32con.KEY_CREATE_SUB_KEY
        )


    def _GetKey(self, key, subkey):
        (key, status) = win32api.RegCreateKeyEx(
            key,
            subkey,
            win32con.KEY_CREATE_SUB_KEY | win32con.KEY_QUERY_VALUE | win32con.KEY_SET_VALUE 
        )

        if status == winnt.REG_CREATED_NEW_KEY:
            self._Changed = True

        return key


    def _GetStrValue(self, key):
        cur = ""
        type = win32con.REG_SZ

        try:
            (cur, type) = win32api.RegQueryValueEx(key, "")
        except:
            pass

        return (cur, type)


    def _SetStrValue(self, key, value):
        (cur, type) = self._GetStrValue(key)
        if type != win32con.REG_SZ or value != cur:
            self._Changed = True
            win32api.RegSetValue(key, None, win32con.REG_SZ, value)


    #-------------------------------------------------------
    def _MakeProgId(self):
        return "NLV.Session.{}".format(self.GetDocumentVersion())


    def _SetupProgId(self):
        prog_key = self._GetKey(self._HKEY_CLASSES_ROOT, self._MakeProgId())
        self._SetStrValue(prog_key, "Log View")

        icon_key = self._GetKey(prog_key, "DefaultIcon")
        self._SetStrValue(icon_key, str(self.GetIconPath()))

        script_path = self.GetScriptPath()
        if script_path.exists():
            open_key = self._GetKey(prog_key, r"shell\open\command")
            self._SetStrValue(open_key, '"{}" --session "%1"'.format(str(script_path)))


    #-------------------------------------------------------
    def _SetupFileType(self):
        type_key = self._GetKey(self._HKEY_CLASSES_ROOT, __class__.Extension())
        self._SetStrValue(type_key, self._MakeProgId())
        

    #-------------------------------------------------------
    def _SetupStartMenu(self):
        # https://docs.microsoft.com/en-gb/windows/desktop/shell/links
        # http://timgolden.me.uk/python/win32_how_do_i/create-a-shortcut.html

        shortcut = pythoncom.CoCreateInstance (
            shell.CLSID_ShellLink,
            None,
            pythoncom.CLSCTX_INPROC_SERVER,
            shell.IID_IShellLink
        )

        shortcut.SetPath(str(self.GetScriptPath()))
        shortcut.SetDescription("LogView")
        shortcut.SetIconLocation(str(self.GetIconPath()), 0)

        menu_dir = shell.SHGetFolderPath (0, shellcon.CSIDL_STARTMENU, 0, 0)
        persist_file = shortcut.QueryInterface(pythoncom.IID_IPersistFile)
        persist_file.Save(os.path.join(menu_dir, "Programs", "NLV.{}.{}.lnk".format(self._PublicVersion, NLV_VERSION)), 0)


    #-------------------------------------------------------
    def SetupIntegration(self):
        # see https://docs.microsoft.com/en-us/windows/desktop/shell/intro

        self._SetupProgId()
        self._SetupFileType()
        self._SetupStartMenu()

        if self._Changed:
            shell.SHChangeNotify(shellcon.SHCNE_ASSOCCHANGED, shellcon.SHCNF_IDLIST, None, None)
