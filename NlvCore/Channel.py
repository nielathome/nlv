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

# system imports
import logging

# pywin32 imports
import pywintypes
import win32file
import win32event
import win32pipe
import winerror



## Channel #################################################

class Channel:
    """
    Notify log file line navigation events to the NLV channel. Typically, the
    channel listener will locate and display the source code which emitted
    the log line.
    """


    #-------------------------------------------------------
    # class statics

    _MaxMessageSize = 4 * 1024
    _PipeSize = 4 * _MaxMessageSize

    _StateNone = 1
    _StateConnect = 2
    _StateConnecting = 3
    _StateReady = 4
    _StateWriting = 5
    _StateRecover = 6


    #-------------------------------------------------------
    def _CheckIO(self):
        """If needed, confirm the previous IO has completed; return True if it has"""
        if self._IoError == winerror.ERROR_SUCCESS:
            return True

        elif self._IoError == winerror.ERROR_IO_PENDING:
            res = win32event.WaitForSingleObject(self._Event, 0)
            if res == winerror.WAIT_TIMEOUT:
                return False
            elif res == win32event.WAIT_OBJECT_0:
                self._IoSent = win32file.GetOverlappedResult(self._Pipe, self._Overlapped, False)
                return True
            else:
                raise Exception("Unexpected wait result")

        else:
            raise Exception("Unexpected I/O result")


    #-------------------------------------------------------
    def _SetState(self, state):
        self._State = state
        return True
        

    def _StartConnection(self):
        self._Overlapped = pywintypes.OVERLAPPED()
        self._Overlapped.hEvent = self._Event
        self._IoError = win32pipe.ConnectNamedPipe(self._Pipe, self._Overlapped)
        return self._SetState(__class__._StateConnecting)


    def _CheckConnection(self):
        if self._CheckIO():
            logging.info("Notifier: started: channel:'{}'".format(self._Name))
            return self._SetState(__class__._StateReady)

        return False


    def _WriteMessage(self):
        if self._NextMessage is not None:
            byte_message = bytes(self._NextMessage, "utf-8")
            self._MessageLen = len(byte_message)

            self._LastMessage = self._NextMessage
            self._NextMessage = None

            if self._MessageLen > self._MaxMessageSize:
                logging.error("Notifier: oversized message, skipping: channel:'{}' len:'{}'".format(self._Name, self._MessageLen))
            else:
                self._Overlapped = pywintypes.OVERLAPPED()
                self._Overlapped.hEvent = self._Event
                self._IoError, self._IoSent = win32file.WriteFile(self._Pipe, byte_message, self._Overlapped)
                return self._SetState(__class__._StateWriting)

        return False


    def _CheckWrite(self):
        if self._CheckIO():
            if self._IoSent != self._MessageLen:
                raise Exception("Incomplete message write")

            return self._SetState(__class__._StateReady)

        return False


    def _Recover(self):
        win32pipe.DisconnectNamedPipe(self._Pipe)
        return self._SetState(__class__._StateConnect)


    #-------------------------------------------------------
    def _Run(self):
        """Step channel writer state machine"""

        if self._Pipe == win32file.INVALID_HANDLE_VALUE:
            return

        max_run = 5
        for i in range(max_run):

            recover = True
            cont = False

            try:
                if self._State == __class__._StateRecover:
                    cont = self._Recover()

                if self._State == __class__._StateConnect:
                    cont = self._StartConnection()

                if self._State == __class__._StateConnecting:
                    cont = self._CheckConnection()

                if self._State == __class__._StateReady:
                    cont = self._WriteMessage()

                if self._State == __class__._StateWriting:
                    cont = self._CheckWrite()

                recover = False

            except pywintypes.error as werr:
                logging.error("Notifier: WinError: channel:'{}' func:'{}' code:'{}' error:'{}'".format(self._Name, werr.funcname, werr.winerror, werr.strerror))

            except Exception as ex:
                logging.error("Notifier: Exception: channel:'{}' message:'{}'".format(self._Name, str(ex)))

            except:
                logging.error("Notifier: Unexpected error: channel:'{}'".format(self._Name))

            if recover:
                cont = self._SetState(__class__._StateRecover)

            if not cont:
                break


    #-------------------------------------------------------
    def __init__(self, name, guid):
        """Startup pipe server"""

        # state variables
        self._State = __class__._StateNone
        self._IoError = winerror.ERROR_SUCCESS
        self._Pipe = win32file.INVALID_HANDLE_VALUE
        self._LastMessage = None
        self._NextMessage = None
        self._Name = name

        try:
            # event for overlapped pipe I/O
            self._Event = win32event.CreateEvent(None, True, False, None)

            # create the pipe used as a transport
            self._Pipe = win32pipe.CreateNamedPipe(
                r"\\.\pipe\nlv-{}".format(guid), # pipeName
                win32pipe.PIPE_ACCESS_OUTBOUND | win32file.FILE_FLAG_OVERLAPPED, # openMode
                win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE, # pipeMode
                1, # nMaxInstances
                self._PipeSize, # nOutBufferSize
                self._PipeSize, # nInBufferSize
                0, # nDefaultTimeOut
                None # sa
           )

            # initiate connection
            self._State = __class__._StateConnect
            self._Run()

        except pywintypes.error as werr:
            logging.error("Notifier: Pipe startup error: channel:'{}' func:'{}' code:'{}' error:'{}'".format(self._Name, werr.funcname, werr.winerror, werr.strerror))

        except:
            logging.error("Notifier: Pipe startup: unexpected error: channel:'{}'".format(self._Name))

    
    #-------------------------------------------------------
    def Notify(self, message):
        """Send the message to the channel."""

        if message == self._LastMessage:
            return

        self._NextMessage = message
        self._Run()


    #-------------------------------------------------------
    def ShutDown(self):
        """Clean shutdown of the channel"""

        # Best efforts pipe shutdown, ignore any errors
        try:
            win32file.CancelIo(self._Pipe)
            win32pipe.DisconnectNamedPipe(self._Pipe)
            self._Pipe.Close()
        except:
            pass

        logging.debug("Notifier: shut down: channel:'{}'".format(self._Name))
