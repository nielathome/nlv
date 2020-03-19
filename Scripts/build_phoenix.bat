@echo off
rem
rem Copyright (C) Niel Clausen 2019-2020. All rights reserved.
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
echo ==== wxPython - setup build environment

rem Make sure CygWin bin directory is available
set "PATH=%PATH%;%CYGWIN_BASE%\Bin"

rem Build wxPython within the defined Python build virtual environment
call %PYENVBLD%\Scripts\Activate.bat

rem Ensure required tools are present and up to date
python -m pip install %PIP_ARGS% --upgrade pip 
pip install %PIP_ARGS% --upgrade pathlib2 setuptools wheel requests pytest six sphinx

cd %PHOENIX%

rem building the Python extensions is slow, so only do this when needed
set HAVE_EXTENSION=no
for %%f in (wx\*.pyd) do set HAVE_EXTENSION=yes
if "%HAVE_EXTENSION%"=="no" (
  echo.
  echo ==== wxPython - build
  python build.py -j 4 --nodoc dox etg sip
)

echo.
echo ==== wxWidgets - build
python build.py -j 4 --relwithdebug --release build


echo.
echo ==== wxPython - package
rem Can't see how to stop verbose printout; so always capture to log file
python build.py bdist_wheel > %ROOT_DIR%\_Work\Logs\phoenix.package.log

rem Copy installer to install directory
xcopy /q /y dist\*.* %INSTDIR% >NUL
