@echo off
rem
rem Copyright (C) Niel Clausen 2023. All rights reserved.
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

set PLUGIN_DIR=%1
set PLUGIN_NAME=%2
set PLUGIN_BLDDIR=%3

echo.
echo ==== Build distribution

call %PYENVBLD%\Scripts\activate

xcopy /q /y /s /i %PLUGIN_DIR%\%PLUGIN_NAME% %PLUGIN_BLDDIR%\%PLUGIN_NAME% >NUL
cd %PLUGIN_BLDDIR%

python -m build %PYBLD_ARGS% --no-isolation --wheel --outdir %LOCAL_INSTDIR%
xcopy /q /y %LOCAL_INSTDIR%\%PLUGIN_NAME%*.whl %REMOTE_INSTDIR%

call deactivate


echo.
echo ==== Setup Debugging

set SITEDIR=%PYENVDBG%\Lib\site-packages
set EGG_LINK=%SITEDIR%\%PLUGIN_NAME%.egg-link

rem sys.path extension
set NLV_PTH=%SITEDIR%\nlv.pth
echo %PLUGIN_DIR% >> %NLV_PTH%

rem Egg link
echo %PLUGIN_DIR% > %EGG_LINK%
echo . >> %EGG_LINK%
