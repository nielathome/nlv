@echo off
rem
rem Copyright (C) Niel Clausen 2019-2023. All rights reserved.
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

call "%VS2017ENV%"



echo.
echo ==== vsNLV

rem Build the VisualStudio Extension - although it does require NuGet to restore
rem the packages

if not exist %NUGET% (
  echo Unable to build the VisualStudio Extension as nuget.exe is not
  echo available in the build directory, download latest from
  echo https://www.nuget.org/downloads
  goto FINISH 
)

cd %ROOT_DIR%\NlvVsExtension

%NUGET% restore packages.config

msbuild vsNLV.csproj /maxcpucount %MSBUILD_ARGS% %MSBUILD_TARGET% /property:Configuration=Release

rem copy results to NlvCore sub-directory
set OUTDIR=%NLVCORE_BLDDIR%\NlvCore\vsNLV
if not exist %OUTDIR% (
  mkdir %OUTDIR%
)

xcopy /q /y %BLDDIR%\VsExtension\Bin\Release\*.vsix %OUTDIR% > NUL

:FINISH
