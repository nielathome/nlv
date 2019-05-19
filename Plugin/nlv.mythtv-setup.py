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

from setuptools import setup


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

if __name__ == '__main__':

    dir = "NlvMythTV"

    setup(

        #-------------------------------------------------------------------
        # Files

        name = dir,
        packages = [dir],

        package_data={
            "": [
                '*.xml'
             ]
        },

        install_requires = [
          'Nlv==386'
        ],

        entry_points={
            'nlv.extensions': [
                'MythTV = NlvMythTV.Main:MakeExtension',
            ]
        },
        

        #-------------------------------------------------------------------
        # Metadata

        version = "386",
        license = "GPL V3.0",
        platforms = "WIN64",
        classifiers = [c for c in CLASSIFIERS.split("\n") if c],
        keywords = "GUI,nlv",

        description = "MythTV extension for NLV",
        long_description = "Add support for MythTV logfiles to NLV",

        author = "Niel Clausen",
        author_email = "Niel Clausen <niel@home>",

        url = "http://tbd/",
        download_url = "http://tbd/"
    )
