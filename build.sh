#!/bin/bash
#
# Copyright (C) Niel Clausen 2018-2020. All rights reserved.
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
  echo "--clean-pyenv - when cleaning, also remove Python virtual environments"
  echo "--force - force BOOST/TBB (re-)build"
  echo "--help | -h - display help"
  echo "--install | -i - install the build"
  echo "--install-demo | -d - install the build with the standard demo"
  echo "--release | -r - increment release number"
  echo "--skip-phoenix - do not clean/build wxPython or wxWidgets"
  echo "--verbose | -v - increase detail in output"
}

cfg_clean=""
cfg_clean_pyenv=""
cfg_install=""
cfg_demo_install=""
cfg_force=""
cfg_release=""
cfg_verbose=""
cfg_skip_phoenix=""
for arg in $*; do

  case "$arg" in

    "--clean")
      cfg_clean=1
      ;;
        
    "--clean-pyenv")
      if [ -n "$cfg_clean" ]; then
        cfg_clean_pyenv=1
      fi
      ;;
      
    "--force")
      cfg_force=1
      ;;

    "--help"|"-h"|"/?")
      help
      exit 0
      ;;

    "--install"|"-i")
      cfg_install=1
      ;;

    "--install-demo"|"-d")
      cfg_install=1
      cfg_demo_install="--withdemo"
      ;;

    "--skip-phoenix")
      cfg_skip_phoenix=1
      ;;
      
    "--release"|"-r")
      cfg_release=1
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
function addenvpath()
{
  name=$1
  winpath=`cygpath -a -w "$2"`
  echo "SET $name=$winpath" >> $envbat
}

# add path variable to VisualStudio environment
function addpropspath()
{
  name=$1
  winpath=`cygpath -a -w "$2"`
  echo "    <$name>$winpath</$name>" >> $envprops
}

# add path variable to Windows and VisualStudio environments
function addenvpropspath()
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
if [ -n "$cfg_release" ]; then
  echo -n "0" > bld.txt
  tmp=`cat ver.txt`
  echo -n $(($tmp + 1)) > ver.txt
else
  tmp=`cat bld.txt`
  echo -n $(($tmp + 1)) > bld.txt
fi
ver="`cat ver.txt`.`cat bld.txt`"


# make the application version available to the Python code
sed -e "s/__DEV__/$ver/" < Application/Template/tpl-Version.py > Application/Nlv/Version.py

# directory structure
prjdir=`pwd`
wrkdir="$prjdir/_Work"
blddir="$wrkdir/Bld"
pkgdir="$prjdir/Deps/Packages"
instdir="$wrkdir/Installers/$ver"
logdir="$wrkdir/Logs"
stagedir="$wrkdir/Stage"
testdir="$wrkdir/Test"
mkdir -p "$blddir" "$pkgdir" "$instdir" "$logdir" "$stagedir" "$testdir"

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
addenvpath ROOT_DIR "."
addenvpath CYGWIN_BASE "/"
addenvpath BLDDIR "$blddir"
addenvpath INSTDIR "$instdir"
addenvpath LOGDIR "$logdir"
addenvpath STAGEDIR "$stagedir"

if [ -n "$http_proxy" ]; then
  echo "set HTTP_PROXY=$http_proxy" >> $envbat
fi

if [ -n "$https_proxy" ]; then
  echo "set HTTPS_PROXY=$https_proxy" >> $envbat
fi

if [ -n "$REQUESTS_CA_BUNDLE" ]; then
  echo "set REQUESTS_CA_BUNDLE=`cygpath -w "$REQUESTS_CA_BUNDLE"`" >> $envbat
fi

# initialise VisualStudio environment
envprops=$wrkdir/env.props
echo "<?xml version=\"1.0\" encoding=\"utf-8\"?>" > $envprops
echo "<Project xmlns=\"http://schemas.microsoft.com/developer/msbuild/2003\">" >> $envprops
echo "  <PropertyGroup>" >> $envprops

addenvpropspath GTEST "Deps/Modules/GoogleTest"
addenvpropspath JSON "Deps/Modules/Json"
addenvpropspath PHOENIX "Deps/Modules/Phoenix"
addenvpropspath WXWIDGETS "Deps/Modules/Phoenix/ext/wxWidgets"



###############################################################################
# Utility Functions
###############################################################################

function fail()
{
  echo
  echo "+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
  echo "$1"
  echo "Ref: $2"
  echo "+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
  exit 3
}

function findf()
{
  for i in "$@"
  do
    if [ -f "$i" ]; then
      echo "$i"
	  return 0
	fi
  done
  
  return 1
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
  `cygpath -u $COMSPEC` /C `cygpath -w $path` $2 $3 $4

  cd $prjdir
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

pyver=37
loc=`which -a python | fgrep $pyver`
python=`findf "$loc"`
if [ "$?" == 0 ]; then
  python_dir=`dirname "$python"`

  echo "SET PYVER=$pyver" >> $envbat
  addenvpath PYTHON "$python"
  addpropspath PYTHON "$python_dir"
else
  fail "Unable to locate Python $pyver" "$loc"
fi

loc="C:/Program Files (x86)/Microsoft Visual Studio 14.0/VC/vcvarsall.bat"
cyg_vs2015env=$(findf "$loc")
if [ "$?" == 0 ]; then
  addenvpath VS2015ENV "$cyg_vs2015env"
else
  fail "Unable to locate VisualStudio 2015" "$loc"
fi


loc1="C:/Program Files (x86)/Microsoft Visual Studio/2017/Community/Common7/Tools/VsDevCmd.bat"
loc2="C:/Program Files (x86)/Microsoft Visual Studio/2017/Enterprise/Common7/Tools/VsDevCmd.bat"
cyg_vs2017env=$(findf "$loc1" "$loc2")
if [ "$?" == 0 ]; then
  addenvpath VS2017ENV "$cyg_vs2017env"
else
  fail "Unable to locate VisualStudio 2017" "$loc1 $loc2"
fi



###############################################################################
# Python Virtual Environments
###############################################################################

pyenvbld="$wrkdir/PyEnv/Bld"
addenvpath PYENVBLD "$pyenvbld"

pyenvdbg="$wrkdir/PyEnv/Dbg"
addenvpath PYENVDBG "$pyenvdbg"

if [ -n "$cfg_clean_pyenv" ]; then

  msg_line "Remove Python virtual environments"
  rm -rf "$pyenvbld"
  rm -rf "$pyenvdbg"
    
else

  if [ ! -d "$pyenvbld" ]; then
  
    msg_line "Creating Python virtual environment directory for build"
    "$python" -m venv `cygpath -w $pyenvbld`
  fi
  
  if [ ! -d "$pyenvdbg" ]; then
    msg_line "Creating Python virtual environment directory for debugging"
    "$python" -m venv `cygpath -w $pyenvdbg`
  fi
fi



###############################################################################
# BOOST
###############################################################################

boost_ver=72
boost_name="boost_1_${boost_ver}_0"
boost_file="${boost_name}.tar.bz2"
boost_url="https://dl.bintray.com/boostorg/release/1.${boost_ver}.0/source/${boost_file}"
boost_path="$pkgdir/${boost_file}"
boost_dir="$pkgdir/${boost_name}"
boost_build="${logdir}/${boost_name}.build.log"
boost_clean="${logdir}/${boost_name}.clean.log"

if [ ! -d "$boost_dir" ]; then

  getfile $boost_url $boost_path   

  msg_line "Unpacking archive: $boost_file ..."
  tar xfj $boost_path -C $pkgdir

fi

addenvpropspath BOOST "${boost_dir}"
echo -n ";`cygpath -w ${boost_dir}/stage/x64/lib`" >> $pathvar 

if [ -n "$cfg_clean" ]; then
  msg_header "Cleaning BOOST ${boost_name}"
  rm -f "${boost_build}" 
  runbat Scripts/build_boost.bat 2>&1 | tee "${boost_clean}"

elif [ -n "$cfg_force" -o ! -f "$boost_build" ]; then
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

  # latest downloads extract to a different directory; fix
  if [ -d "$pkgdir/onetbb-${tbb_name}" ]; then
    mv "$pkgdir/onetbb-${tbb_name}" "$tbb_dir"
  fi
  
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

addenvpropspath TBB "${tbb_dir}"
echo -n ";`cygpath -w ${tbb_dir}/build/vs2013/x64/Debug`" >> $pathvar 
echo -n ";`cygpath -w ${tbb_dir}/build/vs2013/x64/Release`" >> $pathvar 

if [ -n "$cfg_clean" ]; then
  msg_header "Cleaning TBB ${tbb_name}"
  rm -f "${tbb_build}" 
  runbat Scripts/build_tbb.bat 2>&1 | tee "${tbb_clean}"

elif [ -n "$cfg_force" -o ! -f "$tbb_build" ]; then
  msg_header "Building TBB ${tbb_name}"
  time runbat Scripts/build_tbb.bat 2>&1 | tee "${tbb_build}"
fi



###############################################################################
# SQLite Header
###############################################################################

sql_name="amalgamation-3310100"
sql_file="sqlite-${sql_name}.zip"
sql_url="https://www.sqlite.org/2020/${sql_file}"
sql_path="$pkgdir/${sql_file}"
sql_dir="$pkgdir/sqlite-${sql_name}"

addenvpropspath SQLITE "${sql_dir}"

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
wxpythonver=`grep "^Version:" < Deps/Modules/Phoenix/Nlv_wxPython.egg-info/PKG-INFO  | tr -d '\r\n' | awk '{ printf("%s", $2); }'`
sed -e "s/__VER__/$ver/" -e "s/__WXPYTHONVER__/$wxpythonver/" < Application/Template/tpl-nlv-setup.py > "$stagedir/nlv-setup.py"
sed -e "s/__VER__/$ver/" < Plugin/Template/tpl-nlv.mythtv-setup.py > Plugin/nlv.mythtv-setup.py

sqlite_lib=$wrkdir/sqlite3.lib
addenvpath SQLITE_LIB_DIR "$wrkdir"

if [ -n "$cfg_clean" ]; then
  msg_header "Clean Sqlite import library"
  rm -f "$sqlite_lib"

else
  if [ ! -f "$sqlite_lib" ]; then
    msg_header "Build Sqlite import library"
    runbat Scripts/build_sqlite_lib.bat
  fi
fi

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
# Finish NLV build
###############################################################################

# close the .props file now
echo "  </PropertyGroup>" >> $envprops
echo "</Project>" >> $envprops

# as a convenience, customise the Visual Studio Python project file to allow
# debugging to work
projfile="Application/Nlv/Nlv.pyproj"
tplfile="Application/Template/tpl-Nlv.pyproj"

if [ -n "$cfg_clean" ]; then
  rm -rf "$blddir"
  rm -f $projfile
  
elif [ ! -f "$projfile" ]; then 
  wtestdir=`cygpath -a -m "$testdir"`
  subst=`cat $pathvar | sed -e 's|\\\\|\\\\\\\\|'g`
  sed -e "s@__ENVIRONMENT__@PATH=$subst@" < $tplfile \
    | sed -e "s@__TESTDIR__@$wtestdir@" > $projfile 

fi



###############################################################################
# Build any co-resident plugins
###############################################################################


for plugin in ../*/build-nlv.bat; do
  dir_name=`dirname ${plugin}`
  plugin_name=`basename ${dir_name}`
  msg_header "Build plugin: ${plugin_name}"  
  pushd $dir_name > /dev/null
  runbat build-nlv.bat 2>&1 | tee "${logdir}/Plugin-${plugin_name}.log"
  popd > /dev/null
done



###############################################################################
# If requested, install the build
###############################################################################

if [ -n "$cfg_install" ]; then
  msg_header "Install NLV ${ver}"  
  pushd $instdir > /dev/null
  runbat install.bat $cfg_demo_install 2>&1 | tee "${logdir}/install.log"
  popd > /dev/null
fi



###############################################################################
# All done
###############################################################################

msg_line "Build finished"
