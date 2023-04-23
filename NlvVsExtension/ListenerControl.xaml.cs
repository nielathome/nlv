//
// Copyright 2018 by Niel Clausen. All rights reserved.
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program. If not, see <https://www.gnu.org/licenses/>.
//

using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.IO.Pipes;
using System.Threading;
using System.Windows;
using System.Windows.Controls;
using System.Linq;
using System.Xml.Linq;
using System.Runtime.InteropServices;

using Microsoft.VisualStudio.Shell.Interop;
using Microsoft.VisualStudio.TextManager.Interop;

using MsVsShell = Microsoft.VisualStudio.Shell;
using VsConstants = Microsoft.VisualStudio.VSConstants;
using ErrorHandler = Microsoft.VisualStudio.ErrorHandler;

namespace NLV.VisualStudio
{
    // data source to be bound into the list view
    [ComVisible(false)]
    public class LogLine : DependencyObject
    {
        // log text displayed in the NLV view
        public string LogText
        {
            get { return (string)GetValue(LogTextProperty); }
            set { SetValue(LogTextProperty, value); }
        }

        // emitter field text
        public string Emitter
        {
            get { return (string)GetValue(EmitterProperty); }
            set { SetValue(EmitterProperty, value); }
        }

        public static readonly DependencyProperty LogTextProperty =
            DependencyProperty.Register("LogText", typeof(string), typeof(LogLine), new PropertyMetadata(""));

        public static readonly DependencyProperty EmitterProperty =
            DependencyProperty.Register("Emitter", typeof(string), typeof(LogLine), new PropertyMetadata(""));

        // source location data associated with this log line
        public string m_Path;
        public int m_LineNo;
    }


    [ComVisible(false)]
    public partial class ListenerControl : UserControl, IDisposable
    {
        public ListenerControl()
        {
            InitializeComponent();
            InitList();
        }


        #region IDisposable Support
        private bool disposedValue = false; // To detect redundant calls

        protected virtual void Dispose(bool disposing)
        {
            if (!disposedValue)
            {
                if (disposing)
                {
                    if (m_PipeReadTask != null)
                        ((IDisposable)m_PipeReadTask).Dispose();

                    if (m_PipeReadCancel != null)
                        ((IDisposable)m_PipeReadCancel).Dispose();

                    if (m_Pipe != null)
                        m_Pipe.Dispose();

                    if (m_IdleManager != null)
                        ((IDisposable)m_IdleManager).Dispose();
                }

                disposedValue = true;
            }
        }

        // This code added to correctly implement the disposable pattern.
        public void Dispose()
        {
            Dispose(true);
        }
        #endregion
        
        

        // --------------------------------------------------------------
        // Trace/log service
        // --------------------------------------------------------------

        // GUID for NLV output pane
        private static readonly Guid s_OutputPaneGuid = new Guid("F55EEC22-1653-4534-B256-E341319BFE8A");


        // create the output pane
        public static void MakeOutputPane()
        {
            IVsOutputWindow window = MsVsShell.Package.GetGlobalService(typeof(SVsOutputWindow)) as IVsOutputWindow;
            Guid guid = s_OutputPaneGuid;
            window.CreatePane(ref guid, "NLV listener", 1, 0);
        }


        // provide user visibility of extension's actions
        private void OutputString(string message)
        {
            IVsOutputWindow window = MsVsShell.Package.GetGlobalService(typeof(SVsOutputWindow)) as IVsOutputWindow;
            if (window == null)
                return;

            IVsOutputWindowPane pane;
            Guid guid = s_OutputPaneGuid;
            if (ErrorHandler.Failed(window.GetPane(ref guid, out pane)))
                return;

            if(pane != null)
                pane.OutputString(message + "\n");
        }



        // --------------------------------------------------------------
        // Pipe management
        // --------------------------------------------------------------

        // pipe state
        private static int s_PipeSize = 16184;
        private NamedPipeClientStream m_Pipe = null;
        private string m_ChannelName = "";
        private Byte[] m_PipeReadData;
        private CancellationTokenSource m_PipeReadCancel = null;
        private System.Threading.Tasks.Task<int> m_PipeReadTask;

        // idle time manager
        private MsVsShell.SingleTaskIdleManager m_IdleManager = null;


        private void SwitchPipe(bool disconnect, string name, string guid)
        {
            if (m_Pipe != null)
                PipeClose();

            if (disconnect)
                return;

            PipeCreate(name, guid);

            if (m_IdleManager == null)
            {
                MsVsShell.OnIdleHandler onIdleHandler = OnIdle;
                m_IdleManager = new MsVsShell.SingleTaskIdleManager(onIdleHandler);
            }
        }


        private void PipeCreate(string name, string guid)
        {
            m_ChannelName = name;
            string pipe_name = "NLV-" + guid;

            // the simple NamedPipeClientStream(String, String, PipeDirection) constructor
            // fails badly, due to a MS bug that causes the pipe handle to end up with
            // incorrect permissions. As a result, trying to set the read mode to "message"
            // fails with an authorisation exception. The workaround here comes from 
            // https://stackoverflow.com/questions/32739224/c-sharp-unauthorizedaccessexception-when-enabling-messagemode-for-read-only-name
            m_Pipe = new NamedPipeClientStream
            (
                ".",
                pipe_name,
                PipeAccessRights.ReadData | PipeAccessRights.WriteAttributes,
                PipeOptions.None,
                System.Security.Principal.TokenImpersonationLevel.None,
                System.IO.HandleInheritability.None
            );
        }


        private void PipeClose()
        {
            if (m_PipeReadCancel != null)
                m_PipeReadCancel.Cancel();

            m_Pipe.Close();
            m_Pipe = null;

            OutputString(System.String.Format("Disconnected channel '{0}'", m_ChannelName));
        }


        private void PipeConnect()
        {
            try
            {
                // polled pipe connection
                m_Pipe.Connect(0);

                // still here - must be connected then
                m_Pipe.ReadMode = PipeTransmissionMode.Message;

                OutputString(System.String.Format("Connected channel '{0}'", m_ChannelName));
                PipeStartRead();
            }
            catch (TimeoutException)
            {
            }
            catch (System.IO.IOException)
            {
            }
            catch (Exception ex)
            {
                OutputString(System.String.Format("Unable to connect to channel: reason: {0}", ex.Message));
            }
        }


        private void PipeStartRead()
        {
            m_PipeReadData = new Byte[s_PipeSize];
            if (m_PipeReadCancel != null)
                m_PipeReadCancel.Dispose();

            m_PipeReadCancel = new CancellationTokenSource();
            m_PipeReadTask = m_Pipe.ReadAsync(m_PipeReadData, 0, s_PipeSize, m_PipeReadCancel.Token);
        }


        private void PipeCheckRead()
        {
            if (m_PipeReadTask.Status == System.Threading.Tasks.TaskStatus.RanToCompletion)
            {
                int len = m_PipeReadTask.Result;

                try
                {
                    string text = System.Text.Encoding.UTF8.GetString(m_PipeReadData).Remove(len);
                    PipeStartRead();
                    OnPipeMessage(text);
                }
                catch (Exception ex)
                {
                    OutputString(System.String.Format("Unable to read channel: reason: {0}", ex.Message));
                }
            }
        }


        // idle time handler runs the pipe; not clear why it returns an enumerable
        public System.Collections.IEnumerable OnIdle()
        {
            if (m_Pipe != null)
            {
                if (!m_Pipe.IsConnected)
                    PipeConnect();
                else
                    PipeCheckRead();
            }

            return null;
        }



        // --------------------------------------------------------------
        // Message handling
        // --------------------------------------------------------------

        private void OnPipeMessage(string text)
        {
            try
            {
                XElement message = XElement.Parse(text);
                string path = (string)message.Element("path");
                int line = (int)message.Element("line");
                string log = (string)message.Element("log");
                string emitter = (string)message.Element("emitter");

                AddListItem(log, emitter, path, line);
            }
            catch(Exception ex)
            {
                OutputString(System.String.Format("Unable to process channel communication: reason: {0}", ex.Message));
            }
        }



        // --------------------------------------------------------------
        // List handling
        // --------------------------------------------------------------

        private ObservableCollection<LogLine> m_ListContents = new ObservableCollection<LogLine>();

        private void AddListItem(string log_text, string emitter, string path, int line_no)
        {
            LogLine line = new LogLine();
            line.LogText = log_text;
            line.Emitter = emitter;
            line.m_Path = path;
            line.m_LineNo = line_no;

            m_ListContents.Insert(0, line);
            m_ListView.SelectedIndex = 0;
        }


        private void InitList()
        {
            m_ListView.ItemsSource = m_ListContents;
        }


        public void OnClear()
        {
            m_ListContents.Clear();
        }


        public void OnPrev()
        {
            int selection = m_ListView.SelectedIndex - 1;
            if (selection >= 0)
                m_ListView.SelectedIndex = selection;
        }


        public void OnNext()
        {
            int selection = m_ListView.SelectedIndex + 1;
            if(selection < m_ListContents.Count)
                m_ListView.SelectedIndex = selection;
        }


        private void OnSelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            int selection = m_ListView.SelectedIndex;
            if (selection >= 0)
            {
                LogLine line = m_ListContents[selection];
                ShowSource(line.Emitter, line.m_Path, line.m_LineNo);
            }
        }



        // --------------------------------------------------------------
        // Combo handling
        // --------------------------------------------------------------

        private List<string> m_ChannelNames, m_ChannelGuids;
        private int m_ChannelIdx = 0;
        private bool m_GotChannelNames = false;


        private void SetupChannelNames()
        {
            if (!m_GotChannelNames)
            {
                m_GotChannelNames = true;

                // the list of channels available to this user are
                // listed in a "well known" location
                string path = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
                path += "\\NLV\\Channels.xml";

                List<string> names = new List<string>(), guids = new List<string>();
                names.Add("--None--");
                guids.Add("");
                names.Add("Default");
                guids.Add("8C8F999F-6448-4482-84C4-31DFAFFF7EE4");

                try
                {
                    XElement root = XElement.Load(path);
                    IEnumerable<XElement> channels =
                        from e in root.Elements("channel")
                        select e;

                    foreach (XElement channel in channels)
                    {
                        names.Add((string)channel.Attribute("name"));
                        guids.Add(channel.Value);
                    }
                }
                catch (Exception ex)
                {
                    OutputString(System.String.Format("Unable to process channels list: reason: {0}", ex.Message));
                }

                m_ChannelNames = names;
                m_ChannelGuids = guids;
            }
        }


        //
        // A DropDownCombo combobox requires two commands:
        //   One command (cmdidCombo) is used to ask for the current value for the
        //    display area of the combo box and to set the new value when the user
        //    makes a choice in the combo box.
        //
        //   The second command (cmdidComboGetList) is used to retrieve the list of
        //    choices for the combo box drop down area.
        // 
        // Normally IOleCommandTarget::QueryStatus is used to determine the state of
        // a command, e.g. enable vs. disable, shown vs. hidden, etc. The QueryStatus
        // method does not have enough flexibility for combos which need to be able
        // to indicate a currently selected (displayed) item as well as provide a list
        // of items for their dropdown area. In order to communicate this information
        // actually IOleCommandTarget::Exec is used with a non-NULL varOut parameter. 
        // You can think of these Exec calls as extended QueryStatus calls. There are
        // two pieces of information needed for a combo, thus it takes two commands
        // to retrieve this information. The main command id for the command is used
        // to retrieve the current value and the second command is used to retrieve
        // the full list of choices to be displayed as an array of strings.
        //

        public void OnCombo(EventArgs args)
        {
            MsVsShell.OleMenuCmdEventArgs eventArgs = args as MsVsShell.OleMenuCmdEventArgs;

            if (eventArgs == null)
                return;

            object input = eventArgs.InValue;
            IntPtr vOut = eventArgs.OutValue;

            if (vOut != IntPtr.Zero)
            {
                // when vOut is non-NULL, the IDE is requesting the current value
                // for the combo
                SetupChannelNames();
                Marshal.GetNativeVariantForObject(m_ChannelNames[m_ChannelIdx], vOut);
            }

            else if (input != null)
            {
                int newChoice = -1;
                if (!int.TryParse(input.ToString(), out newChoice))
                {
                    // user typed a string argument in command window.
                    int i = 0;
                    foreach (string name in m_ChannelNames)
                    {
                        if (string.Compare(name, input.ToString(), StringComparison.CurrentCultureIgnoreCase) == 0)
                        {
                            newChoice = i;
                            break;
                        }
                        i += 1;
                    }
                }

                // new value was selected or typed in
                if (newChoice != -1 && newChoice != m_ChannelIdx)
                {
                    m_ChannelIdx = newChoice;
                    SwitchPipe(m_ChannelIdx == 0, m_ChannelNames[m_ChannelIdx], m_ChannelGuids[m_ChannelIdx]);
                }
            }
        }


        public void OnComboGetList(EventArgs args)
        {
            MsVsShell.OleMenuCmdEventArgs eventArgs = args as MsVsShell.OleMenuCmdEventArgs;

            if (eventArgs == null)
                return;

            IntPtr vOut = eventArgs.OutValue;

            if (vOut == IntPtr.Zero)
                return;

            SetupChannelNames();

            int size = m_ChannelNames.Count();
            string[] names = new string[size];
            for (int i = 0; i < size; ++i)
                names[i] = m_ChannelNames[i];

            Marshal.GetNativeVariantForObject(names, vOut);
        }



        // --------------------------------------------------------------
        // Editor control
        // --------------------------------------------------------------

        private void ShowSource(string emitter, string path, int line_no)
        {
            IVsUIShellOpenDocument od = (IVsUIShellOpenDocument)MsVsShell.Package.GetGlobalService(typeof(SVsUIShellOpenDocument));

            // not clear why lookup needs a string array; documentation does not mention returning
            // more than one path
            uint search_strategy = (uint)__VSRELPATHSEARCHFLAGS.RPS_UseAllSearchStrategies;
            String[] found_abs_paths = new String[1];
            int res = od.SearchProjectsForRelativePath(search_strategy, path, found_abs_paths);

            // if the whole path wasn't found, retry with just the filename
            String chosen_abs_path;
            if (res != VsConstants.S_OK)
            {
                int last_elem_pos = path.LastIndexOf('\\');
                if (last_elem_pos >= 0)
                {
                    string last_elem = path.Substring(last_elem_pos + 1);
                    res = od.SearchProjectsForRelativePath(search_strategy, last_elem, found_abs_paths);
                }
            }

            if (res == VsConstants.S_OK)
                chosen_abs_path = found_abs_paths[0];
            else
            {
                OutputString(System.String.Format("Unable to find source code in any project: path:'{0}' line:{1}", path, line_no));
                return;
            }

            // fetch a hierarchy for the absolute path
            IVsUIHierarchy hierarchy;
            UInt32 item_id;
            Microsoft.VisualStudio.OLE.Interop.IServiceProvider provider;
            Int32 in_proj;
            res = od.IsDocumentInAProject(chosen_abs_path, out hierarchy, out item_id, out provider, out in_proj);

            if (res != VsConstants.S_OK)
            {
                OutputString(System.String.Format("Unable to find project for source code: emitter: '{0}'", emitter));
                return;
            }

            if (in_proj == 0)
            {
                OutputString(System.String.Format("Unable to find source code in project: emitter: '{0}'", emitter));
                return;
            }

            // convert the hierarchy to a project, and open & show the source code document
            IVsProject project = (IVsProject)hierarchy;
            IntPtr DOCDATAEXISTING_UNKNOWN = (IntPtr)(int)-1;
            Guid logical_view = new Guid(LogicalViewID.Code);
            IVsWindowFrame frame;
            res = project.OpenItem(item_id, logical_view, DOCDATAEXISTING_UNKNOWN, out frame);

            if (res != VsConstants.S_OK)
            {
                OutputString(System.String.Format("Unable to open editor for source code: emitter: '{0}'", emitter));
                return;
            }

            frame.Show();

            // move the cursor to the correct line in the editor
            IVsTextView text_view = Microsoft.VisualStudio.Shell.VsShellUtilities.GetTextView(frame);
            if (text_view == null)
            {
                OutputString(System.String.Format("Unable to access editor for source code: emitter: '{0}'", emitter));
                return;
            }

            line_no = line_no - 1;
            res = text_view.SetCaretPos(line_no, 0);
            if (res != VsConstants.S_OK)
            {
                OutputString(System.String.Format("Unable to set cursor to source code: emitter: '{0}'", emitter));
                return;
            }

            // and finally, centre the view on the source code line - ignore errors, it doesn't
            // matter that much
            text_view.CenterLines(line_no, 1);
        }
    }
}
