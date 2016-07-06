#!/usr/bin/env python

# This file may be used under the terms of the GNU General Public License
# version 3.0 as published by the Free Software Foundation and appearing in
# the file LICENSE included in the packaging of this file.  Please review the
# following information to ensure the GNU General Public License version 3.0
# requirements will be met: http://www.gnu.org/copyleft/gpl.html.
#
# If you do not wish to use this file under the terms of the GPL version 3.0
# then you may purchase a commercial license.  For more information contact
# info@riverbankcomputing.com.
#
# This file is provided AS IS with NO WARRANTY OF ANY KIND, INCLUDING THE
# WARRANTY OF DESIGN, MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.

from os.path import expanduser

class Configs:
    CONFIGFILE='settings.conf'
    USERCREDSFILE=expanduser('~') + '/.ovirtclient'
    USERNAME=None
    PASSWORD=None
    OVIRTCONN=None
    CONFIG={}
conf = Configs()

IMGDIR = 'imgs/'
UPDATESLEEPINTERVAL = 5
MAXWIDTH = 500
MAXHEIGHT = 600
BACKGROUNDCSS = 'background: black; color: white'
STANDARDCELLCSS = 'background: #1a1a1a; padding: 5px;'
