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

set PYPI=PyPI
if "%1" == "--debug" (
    set PYPI=TesrPyPI
    set DBG_ARGS=--verbose --repository-url https://test.pypi.org/legacy/
)

call _Work\env.bat

echo.
echo ==== Upload to PyPi %DBG_TEXT%

call %PYENVBLD%\Scripts\Activate.bat

rem Ensure required tools are present and up to date
python -m pip install %PIP_ARGS% --upgrade twine

rem Upload distribution
python -m twine upload --username __token__ %DBG_ARGS% %UPLOADDIR%\*.whl