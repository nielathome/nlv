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


rem
rem Setup the debug Python virtual environment so that VisualStudio picks
rem up the debug versions of the supporting DLLs.
rem

call _Work\env.bat
set SITEDIR=%PYENVDBG%\Lib\site-packages



echo.
echo ==== Check/update Python Virtual Environment

call %PYENVDBG%\Scripts\Activate.bat
python -m pip install %PIP_ARGS% --upgrade pip 
python -m pip %PIP_ARGS% install --upgrade pip pywin32 six pillow comtypes



echo.
echo ==== Add Phoenix to debug environment

cd %PHOENIX%
python setup.py %PIP_ARGS% develop



echo.
echo ==== Add NLV to debug environment

set NLV_PTH=%SITEDIR%\nlv.pth
set NLV_EGG_LINK=%SITEDIR%\nlv.egg-link
set NLOG_EGG_LINK=%SITEDIR%\nlog.egg-link

set NLV_DIR=%ROOT_DIR%\Application
set NLOG_DIR=%BLDDIR%\NlogDll\Bin

rem sys.path extension
echo # NLV developer paths > %NLV_PTH%
echo %NLV_DIR% >> %NLV_PTH%
echo %NLOG_DIR% >> %NLV_PTH%

rem Nlv Egg link
echo %NLV_DIR% > %NLV_EGG_LINK%   
echo . >> %NLV_EGG_LINK%

rem Nlog Egg link
echo %NLOG_DIR% > %NLOG_EGG_LINK%   
echo . >> %NLOG_EGG_LINK%



echo.
echo ==== Add MythTV to debug environment

set MYTHTV_DIR=%ROOT_DIR%\Plugin
set MYTHTV_EGG_LINK=%SITEDIR%\NlvMythTV.egg-link

rem sys.path extension
echo %MYTHTV_DIR% >> %NLV_PTH%

rem Nlv Egg link
echo %MYTHTV_DIR% > %MYTHTV_EGG_LINK%   
echo . >> %MYTHTV_EGG_LINK%



echo.
echo ===============================================================================
echo NLV development environment installed to %VIRTUAL_ENV%
echo Double-click the solution file; ensure the _Work\PyEnv\Dbg Python virtual
echo environment is setup and activated:
echo   Solution Platforms = x64
echo   Solution Explorer ] Nlv ] Python Environments ] Add Existing Virtual Environment...
echo   Solution Explorer ] Nlv ] Python Environments ] Dbg (Python %PYVER%) ] Activate Environment      
echo.

:FINISH
