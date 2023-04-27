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

#
# Resources
#  Intro:      https://docs.python.org/3/distributing/
#  SetupTools: https://setuptools.readthedocs.io/en/latest/setuptools.html
#  DistUtils:  https://docs.python.org/3/distutils/index.html
#  pip:        https://pip.pypa.io/en/stable/
#  wheel:      https://wheel.readthedocs.io/en/stable/#
#

import sys, os

from glob import glob
from pathlib import Path
from setuptools import setup, find_packages, Extension


#---------------------------------------------------------------------------

LONG_DESCRIPTION = """\
Log file viewing and analysis
"""

CLASSIFIERS = """\
Development Status :: 4 - Beta
Environment :: Win32 (MS Windows)
Intended Audience :: Developers
License :: OSI Approved
Operating System :: Microsoft :: Windows :: Windows 10
Programming Language :: Python :: __PYVER__
Topic :: Software Development :: User Interfaces
"""


#---------------------------------------------------------------------------

def GetDir(var):
  try:
    dir = os.environ[var]
    if Path(dir).is_dir():
      return dir

    print("Unable to locate dependency: {0}".format(dir))

  except KeyError:
    print("Unable to locate environment variable: {0}".format(var))

  exit()


#---------------------------------------------------------------------------

if __name__ == '__main__':

    #-----------------------------------------------------------------------
    # Ensure all build dependencies are present

    root_dir = GetDir("ROOT_DIR")
    nlv_source = glob(root_dir + "/NlvLog/Dll/Src/*cpp")
    nlv_source.extend(glob(root_dir + "/NlvLog/Lib/Src/*cpp"))

    phoenix_dir = GetDir("PHOENIX")
    boost_dir = GetDir("BOOST")
    json_dir = GetDir("JSON")
    tbb_dir = GetDir("TBB")
    sql_dir = GetDir("SQLITE")
    sql_lib_dir = GetDir("SQLITE_LIB_DIR")

    wx_dir = phoenix_dir + "/ext/wxWidgets"
    boost_lib_dir = boost_dir + "/stage/x64/lib"
    boost_dll = glob(boost_lib_dir + "/*dll")
    tbb_dll = glob(tbb_dir + "/build/vs2013/x64/Release/*dll")

    #-----------------------------------------------------------------------
    # Define the extension

    nlvlog_extension = Extension(
        name = "NlvLog",

        sources = nlv_source,

        include_dirs = [
            root_dir + "/NlvLog/Dll/Hdr",
            root_dir + "/NlvLog/Lib/Hdr",
            wx_dir + "/src/stc",
            boost_dir,
            json_dir + "/single_include",
            tbb_dir + "/include",
            sql_dir
        ],

        define_macros = [
            ("_USRDLL", "1"),
            ("UNICODE", None),
            ("_UNICODE", None),
            ("_WINDOWS", None),
            ("VS2015U3", None)
        ],

        library_dirs = [
            boost_lib_dir,
            tbb_dir + "/build/vs2013/x64/Release",
            sql_lib_dir
        ],

        libraries = [
            "sqlite3"
        ]
    )

    setup(

        #-------------------------------------------------------------------
        # Files

        name = "NlvCore",
        packages = find_packages(),

        package_data={
            "NlvCore": [
                "*.xml",
                "Sphinx/doctrees/*",
                "Sphinx/html/[!_]*",
                "Sphinx/html/_sources/*",
                "Sphinx/html/_static/*",
                "Sphinx/html/_images/*",
                "Ico/*.ico",
                "Web/*",
                "Web/Charts/*",
                "Web/Charts/Bar/*",
                "Web/Charts/Network/*",
                "Web/Charts/Pie/*",
                "Web/Charts/TangledTree/*",
                "Web/Charts/TreeMap/*",
                "vsNLV/*"
             ]
        },

        data_files=[
            ("../..", boost_dll),
            ("../..", tbb_dll)
        ],

        zip_safe = False,
        install_requires = [
          'NlvWxPython==__WXPYTHONVER__',
          'comtypes',
          'pywin32==300' # there's something broken with newer pywin32 and older Python; pin to 300 for the time being
        ],

        entry_points={
            'console_scripts': [
                'nlvc=NlvCore.Main:main',
                'launchc=NlvCore.Launch:main'
            ],
            'gui_scripts': [
                'nlvw=NlvCore.Main:main',
                'launchw=NlvCore.Launch:main'
            ]

        },

        ext_modules = [ nlvlog_extension ],


        #-------------------------------------------------------------------
        # Metadata

        version = "__VER__",
        license = "GPL V3.0",
        platforms = "WIN64",
        classifiers = [c for c in CLASSIFIERS.split("\n") if c],
        keywords = "GUI,NLV",

        description = "Log file viewing and analysis",
        long_description = LONG_DESCRIPTION,

        author = "Niel Clausen",

        url = "https://github.com/nielathome/nlv"
    )
