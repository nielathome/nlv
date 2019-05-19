@echo off
rem
rem Copyright (C) Niel Clausen 2019. All rights reserved.
rem 
rem This program is free software: you can redistribute it and/or modify
rem it under the terms of the GNU General Public License as published by
rem the Free Software Foundation, either version 3 of the License, or
rem (at your option) any later version.
rem 
rem This program is distributed in the hope that it will be useful,
rem but WITHOUT ANY WARRANTY; without even the implied warranty of
rem MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
rem GNU General Public License for more details.
rem 
rem You should have received a copy of the GNU General Public License
rem along with this program. If not, see <https://www.gnu.org/licenses/>.
rem

call _Results\env.bat
call "%VS2015ENV%" x64

echo.
echo ==== Intel TBB Release %TBB%

cd %TBB%\build\vs2013

msbuild tbb.vcxproj /nologo /maxcpucount %MSBUILD_ARGS% %MSBUILD_TARGET% /property:Configuration=Release /property:Platform=x64

echo.
echo ==== Intel TBB Debug %TBB%
msbuild tbb.vcxproj /nologo /maxcpucount %MSBUILD_ARGS% %MSBUILD_TARGET% /property:Configuration=Debug /property:Platform=x64

