#
# Copyright (C) Niel Clausen 2017-2020. All rights reserved.
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
from NlvCore.Version import NLV_VERSION



## G_AppData ###############################################

class G_AppData:

    #-------------------------------------------------------

    # overall document version; change this when non-backwards
    # compatible changes are made to the document structure or
    # application
    PublicVersion = 3

    VersionData = {
        # document-public-version : document-internal-version, icon-file
        1 : [4, "if_puzzle_yellow_10505.ico"],
        2 : [5, "if_puzzle_yellow_10505.ico"],
        3 : [6, "if_puzzle_red_10504.ico", "if_gear_red_10439.ico"]
    }


    #-------------------------------------------------------
    @staticmethod
    def GetPackageDir():
        return Path( __file__ ).parent


    @classmethod
    def GetDocumentVersion(cls):
        return cls.VersionData[cls.PublicVersion][0]


    @classmethod
    def GetIconPathFor(cls, idx):
        filename = cls.VersionData[cls.PublicVersion][idx + 1]
        return cls.GetPackageDir() / "Ico" / filename


    @classmethod
    def GetScriptPathFor(cls, name):
        return cls.GetPackageDir().parent.parent.parent / "Scripts" / name



## G_AppTraits #############################################

class G_AppTraits(G_AppData):

    #-------------------------------------------------------
    @classmethod
    def GetDescription(cls):
        return "Log View"


    @classmethod
    def GetOpenArg(cls):
        return "--session"


    @classmethod
    def GetLinkName(cls):
        return "NLV.{}.{}.lnk".format(cls.PublicVersion, NLV_VERSION)


    @classmethod
    def GetProgId(cls):
        return "NLV.Session.{}".format(cls.GetDocumentVersion())


    @classmethod
    def GetIconPath(cls):
        return cls.GetIconPathFor(0)


    @classmethod
    def GetScriptPath(cls):
        return cls.GetScriptPathFor("nlvw.exe")



## G_LaunchTraits ##########################################

class G_LaunchTraits(G_AppData):

    #-------------------------------------------------------
    @classmethod
    def GetDescription(cls):
        return "Log Launch"


    @classmethod
    def GetOpenArg(cls):
        return "--launch"


    @classmethod
    def GetLinkName(cls):
        return "NLV.Launch.lnk"


    @classmethod
    def GetProgId(cls):
        return "NLV.Launch"


    @classmethod
    def GetIconPath(cls):
        return cls.GetIconPathFor(1)


    @classmethod
    def GetScriptPath(cls):
        return cls.GetScriptPathFor("launchw.exe")



## G_Shell #################################################

class G_Shell:
    #-------------------------------------------------------
    def GetAppIconPath():
        return G_AppTraits.GetIconPath()

    def GetLaunchIconPath():
        return G_LaunchTraits.GetIconPath()

    def GetDocumentVersion():
        return G_AppData.GetDocumentVersion()


    #-------------------------------------------------------
    def Extension():
        version = G_AppData.PublicVersion
        if version == 1:
            return ".nlv"
        else:
            return ".nlv{}".format(version)


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


    def _GetStrValue(self, key, value_name = None):
        cur = None
        type = win32con.REG_SZ

        try:
            (cur, type) = win32api.RegQueryValueEx(key, value_name)
        except:
            pass

        return (cur, type)


    def _SetStrValue(self, key, value, value_name = None):
        (cur, type) = self._GetStrValue(key, value_name)
        if type != win32con.REG_SZ or value != cur:
            self._Changed = True
            win32api.RegSetValueEx(key, value_name, 0, win32con.REG_SZ, value)


    #-------------------------------------------------------
    def _SetupProgId(self, traits):
        prog_key = self._GetKey(self._HKEY_CLASSES_ROOT, traits.GetProgId())
        self._SetStrValue(prog_key, traits.GetDescription())

        icon_key = self._GetKey(prog_key, "DefaultIcon")
        self._SetStrValue(icon_key, str(traits.GetIconPath()))

        script_path = traits.GetScriptPath()
        open_arg = traits.GetOpenArg()
        if script_path.exists():
            open_key = self._GetKey(prog_key, r"shell\open\command")
            self._SetStrValue(open_key, '"{}" {} "%1"'.format(str(script_path), open_arg))


    #-------------------------------------------------------
    def _SetupFileOpen(self, traits):
        type_key = self._GetKey(self._HKEY_CLASSES_ROOT, __class__.Extension())
        self._SetStrValue(type_key, traits.GetProgId())
        

    #-------------------------------------------------------
    def _SetupFileOpenWith(self, extension, traits):
        # https://docs.microsoft.com/en-us/windows/win32/shell/how-to-include-an-application-on-the-open-with-dialog-box
        open_key = self._GetKey(self._HKEY_CLASSES_ROOT, extension + r"\OpenWithProgids")
        self._SetStrValue(open_key, "", traits.GetProgId())


    #-------------------------------------------------------
    def _SetupStartMenu(self, traits):
        # https://docs.microsoft.com/en-gb/windows/desktop/shell/links
        # http://timgolden.me.uk/python/win32_how_do_i/create-a-shortcut.html

        shortcut = pythoncom.CoCreateInstance (
            shell.CLSID_ShellLink,
            None,
            pythoncom.CLSCTX_INPROC_SERVER,
            shell.IID_IShellLink
        )

        shortcut.SetPath(str(traits.GetScriptPath()))
        shortcut.SetDescription(traits.GetDescription())
        shortcut.SetIconLocation(str(traits.GetIconPath()), 0)

        menu_dir = shell.SHGetFolderPath (0, shellcon.CSIDL_STARTMENU, 0, 0)
        persist_file = shortcut.QueryInterface(pythoncom.IID_IPersistFile)
        persist_file.Save(os.path.join(menu_dir, "Programs", traits.GetLinkName()), 0)


    #-------------------------------------------------------
    def GetInstalledAppPath(self):
        traits = G_AppTraits
        open_key = self._GetKey(self._HKEY_CLASSES_ROOT, traits.GetProgId() + r"\shell\open\command")
        (value, type) = self._GetStrValue(open_key)

        if type == win32con.REG_SZ and value is not None:
            split = value.split(" ")
            if len(split) > 0:
                return split[0].strip('"')

        return None


    #-------------------------------------------------------
    def SetupAppIntegration(self):
        # see https://docs.microsoft.com/en-us/windows/desktop/shell/intro

        traits = G_AppTraits
        self._SetupProgId(traits)
        self._SetupFileOpen(traits)
        self._SetupStartMenu(traits)

        if self._Changed:
            shell.SHChangeNotify(shellcon.SHCNE_ASSOCCHANGED, shellcon.SHCNF_IDLIST, None, None)


    #-------------------------------------------------------
    def SetupLaunchIntegration(self, extensions):
        traits = G_LaunchTraits
        self._SetupProgId(traits)
        self._SetupStartMenu(traits)

        for extension in extensions:
            self._SetupFileOpenWith("." + extension, traits)

        if self._Changed:
            shell.SHChangeNotify(shellcon.SHCNE_ASSOCCHANGED, shellcon.SHCNF_IDLIST, None, None)
