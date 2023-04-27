..  
  Copyright (C) Niel Clausen 2018. All rights reserved.
  
  This program is free software: you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.
  
  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
  GNU General Public License for more details.
  
  You should have received a copy of the GNU General Public License
  along with this program. If not, see <https://www.gnu.org/licenses/>.


Building
========

Structure
---------

NLV is a Python program and relies on customised versions of wxPython & wxWidgets
to provide all Windows UI capabilities. These are provided as Git submodules.

NLV relies on NlvLog, a C++ DLL, for all searching, mapping and indexing tasks. The
NlvLog DLL makes use of a number of Open Source packages.

Building requires downloading the dependencies, patching wxWidgets, and compiling
& packaging the source. It is recommended the supplied build.sh script is
used to do this.


Tools
-----

The build machine should have the following tools installed:

* CygWin: (x32 or x64): base install + git + graphviz + wget + unzip (https://www.cygwin.com/)
* Python 3.6.x: 64-bit install, ensure Python is added to path (https://www.python.org/)
* Visual Studio 2015 Community Edition (https://www.visualstudio.com/vs/older-downloads/).

  To run the Unit Tests, install the "Google Test Adapter" extension (from
  TOOLS | Extensions and Updates | Online).

* Optionally, Visual Studio 2017 Community Edition (https://www.visualstudio.com/).
  This toolchain is required to build the VisualStudio extension. If the toolchain is
  not installed, the extension will not be built.

  In the installer, select the "Visual Studio extension development" workload. Also,
  under "Individual components" select Windows 10 SDK (10.0.14393.0). The SDK is
  required to workaround a corruption to the VisualStudio 2015 environment that
  occurs when VisualStudio 2017 is installed. The corruption causes the WAF builder
  in wxPython to fail.
 

Other

* The NuGet command line tool (https://docs.microsoft.com/en-us/nuget/tools/nuget-exe-cli-reference)
  is used, and is downloaded if needed.

Setup
-----

See :doc:`references` for more information on the source dependencies. NLV
makes use of the following Open Source projects:

* BOOST
* Intel Thread Building Blocks (TBB)
* GoogleTest
* JSON v3.1.2
* wxPython (GIT version 5c7046bdbc9a5a6889363793e2904c4faccd9111)
* wxWidgets 3.1.1 (GIT version 379a404f9804ac044df44f18907e192917fec8aa)

NLV is distributed as a single archive nlv.rel.xxx.tar.bz2, where xxx is
the release number. Compatible versions of BOOST and the Intel TBB library
are usually also available. From a CygWin prompt::

  $ ls ~/Export
  boost_1_63_0.tar.bz2  nlv.rel.200.tar.bz2  tbb-2018_U2.tar.gz

Extract the build setup script from the archive. This only needs to be
done once::

  $ tar xfj ~/Export/nlv.rel.200.tar.bz2 nlvsetup.sh

The setup script requires two arguments:

* the path to the NLV archive
* one of

  * --full, reverts the whole Phoenix tree, triggering a full rebuild
  * --vstc, applies the VSTC patch; implied for --full
  * --quick, no changes to Phoenix/wxWidgets; relatively quick build

where --vstc is recommended.

The script unpacks BOOST/TBB from the archives and fetches the
other Open Source projects from GitHub. It then builds all projects::

  $ ./nlvsetup.sh nlv.rel.200.tar.bz2 --vstc
  =======================================================================
  Get release
  =======================================================================

  ...

  =======================================================================
  ==== Build Complete
  Installation files can be found in C:\Dev\Installers\200

The script then performs a developer install, which permits Visual Studio
to be used to run/debug NLV::

  =======================================================================
  ==== NLV developer environment

  ...

  =======================================================================
  NLV development environment installed to C:\Dev\Nlv\_PyEnv\Dbg
  Double-click the solution file; ensure the Nlv\_PyEnv\Dbg Python virtual
  environment is setup and activated:
    Solution Platforms = x64
    Solution Explorer ] Nlv ] Python Environments ] Add Existing Virtual Environment...
    Solution Explorer ] Nlv ] Python Environments ] Dbg (Python 36) ] Activate Environment


Install
-------

On a deployment machine, copy the install directory from the build machine. 
The ``install.bat`` script installs the resulting Python packages::

  C:\Installers\200>install
  =======================================================================
  Using ..\PyEnvNlv as the Python virtual environment for NLV

  =======================================================================
  ==== NLV

  ...

  Successfully installed Nlv-200 NlvMythTV-200

  =======================================================================
  NLV installed to \Scripts
  In Explorer, right click the file and select "Pin to start"

To install into a specified Python virtual environment, supply the environment's
path to the install script. In this case, it isn't necessary to copy the install
files to the local machine.
