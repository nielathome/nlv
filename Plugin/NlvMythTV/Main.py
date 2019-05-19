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

# Python imports
from pathlib import Path

# NLV imports
from Nlv.Extension import G_Extension
import Nlv.Logmeta as Schema
from Nlv.Theme import GetThemeStore



## E_MythTV ################################################

class E_MythTV(G_Extension):

    #-------------------------------------------------------
    def __init__(self, name):
        super().__init__(name)

        install_dir = Path(__file__).parent
        Schema.RegisterLogSchemata(install_dir)
        GetThemeStore().RegisterDirectory(install_dir)



## MODULE ##################################################

def MakeExtension(name):
    return E_MythTV(name)
