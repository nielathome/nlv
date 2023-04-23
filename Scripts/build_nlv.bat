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

rem Ensure required tools are present and up to date
pip install %PIP_ARGS% --upgrade build



echo.
echo ==== Sphinx

rem Build the documentation
cd %ROOT_DIR%\Sphinx
call make html %NLVCORE_BLDDIR%\NlvCore\Sphinx



echo.
echo ==== NLV


rem Setup staging area for build; now contains NLV *and* built documentation
xcopy /q /y /s /i %ROOT_DIR%\NlvCore %NLVCORE_BLDDIR%\NlvCore >NUL
cd %NLVCORE_BLDDIR%

rem Build the distributable wheel
rem python nlv-setup.py %PIP_ARGS% ^
rem   build --build-base=%PYNLV% --parallel 4 ^
rem   egg_info --egg-base %PYNLV% ^
rem   bdist_wheel --bdist-dir=%PYNLV%\bdist.win-amd64 --dist-dir=%INSTDIR%

rem Copy the program icon(s) to the install directory
xcopy /q /y Nlv\Ico\*.ico %INSTDIR% >NUL



echo.
echo ==== NlvMythTV

rem The new Python build system ignores most options (e.g. --build-base, --egg-base etc)
rem so copy everything to the build directory and process there
xcopy /q /y /s /i %ROOT_DIR%\NlvMythTV %MYTHTV_BLDDIR%\NlvMythTV >NUL
cd %MYTHTV_BLDDIR%
python -m build %PYBLD_ARGS% --no-isolation --wheel --outdir %INSTDIR%

rem Deactivate the Python virtual environment
call %PYENVBLD%\Scripts\Deactivate.bat
