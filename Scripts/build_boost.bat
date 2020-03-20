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

call _Work\env.bat

echo.
echo ==== BOOST Release %BOOST%

cd %BOOST%
if not exist b2.exe (
  call bootstrap.bat
)

set OPT=%B2_ARGS% -j 4 --toolset=msvc-14.0 --stagedir=./stage/x64 address-model=64 --build-dir=bld threading=multi runtime-link=shared --with-python
.\b2 %OPT% variant=release link=shared debug-symbols=on

echo.
echo ==== BOOST Debug %BOOST%
.\b2 %OPT% variant=debug link=shared



