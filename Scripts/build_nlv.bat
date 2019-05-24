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
set HOME=%CD%

rem Build NLV within the defined Python build virtual environment
call %PYENVBLD%\Scripts\Activate.bat



echo.
echo ==== Sphinx

rem Build the documentation
cd Sphinx
call make html
cd %HOME%



echo.
echo ==== NLV

set PYBLD=%HOME%\_Work\Bld\Python\
set PYNLV=%PYBLD%\Nlv
cd %HOME%\Application

rem Build the distributable wheel
python nlv-setup.py %PIP_ARGS% ^
  build --build-base=%PYNLV% --parallel 4 ^
  egg_info --egg-base %PYNLV% ^
  bdist_wheel --bdist-dir=%PYNLV%\bdist.win-amd64 --dist-dir=%INSTDIR%

rem Copy the program icon(s) to the install directory
xcopy /q /y nlv\*.ico %INSTDIR% >NUL



echo.
echo ==== MythTV

set PYMYTHTV=%PYBLD%\MythTV
cd %HOME%\Plugin

rem Build the distributable wheel
python nlv.mythtv-setup.py %PIP_ARGS% ^
  build --build-base=%PYMYTHTV% ^
  egg_info --egg-base %PYMYTHTV% ^
  bdist_wheel --bdist-dir=%PYMYTHTV%\bdist.win-amd64 --dist-dir=%INSTDIR%

rem Deactivate the Python virtual environment
call %PYENVBLD%\Scripts\Deactivate.bat
