@echo off
rem
rem Copyright (C) Niel Clausen 2018-2020. All rights reserved.
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

set TARGET=Nlv
if "%1"=="--withdemo" (
  set TARGET=NlvMythTV
  shift
)

if not "%VIRTUAL_ENV%"=="" goto :INSTALL

call .\iver.bat
set ENVDIR=%1
if "%1"=="" (
  set ENVDIR=C:\Nlv\%VER%
)

echo ===============================================================================
echo Installing NLV to %ENVDIR%

if not exist %ENVDIR% (
  echo ===============================================================================
  echo Creating Python virtual environment
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
pip install --upgrade --find-links=. %TARGET%
 
for %%f in (plugin-*.bat) do (
  call %%~nf
)

rem Temporary (~Q1'21)- until MS fix this: https://tinyurl.com/y3dm3h86
pip install numpy==1.19.3
 
rem Shell integration
nlvc -i
launchc -i

 
echo.
echo ===============================================================================
echo NLV installed to %VIRTUAL_ENV%\Scripts and to the Start Menu

if "%ENVDIR%"=="" goto :FINISH
call %ENVDIR%\Scripts\Deactivate.bat

:FINISH
set TARGET=
set ENVDIR=