/***************************************************************************

Copyright (c) Microsoft Corporation. All rights reserved.
THIS CODE IS PROVIDED *AS IS* WITHOUT WARRANTY OF
ANY KIND, EITHER EXPRESS OR IMPLIED, INCLUDING ANY
IMPLIED WARRANTIES OF FITNESS FOR A PARTICULAR
PURPOSE, MERCHANTABILITY, OR NON-INFRINGEMENT.

***************************************************************************/

using System;
using System.ComponentModel.Design;
using System.Runtime.InteropServices;
using Microsoft.VisualStudio.Shell.Interop;

using MsVsShell = Microsoft.VisualStudio.Shell;
using ErrorHandler = Microsoft.VisualStudio.ErrorHandler;

//
// References
// . https://github.com/Microsoft/VSSDK-Extensibility-Samples/tree/master/Combo_Box
//

namespace NLV.VisualStudio
{
    /// <summary>
    /// This is the class that implements the package exposed by this assembly.
    ///
    /// The minimum requirement for a class to be considered a valid package for
    /// Visual Studio is to implement the IVsPackage interface and register itself
    /// with the shell. This package uses the helper classes defined inside the
    /// Managed Package Framework (MPF) to do it: it derives from the Package class
    /// that provides the implementation of the IVsPackage interface and uses
    /// the registration attributes defined in the framework to register itself
    /// and its components with the shell.
    /// </summary>

    //
    // The Package class is responsible for the following:
    //		- Attributes to enable registration of the components
    //		- Enable the creation of our tool windows
    //		- Respond to our commands
    // 
    // The following attributes are covered in other samples:
    //		PackageRegistration:   Reference.Package
    //		ProvideMenuResource:   Reference.MenuAndCommands
    // 
    // Our initialize method defines the command handlers for the commands that
    // we provide under View | Other Windows to show our tool windows
    // 

    // The first new attribute we are using is ProvideToolWindow. That attribute
    // is used to advertise that our package provides a tool window. In addition
    // it can specify optional parameters to describe the default start location
    // of the tool window. For example, the ListenerWindowPane will start tabbed
    // with Solution Explorer. The default position is only used the very first
    // time a tool window with a specific Guid is shown for a user. After that,
    // the position is persisted based on the last known position of the window.
    // When trying different default start positions, you may find it useful to
    // delete *.prf from:
    //		"%USERPROFILE%\Application Data\Microsoft\VisualStudio\10.0Exp\"
    // as this is where the positions of the tool windows are persisted.
    // 
    // To get the Guid corresponding to the Solution Explorer window, we ran this
    // sample, made sure the Solution Explorer was visible, selected it in the
    // Persisted Tool Window and looked at the properties in the Properties
    // window. You can do the same for any window.
    [MsVsShell.ProvideToolWindow(typeof(ListenerWindowPane), Style = MsVsShell.VsDockStyle.Tabbed, Window = "3ae79031-e1bc-11d0-8f78-00a0c9110057")]

    // This attribute is needed to let the shell know that this package exposes
    // VS commands (menus, buttons, etc...)
    [MsVsShell.ProvideMenuResource(1000, 1)]

    // This attribute tells the registration utility (regpkg.exe) that this
    // class needs to be registered as package.
    [MsVsShell.PackageRegistration(UseManagedResourcesOnly = true)]

	[Guid("D36AA01F-2FB4-4A38-B527-8411E9CE0226")]
	public class PackageToolWindow : MsVsShell.Package
	{
		// Cache the Menu Command Service since we will use it multiple times
		private MsVsShell.OleMenuCommandService menuService;


        /// <summary>
        /// Default constructor of the package.
        /// Inside this method you can place any initialization code that does
        /// not require any Visual Studio service because at this point the
        /// package object is created but not sited yet inside Visual Studio
        /// environment. The place to do all the other initialization is the
        /// Initialize method.
        /// </summary>
        public PackageToolWindow()
        {
        }


        /// <summary>
        /// Initialization of the package; this method is called right after the
        /// package is sited, so this is the place where you can put all the
        /// initilaization code that rely on services provided by VisualStudio.
        /// </summary>
        protected override void Initialize()
		{
			base.Initialize();

			// Create one object derived from MenuCommand for each command defined in
			// the VSCT file and add it to the command service.

			// Each command is uniquely identified by a Guid/integer pair.
			CommandID id = new CommandID(GuidsList.guidClientCmdSet, PkgCmdId.cmdidToolWindowShow);

			// Add the handler for the persisted window with selection tracking
			DefineCommandHandler(new EventHandler(ShowPersistedWindow), id);
		}


		/// <summary>
		/// Define a command handler.
		/// When the user press the button corresponding to the CommandID
		/// the EventHandler will be called.
		/// </summary>
		/// <param name="id">The CommandID (Guid/ID pair) as defined in the .vsct file</param>
		/// <param name="handler">Method that should be called to implement the command</param>
		/// <returns>The menu command. This can be used to set parameter such as the default visibility once the package is loaded</returns>
		internal MsVsShell.OleMenuCommand DefineCommandHandler(EventHandler handler, CommandID id)
		{
			// if the package is zombied, we don't want to add commands
			if (Zombied)
				return null;

			// Make sure we have the service
			if (menuService == null)
			{
				// Get the OleCommandService object provided by the MPF; this object is the one
				// responsible for handling the collection of commands implemented by the package.
				menuService = GetService(typeof(IMenuCommandService)) as MsVsShell.OleMenuCommandService;
			}

			MsVsShell.OleMenuCommand command = null;
			if (null != menuService)
			{
				// Add the command handler
				command = new MsVsShell.OleMenuCommand(handler, id);
				menuService.AddCommand(command);
			}
			return command;
		}


		/// <summary>
		/// Event handler for our menu item.
		/// This results in the tool window being shown.
		/// </summary>
		/// <param name="sender"></param>
		/// <param name="arguments"></param>
		private void ShowPersistedWindow(object sender, EventArgs arguments)
		{
			// Get the 1 (index 0) and only instance of our tool window (if it does not already exist it will get created)
			MsVsShell.ToolWindowPane pane = FindToolWindow(typeof(ListenerWindowPane), 0, true);
			if (pane == null)
			{
				throw new COMException("Unable to locate NLV Listener pane");
			}

			IVsWindowFrame frame = pane.Frame as IVsWindowFrame;
			if (frame == null)
			{
				throw new COMException("Unable to locate NLV Listener frame");
			}

			// Bring the tool window to the front and give it focus
			ErrorHandler.ThrowOnFailure(frame.Show());
		}
	}
}
