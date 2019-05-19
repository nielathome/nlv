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

CLASSIFIERS = """\
Development Status :: 3 - Alpha
Environment :: Win32 (MS Windows)
Intended Audience :: Developers
License :: OSI Approved
Operating System :: Microsoft :: Windows :: Windows 10
Programming Language :: Python :: 3.5
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

    nlv_source = glob("../Log/Dll/Src/*cpp")
    nlv_source.extend(glob("../Log/Lib/Src/*cpp"))
    
    phoenix_dir = GetDir("PHOENIX")
    boost_dir = GetDir("BOOST")
    json_dir = GetDir("JSON")
    tbb_dir = GetDir("TBB")

    wx_dir = phoenix_dir + "/ext/wxWidgets"
    boost_lib_dir = boost_dir + "/stage/x64/lib"
    boost_dll = glob(boost_lib_dir + "/*dll")
    tbb_dll = glob(tbb_dir + "/build/vs2013/x64/Release/*dll")

	#-----------------------------------------------------------------------
	# Define the extension

    nlog_extension = Extension(
        name = "Nlog",

        sources = nlv_source,
    
        include_dirs = [
            "../Log/Dll/Hdr",
            "../Log/Lib/Hdr",
            wx_dir + "/src/stc",
            boost_dir,
            json_dir + "/single_include",
            tbb_dir + "/include"
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
            tbb_dir + "/build/vs2013/x64/Release"
        ]
    )

    setup(

        #-------------------------------------------------------------------
        # Files

        name = "Nlv",
        packages = find_packages(),

        package_data={
            "Nlv": [
                '*.xml',
                '*.ico',
                 "Sphinx/doctrees/*",
                 "Sphinx/html/[!_]*",
                 "Sphinx/html/_sources/*",
                 "Sphinx/html/_static/*",
                 "Sphinx/html/_images/*"
             ]
        },

        data_files=[
            ("../..", boost_dll),
            ("../..", tbb_dll)
        ],

        zip_safe = False,
        install_requires = [
          'Nlv-wxPython==4.0.4',
          'pywin32',
          'matplotlib'
        ],

        entry_points={
            'gui_scripts': [
                'nlv=Nlv.Main:main',
            ]
        },
        
        ext_modules = [ nlog_extension ],


        #-------------------------------------------------------------------
        # Metadata

        version = "386",
        license = "GPL V3.0",
        platforms = "WIN64",
        classifiers = [c for c in CLASSIFIERS.split("\n") if c],
        keywords = "GUI,nlv",

        description = "Log file viewing and analysis",
        long_description = "TBD",

        author = "Niel Clausen",
        author_email = "Niel Clausen <niel@home>",

        url = "http://tbd/",
        download_url = "http://tbd/"
    )
