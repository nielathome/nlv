#
# Copyright (C) Niel Clausen 2018-2023. All rights reserved.
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


## LAUNCHER ################################################

def OnDirectorySearch(dir):
    schema_guid = "6E4169C7-97D2-4F98-9BB9-AB9CCA90AC70"
    builder_guid = "50F34148-43D8-452E-B2E3-CDF0FCE90DD4"
    return [(dir/p, schema_guid, builder_guid) for p in dir.rglob("myth*.log")]


def OnFileConvert(file):
    pass



## MODULE ##################################################

def MakeExtension(context):
    install_dir = Path(__file__).parent
    context.RegisterLogSchemata(install_dir)
    context.RegisterThemeDirectory(install_dir)
#    context.RegisterFileConverter(extension, converter)
    context.RegisterDirectorySearch(OnDirectorySearch)
