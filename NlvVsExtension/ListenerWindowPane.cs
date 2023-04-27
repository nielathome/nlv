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

namespace NLV.VisualStudio
{
	/// <summary>
	/// This ListenerWindowPane demonstrates the following features:
	///	 - Hosting a user control in a tool window
	///	 - Persistence (visible when VS starts based on state when VS closed)
	///	 - Tool window Toolbar
	///	 - Selection tracking (content of the Properties window is based on 
	///	   the selection in that window)
	/// 
	/// Tool windows are composed of a frame (provided by Visual Studio) and a
	/// pane (provided by the package implementer). The frame implements
	/// IVsWindowFrame while the pane implements IVsWindowPane.
	/// 
	/// ListenerWindowPane inherits the IVsWindowPane implementation from its
	/// base class (ToolWindowPane). ListenerWindowPane will host a .NET
	/// UserControl (PersistedWindowControl). The Package base class will
	/// get the user control by asking for the Window property on this class.
	/// </summary>
	[Guid("7C3A37FC-2E9A-4B10-8EEC-A79178A80CA7")]
	class ListenerWindowPane : MsVsShell.ToolWindowPane
	{
		// Control that will be hosted in the tool window
		private ListenerControl m_Control = null;


		/// <summary>
		/// Constructor for ToolWindowPane.
		/// Initialization that depends on the package or that requires access
		/// to VS services should be done in OnToolWindowCreated.
		/// </summary>
		public ListenerWindowPane()
			: base(null)
		{
            // Set the image that will appear on the tab of the window frame when docked with another window.
            // KnownMonikers is a set of image monkiers that are globablly recognized by VS. These images can be
            // used in any project without needing to include the source image.
            BitmapImageMoniker = Microsoft.VisualStudio.Imaging.KnownMonikers.GoToSourceCode;

			// Add the toolbar by specifying the Guid/MenuID pair corresponding to
			// the toolbar definition in the vsct file.
			ToolBar = new CommandID(GuidsList.guidClientCmdSet, PkgCmdId.IDM_MyToolbar);

			// Specify that we want the toolbar at the top of the window
			ToolBarLocation = (int)VSTWT_LOCATION.VSTWT_TOP;

            // Set the text that will appear in the title bar of the tool window.
            this.Caption = "NLV Listener";

            // Creating the user control that will be displayed in the window - change this to content
            Content = (m_Control = new ListenerControl());
		}
        

		/// <summary>
		/// This is called after our control has been created and sited.
		/// This is a good place to initialize the control with data gathered
		/// from Visual Studio services.
		/// </summary>
		public override void OnToolWindowCreated()
		{
			base.OnToolWindowCreated();

			// Add the handler for our toolbar buttons
			CommandID id = new CommandID(GuidsList.guidClientCmdSet, PkgCmdId.cmdidLogListClear);
			DefineCommandHandler(new EventHandler(this.OnLogListClear), id);

            id = new CommandID(GuidsList.guidClientCmdSet, PkgCmdId.cmdidLogListPrev);
            DefineCommandHandler(new EventHandler(this.OnLogListPrev), id);

            id = new CommandID(GuidsList.guidClientCmdSet, PkgCmdId.cmdidLogListNext);
            DefineCommandHandler(new EventHandler(this.OnLogListNext), id);

            id = new CommandID(GuidsList.guidClientCmdSet, PkgCmdId.cmdidCombo);
            DefineCommandHandler(new EventHandler(this.OnCombo), id);

            id = new CommandID(GuidsList.guidClientCmdSet, PkgCmdId.cmdidComboGetList);
            DefineCommandHandler(new EventHandler(this.OnComboGetList), id);

            // Ensure the control's handle has been created; otherwise, BeginInvoke cannot be called.
            // Note that during runtime this should have no effect when running inside Visual Studio,
            // as the control's handle should already be created, but unit tests can end up calling
            // this method without the control being created.
            m_Control.InitializeComponent();

            // setup output pane
            ListenerControl.MakeOutputPane();
        }

		private void OnLogListClear(object sender, EventArgs arguments)
		{
            m_Control.OnClear();
		}

        private void OnLogListPrev(object sender, EventArgs arguments)
        {
            m_Control.OnPrev();
        }

        private void OnLogListNext(object sender, EventArgs arguments)
        {
            m_Control.OnNext();
        }

        private void OnCombo(object sender, EventArgs arguments)
        {
            m_Control.OnCombo(arguments);
        }

        private void OnComboGetList(object sender, EventArgs arguments)
        {
            m_Control.OnComboGetList(arguments);
        }


        /// <summary>
        /// Define a command handler.
        /// When the user presses the button corresponding to the CommandID,
        /// then the EventHandler will be called.
        /// </summary>
        /// <param name="id">The CommandID (Guid/ID pair) as defined in the .vsct file</param>
        /// <param name="handler">Method that should be called to implement the command</param>
        /// <returns>The menu command. This can be used to set parameter such as the default visibility once the package is loaded</returns>
        private MsVsShell.OleMenuCommand DefineCommandHandler(EventHandler handler, CommandID id)
		{
			// First add it to the package. This is to keep the visibility
			// of the command on the toolbar constant when the tool window does
			// not have focus. In addition, it creates the command object for us.
			PackageToolWindow package = (PackageToolWindow)this.Package;
            MsVsShell.OleMenuCommand command = package.DefineCommandHandler(handler, id);
			// Verify that the command was added
			if (command == null)
				return command;

			// Get the OleCommandService object provided by the base window pane class; this object is the one
			// responsible for handling the collection of commands implemented by the package.
			MsVsShell.OleMenuCommandService menuService = GetService(typeof(IMenuCommandService)) as MsVsShell.OleMenuCommandService;
			
			if (null != menuService)
			{
				// Add the command handler
				menuService.AddCommand(command);
			}
			return command;
		}
	}
}
