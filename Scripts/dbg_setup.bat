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


rem
rem Setup the debug Python virtual environment so that VisualStudio picks
rem up the debug versions of teh supporting DLLs.
rem

call _Work\env.bat


echo.
echo ==== Check/update Python Virtual Environment

call %PYENVDBG%\Scripts\Activate.bat
python -m pip install %PIP_ARGS% --upgrade pip 
python -m pip %PIP_ARGS% install --upgrade pip pywin32 matplotlib


rem
rem setup nlog.dll; short-circuit if NLOG already setup
rem
set HOME=%CD%
set SITEDIR=%VIRTUAL_ENV%\Lib\site-packages
set NLOG_EGG=%SITEDIR%\nlog.egg-link
set NLOG_PTH=%SITEDIR%\nlog.pth
set NLOG_DIR=%HOME%\_Work\Bld\NlogDll\Bin\Debug

if exist %NLOG_PTH% (
  goto FINISH
)
 
rem sys.path extension
echo # NLV developer paths > %NLOG_PTH%
echo %NLOG_DIR% >> %NLOG_PTH%

rem Nlog Egg
echo %NLOG_DIR% > %NLOG_EGG%   
echo . >> %NLOG_EGG%


echo.
echo ==== Add Phoenix to debug environment

cd %PHOENIX%
python setup.py develop


echo.
echo ==== Add NLV to debug environment

cd %HOME%\Application
python nlv-setup.py develop
rmdir /s /q build

echo.
echo ==== Add MythTV to debug environment

cd %HOME%\Plugin
python nlv.mythtv-setup.py develop


echo.
echo ===============================================================================
echo NLV development environment installed to %VIRTUAL_ENV%
echo Double-click the solution file; ensure the _Work\PyEnv\Dbg Python virtual
echo environment is setup and activated:
echo   Solution Platforms = x64
echo   Solution Explorer ] Nlv ] Python Environments ] Add Existing Virtual Environment...
echo   Solution Explorer ] Nlv ] Python Environments ] Dbg (Python 36) ] Activate Environment      
echo.

cd %HOME%
call %PYENVDBG%\Scripts\Deactivate.bat

rem
rem Post install fix-up: the installer leaves a packaged version of the Nlog DLL in
rem the Application directory. VisualStudio picks this up instead of the one it
rem compiles, causing confusion. So delete the unwanted DLL
rem
del /q Application\*.pyd
 
:FINISH


