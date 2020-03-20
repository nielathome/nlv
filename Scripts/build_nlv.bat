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

rem
rem For the time being ... force Vs2015, as different Python environments
rem choose different compilers. Should be able to drop this on switching
rem to all Vs2015 build chain
rem
SET DISTUTILS_USE_SDK=1
SET MSSdk=1
call "%VS2015ENV%" x64


rem Build NLV within the defined Python build virtual environment
call %PYENVBLD%\Scripts\Activate.bat



echo.
echo ==== Sphinx

rem Build the documentation
cd %ROOT_DIR%\Sphinx
call make html



echo.
echo ==== NLV

set PYBLD=%BLDDIR%\Python\
set PYNLV=%PYBLD%\Nlv

rem Setup staging area for build; contains NLV *and* built documentation
xcopy /q /y %ROOT_DIR%\Application\Nlv\*.* %STAGEDIR%\Nlv >NUL
cd %STAGEDIR%

rem Build the distributable wheel
python nlv-setup.py %PIP_ARGS% ^
  build --build-base=%PYNLV% --parallel 4 ^
  egg_info --egg-base %PYNLV% ^
  bdist_wheel --bdist-dir=%PYNLV%\bdist.win-amd64 --dist-dir=%INSTDIR%

rem Copy the program icon(s) to the install directory
xcopy /q /y Nlv\*.ico %INSTDIR% >NUL



echo.
echo ==== MythTV

set PYMYTHTV=%PYBLD%\MythTV
cd %ROOT_DIR%\Plugin

rem Build the distributable wheel
python nlv.mythtv-setup.py %PIP_ARGS% ^
  build --build-base=%PYMYTHTV% ^
  egg_info --egg-base %PYMYTHTV% ^
  bdist_wheel --bdist-dir=%PYMYTHTV%\bdist.win-amd64 --dist-dir=%INSTDIR%

rem Deactivate the Python virtual environment
call %PYENVBLD%\Scripts\Deactivate.bat
