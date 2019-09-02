#!/bin/bash
#
# Copyright (C) Niel Clausen 2018-2019. All rights reserved.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#


###############################################################################
# Command line
###############################################################################

help()
{
  echo "build options"
  echo "--clean - clean workspace of build results"
  echo "--help | -h - display help"
  echo "--verbose | -v - increase detail in output"
}

cfg_clean=""
cfg_verbose=""
cfg_skip_phoenix=""
for arg in $*; do

  case "$arg" in

    "--clean")
      cfg_clean=1
      ;;
        
    "--help"|"-h"|"/?")
      help
      exit 0
      ;;

    "--skip-phoenix")
      cfg_skip_phoenix=1
      ;;
      
    "--verbose"|"-v")
      cfg_verbose=1
      ;;
                  
    *)
      echo "Unrecognised argument '$arg'"           
      help
      exit 1
      ;;
      
  esac
  
done

b2_args="-d0"
msbuild_args="/clp:verbosity=quiet"
msbuild_target="/target:Build"
pip_args="--quiet"
wget_args="--no-verbose"

if [ -n "$cfg_verbose" ]; then
  b2_args=""
  msbuild_args=""
  pip_args=""
  wget_args=""
fi

if [ -n "$cfg_clean" ]; then
  b2_args="--clean"
  msbuild_target="/target:Clean"
fi



###############################################################################
# Setup
###############################################################################

# add path variable to Windows environment
function addenvvar()
{
  name=$1
  winpath=`cygpath -a -w "$2"`
  echo "SET $name=$winpath" >> $envbat
}

# add path variable to VisualStudio environment
function addenvprops()
{
  name=$1
  winpath=`cygpath -a -w "$2"`
  echo "    <$name>$winpath</$name>" >> $envprops
}

# add path variable to Windows and VisualStudio environments
function addenv()
{
  name=$1
  winpath=`cygpath -a -w "$2"`
  echo "SET $name=$winpath" >> $envbat
  echo "    <$name>$winpath</$name>" >> $envprops
}

function msg_header()
{
  echo
  echo "==============================================================================="
  echo "==== [`date +%H:%M:%S`] $1"
}

function msg_line()
{
  echo "==== [`date +%H:%M:%S`] $1"
}

msg_header "Initialising NLV Build Directory"

# figure out a PEP440 compliant version number
counter=ver.txt
ver=`cat $counter`
echo -n $(($ver + 1)) > $counter

# make the application version available to the Python code
sed -e "s/__DEV__/$ver/" < Application/Template/tpl-Version.py > Application/Nlv/Version.py

# directory structure
blddir=`pwd`
wrkdir="$blddir/_Work"
pkgdir="$blddir/Deps/Packages"
instdir="$wrkdir/Installers/$ver"
logdir="$wrkdir/Logs"
stagedir="$wrkdir/Stage"
testdir="$wrkdir/Test"
mkdir -p "$logdir" "$pkgdir" "$instdir" "$testdir" "$stagedir"

# initialise installer directory
cp Scripts/install.bat "$instdir"
echo "set VER=${ver}" > "$instdir/iver.bat" 

# initialise debug time DLL path
pathvar=$wrkdir/path.txt
echo -n `cygpath -w -p "$PATH"` > $pathvar

# initialise Windows environment
envbat=$wrkdir/env.bat
echo SET NLV=$ver > $envbat
echo "SET B2_ARGS=$b2_args" >> $envbat
echo "SET MSBUILD_ARGS=$msbuild_args" >> $envbat
echo "SET MSBUILD_TARGET=$msbuild_target" >> $envbat
echo "SET PIP_ARGS=$pip_args" >> $envbat
addenvvar ROOT_DIR "."
addenvvar CYGWIN_BASE "/"
addenvvar INSTDIR "$instdir"

# initialise VisualStudio environment
envprops=$wrkdir/env.props
echo "<?xml version=\"1.0\" encoding=\"utf-8\"?>" > $envprops
echo "<Project xmlns=\"http://schemas.microsoft.com/developer/msbuild/2003\">" >> $envprops
echo "  <PropertyGroup>" >> $envprops

addenv GTEST "Deps/Modules/GoogleTest"
addenv JSON "Deps/Modules/Json"
addenv PHOENIX "Deps/Modules/Phoenix"
addenv WXWIDGETS "Deps/Modules/Phoenix/ext/wxWidgets"



###############################################################################
# Utility Functions
###############################################################################

function checkf()
{
  if [ ! -f "$1" ]; then
    echo
    echo "+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
    echo "$2"
    echo "Ref: $1"
    echo "+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
    exit 3
  fi
}

function getfile()
{
  url=$1
  dest=$2
  file=`basename $dest`  

  if [ ! -f "$dest" ]; then
  
    msg_line "Download $file" 
  
    which wget > /dev/null
    if [ "$?" != 0 ]; then
      echo "ERROR: wget not found; unable to download dependency"
      exit 1 
    fi
  
    wget $wget_args $url 2>&1 | tee -a $logdir/wget.log
    if [ "$?" != 0 ]; then
      echo "ERROR: unable to download dependency"
      exit 2 
    fi
    
    mv $file $dest
  
  fi
}

function runbat()
{
  path=$1
  `cygpath -u $COMSPEC` /C `cygpath -w $path`

  cd $blddir
}



###############################################################################
# NuGet binary
###############################################################################

nuget_file=nuget.exe
nuget_url="https://dist.nuget.org/win-x86-commandline/latest/$nuget_file"
nuget=$wrkdir/$nuget_file

getfile $nuget_url $nuget   
chmod +x $nuget           

echo "SET NUGET=`cygpath -w $nuget`" >> $envbat



###############################################################################
# Environment checks
###############################################################################

python=`which -a python | fgrep 36`
checkf "$python" "Unable to locate Python 36"
python_dir=`dirname $python`

addenvvar PYTHON "$python"
addenvprops PYTHON "$python_dir"

cyg_vs2015env='C:/Program Files (x86)/Microsoft Visual Studio 14.0/VC/vcvarsall.bat'
checkf "$cyg_vs2015env" "Unable to locate VisualStudio 2015"
addenvvar VS2015ENV "$cyg_vs2015env"

cyg_vs2017env='C:/Program Files (x86)/Microsoft Visual Studio/2017/Community/Common7/Tools/VsDevCmd.bat'
checkf "$cyg_vs2017env" "Unable to locate VisualStudio 2017"
addenvvar VS2017ENV "$cyg_vs2017env"



###############################################################################
# Python Virtual Environments
###############################################################################

pyenvbld="$wrkdir/PyEnv/Bld"
addenvvar PYENVBLD "$pyenvbld"

if [ ! -d "$pyenvbld" ]; then

  msg_line "Creating Python virtual environment directory for build"
  $python -m venv `cygpath -w $pyenvbld`
fi

pyenvdbg="$wrkdir/PyEnv/Dbg"
addenvvar PYENVDBG "$pyenvdbg"

if [ ! -d "$pyenvdbg" ]; then
  msg_line "Creating Python virtual environment directory for debugging"
  $python -m venv `cygpath -w $pyenvdbg`
fi



###############################################################################
# BOOST
###############################################################################

boost_ver=63
boost_name="boost_1_${boost_ver}_0"
boost_file="${boost_name}.tar.bz2"
boost_url="https://sourceforge.net/projects/boost/files/boost/1.${boost_ver}.0/${boost_file}"
boost_path="$pkgdir/${boost_file}"
boost_dir="$pkgdir/${boost_name}"
boost_build="${logdir}/${boost_name}.build.log"
boost_clean="${logdir}/${boost_name}.clean.log"

if [ ! -d "$boost_dir" ]; then

  getfile $boost_url $boost_path   

  msg_line "Unpacking archive: $boost_file ..."
  tar xfj $boost_path -C $pkgdir

fi

addenv BOOST "${boost_dir}"
echo -n ";`cygpath -w ${boost_dir}/stage/x64/lib`" >> $pathvar 

if [ -n "$cfg_clean" ]; then
  msg_header "Cleaning BOOST ${boost_name}"
  rm -f "${boost_build}" 
  runbat Scripts/build_boost.bat 2>&1 | tee "${boost_clean}"

elif [ ! -f "$boost_build" ]; then
  msg_header "Building BOOST ${boost_name}"
  time runbat Scripts/build_boost.bat 2>&1 | tee "${boost_build}"
fi



###############################################################################
# Thread Building Blocks
###############################################################################

tbb_name="2018_U2"
tbb_file="${tbb_name}.tar.gz"
tbb_url="https://github.com/intel/tbb/archive/${tbb_file}"
tbb_path="$pkgdir/${tbb_file}"
tbb_dir="$pkgdir/tbb-${tbb_name}"
tbb_build="${logdir}/${tbb_name}.build.log"
tbb_clean="${logdir}/${tbb_name}.clean.log"

if [ ! -d "$tbb_dir" ]; then

  getfile "$tbb_url" "$tbb_path"   

  msg_line "Unpacking archive: $tbb_file ..."
  tar xfz $tbb_path -C $pkgdir
 
  # switch the toolchain in the Vs2013 (120) projects to Vs2015 (140)
  for f in $tbb_dir/build/Vs2013/*vcxproj
  do
    sed \
      -e 's/ToolsVersion="12.0"/ToolsVersion="14.0"/' \
      -e 's/<PlatformToolset>v120/<PlatformToolset>v140/' \
      < $f >t
    
    mv t $f 
  done
 
fi

addenv TBB "${tbb_dir}"
echo -n ";`cygpath -w ${tbb_dir}/build/vs2013/x64/Debug`" >> $pathvar 
echo -n ";`cygpath -w ${tbb_dir}/build/vs2013/x64/Release`" >> $pathvar 

if [ -n "$cfg_clean" ]; then
  msg_header "Cleaning TBB ${tbb_name}"
  rm -f "${tbb_build}" 
  runbat Scripts/build_tbb.bat 2>&1 | tee "${tbb_clean}"

elif [ ! -f "$tbb_build" ]; then
  msg_header "Building TBB ${tbb_name}"
  time runbat Scripts/build_tbb.bat 2>&1 | tee "${tbb_build}"
fi



###############################################################################
# SQLite Header
###############################################################################

sql_name="amalgamation-3140200"
sql_file="sqlite-${sql_name}.zip"
sql_url="https://www.sqlite.org/2016/${sql_file}"
sql_path="$pkgdir/${sql_file}"
sql_dir="$pkgdir/sqlite-${sql_name}"

addenv SQLITE "${sql_dir}"

if [ ! -d "$sql_dir" ]; then

  getfile "$sql_url" "$sql_path"   

  msg_line "Unpacking archive: $sql_file ..."
  unzip -o -d "$pkgdir" "$sql_path"
fi



###############################################################################
# Phoenix
###############################################################################

if [ -z "$cfg_skip_phoenix" ]; then

  if [ -n "$cfg_clean" ]; then
    msg_header "Cleaning Phoenix"
    runbat Scripts/clean_phoenix.bat 2>&1 | tee "${logdir}/phoenix.clean.log"
  
  else
    msg_header "Building Phoenix"
    time runbat Scripts/build_phoenix.bat 2>&1 | tee "${logdir}/phoenix.build.log"
  fi

fi



###############################################################################
# NLV
###############################################################################

# create the Python setup files
sed -e "s/__VER__/$ver/" < Application/Template/tpl-nlv-setup.py > "$stagedir/nlv-setup.py"
sed -e "s/__VER__/$ver/" < Plugin/Template/tpl-nlv.mythtv-setup.py > Plugin/nlv.mythtv-setup.py

sqlite_lib=$wrkdir/sqlite3.lib

if [ -n "$cfg_clean" ]; then
  rm "$sqlite_lib"

else
  if [ ! -f "$sqlite_lib" ]; then
    runbat Scripts/build_sqlite_lib.bat
  fi
fi

addenvvar SQLITE_LIB_DIR "$wrkdir"

if [ -z "$cfg_clean" ]; then
  msg_header "Building NLV Release"
  time runbat Scripts/build_nlv.bat 2>&1 | tee "${logdir}/nlv.build.log"
fi

vsnlv_build="${logdir}/vsnlv.build.log"
vsnlv_clean="${logdir}/vsnlv.clean.log"

if [ -n "$cfg_clean" ]; then
  msg_header "Cleaning vsNLV"
  runbat Scripts/build_vsnlv.bat 2>&1 | tee "${vsnlv_clean}"

else
  msg_header "Building vsNLV"
  time runbat Scripts/build_vsnlv.bat 2>&1 | tee "${vsnlv_build}"
fi



###############################################################################
# Developer support
###############################################################################

if [ -z "$cfg_clean" ]; then
  msg_header "Setup VisualStudio debug environment"
  runbat Scripts/dbg_setup.bat 2>&1 | tee "${logdir}/debug_setup.log"
fi



###############################################################################
# Finish
###############################################################################

# close the .props file now
echo "  </PropertyGroup>" >> $envprops
echo "</Project>" >> $envprops

# as a convenience, customise the Visual Studio Python project file to allow
# debugging to work
projfile="Application/Nlv/Nlv.pyproj"
tplfile="Application/Template/tpl-Nlv.pyproj"

if [ -n "$cfg_clean" ]; then
  rm $projfile
  
elif [ ! -f "$projfile" ]; then 
  wtestdir=`cygpath -a -m "$testdir"`
  subst=`cat $pathvar | sed -e 's|\\\\|\\\\\\\\|'g`
  sed -e "s@__ENVIRONMENT__@PATH=$subst@" < $tplfile \
    | sed -e "s@__TESTDIR__@$wtestdir@" > $projfile 

fi

msg_line "Build finished"
