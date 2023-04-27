@echo off
rem
rem Copyright (C) Niel Clausen 2018-2023. All rights reserved.
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

set VER=__VER__
set PKGLOC=__PKGLOC__

if "%1"=="--withdemo" (
  set WITHDEMO=NlvMythTV
  shift
)

if "%1"=="--testpi" (
  set PKGLOC=-i https://test.pypi.org/simple/
  shift
)


if not "%VIRTUAL_ENV%"=="" goto :INSTALL

set PYENV=%1
if "%1"=="" (
  set PYENV=C:\Nlv\%VER%
)


echo ===============================================================================
echo Installing NLV to %PYENV%

if not exist %PYENV% (
  echo ===============================================================================
  echo Creating Python virtual environment
  python -m venv %PYENV%
)

call %PYENV%\Scripts\Activate.bat


rem
rem Install
rem
:INSTALL


echo.
echo ===============================================================================
echo ==== NLV
 
python -m pip install --upgrade pip

pip install --upgrade %PKGLOC% NlvCore==%VER%


echo.
echo ===============================================================================

if not "%WITHDEMO%" == "" (
	echo ==== %WITHDEMO%
    pip install --upgrade --find-links=. %WITHDEMO%
)

for %%P in (__PLUGINS__) do (
	echo ==== %%P
    pip install --upgrade --find-links=. %%P
)


rem Shell integration
xcopy /y /q %PYENV%\lib\site-packages\NlvCore\Ico\*.ico .
nlvc -i
launchc -i

 
echo.
echo ===============================================================================
echo NLV installed to %VIRTUAL_ENV%\Scripts and to the Start Menu
echo The VisualStudio extension (2015, 2017 and 2019) can be found at
echo   %PYENV%\lib\site-packages\NlvCore\vsNLV

if "%PYENV%"=="" goto :FINISH
call %PYENV%\Scripts\Deactivate.bat

:FINISH
set WITHDEMO=
set ISLOCAL=
set PYENV=