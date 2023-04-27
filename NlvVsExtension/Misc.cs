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

namespace NLV.VisualStudio
{
    /// <summary>
    /// This class exposes the list of Guids used by the package. This list of
    /// guids must match the set of Guids used inside the VSCT file.
    /// </summary>
    static class GuidsList
    {
        // Now define the list of guids as public static members.
        [System.Diagnostics.CodeAnalysis.SuppressMessage("Microsoft.Performance", "CA1823:AvoidUnusedPrivateFields")]
        public static readonly Guid guidClientPkg = new Guid("{D36AA01F-2FB4-4A38-B527-8411E9CE0226}");
        public static readonly Guid guidClientCmdSet = new Guid("{759C8B4E-B5E9-4167-B55F-3751402C2402}");
    }


    /// <summary>
    /// This class exposes the IDs of the commands implemented by the client package.
    /// This list of IDs must match the set of IDs defined in the BUTTONS section of the
    /// VSCT file.
    /// </summary>
    static class PkgCmdId
    {
        // Define the list a set of public static members.
        public const int cmdidToolWindowShow = 0x2001;
        public const int cmdidLogListClear = 0x2003;
        public const int cmdidLogListPrev = 0x2004;
        public const int cmdidLogListNext = 0x2005;

        public const int cmdidCombo = 0x2006;
        public const int cmdidComboGetList = 0x2007;

        // Define the list of menus (these include toolbars)
        public const int IDM_MyToolbar = 0x0101;
    }
}
