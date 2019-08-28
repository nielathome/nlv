@echo off
rem
rem Copyright (C) Niel Clausen 2018-2019. All rights reserved.
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
 
 
rem
rem A Python virtual environment is required
rem

if not "%VIRTUAL_ENV%"=="" goto :INSTALL

call .\iver.bat
set ENVDIR=%1
if "%1"=="" (
  set ENVDIR=PyNlv.%VER%
)

echo ===============================================================================
echo Using %ENVDIR% as the Python virtual environment for NLV

if not exist %ENVDIR% (
  echo ===============================================================================
  echo Unable to locate Python virtual environment directory %ENVDIR% ... creating
  python -m venv %ENVDIR%
)

call %ENVDIR%\Scripts\Activate.bat


rem
rem Install
rem
:INSTALL

echo.
echo ===============================================================================
echo ==== NLV
 
python -m pip install --upgrade pip
pip install --upgrade --find-links=. NlvMythTV
 
for %%f in (plugin-*.bat) do (
  call %%~nf
)
 
rem Shell integration
nlv -i
 
 
echo.
echo ===============================================================================
echo NLV installed to %VIRTUAL_ENV%\Scripts and to the Start Menu

if "%ENVDIR%"=="" goto :FINISH
call %ENVDIR%\Scripts\Deactivate.bat

:FINISH
set ENVDIR=