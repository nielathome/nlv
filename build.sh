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

#directory structure
blddir=`pwd`
wrkdir="$blddir/_Work"
pkgdir="$blddir/Deps/Packages"
instdir="$wrkdir/Installers/$ver"
logdir="$wrkdir/Logs"
mkdir -p "$logdir" "$pkgdir" "$instdir" 

# initialise DLL path
pathvar=$wrkdir/path.txt
echo -n `cygpath -w -p "$PATH"` > $pathvar

# initialise Windows environment
envbat=$wrkdir/env.bat
echo SET NLV=$ver > $envbat
echo "SET B2_ARGS=$b2_args" >> $envbat
echo "SET MSBUILD_ARGS=$msbuild_args" >> $envbat
echo "SET MSBUILD_TARGET=$msbuild_target" >> $envbat
echo "SET PIP_ARGS=$pip_args" >> $envbat
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
addenvvar PYTHON "$python"
addenvprops PYTHON "`dirname $python`"

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
echo -n ";`cygpath -w ${boost_pkg}/stage/x64/lib`" >> $pathvar 

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
  
fi

addenv TBB "${tbb_dir}"
echo -n ";`cygpath -w ${tbb_pkg}/build/vs2013/x64/Debug`" >> $pathvar 

if [ -n "$cfg_clean" ]; then
  msg_header "Cleaning TBB ${tbb_name}"
  rm -f "${tbb_build}" 
  runbat Scripts/build_tbb.bat 2>&1 | tee "${tbb_clean}"

elif [ ! -f "$tbb_build" ]; then
  msg_header "Building TBB ${tbb_name}"
  time runbat Scripts/build_tbb.bat 2>&1 | tee "${tbb_build}"
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
# Finish
###############################################################################

echo "  </PropertyGroup>" >> $envprops
echo "</Project>" >> $envprops

msg_line "Build finished"
