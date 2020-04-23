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

call "%VS2015ENV%" x64



echo.
echo ==== SQLite Import Library

rem
rem Taken from https://stackoverflow.com/questions/9946322/how-to-generate-an-import-library-lib-file-from-a-dll
rem

dumpbin /exports "%PYTHON%\..\DLLs\sqlite3.dll" > %BLDDIR%\exports.txt
echo LIBRARY SQLITE3 > %BLDDIR%\sqlite3.def
echo EXPORTS >> %BLDDIR%\sqlite3.def
for /f "skip=19 tokens=4" %%A in (%BLDDIR%\exports.txt) do echo %%A >> %BLDDIR%\sqlite3.def

lib /nologo /def:%BLDDIR%\sqlite3.def /out:%SQLITE_LIB_DIR%\sqlite3.lib /machine:x64
