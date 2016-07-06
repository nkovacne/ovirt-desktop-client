#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

import gettext
from version import VERSION
from PyQt5.QtWidgets import QPushButton, QDesktopWidget, QDialog, QLabel, QGridLayout
from PyQt5.QtGui import QImage, QPixmap 
from PyQt5.QtCore import Qt

class About(QDialog):
    """
        This class shows additional information about the application
    """

    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        self.initUI()

    def initUI(self):
        """
            Description: Simply shows the dialog
            Arguments: None
            Returns: Nothing
        """

        global conf

        self.resize(450, 150)

        # About image
        filename = 'imgs/about.png'
        image = QImage(filename)
        imageLabel = QLabel()
        imageLabel.setPixmap(QPixmap.fromImage(image))
        imageLabel.setAlignment(Qt.AlignCenter)

        # Labels for info
        lab_appname = QLabel("<font color='#0000FF'>" + _('apptitle') + ' ' + VERSION + "</font>")
        lab_appname.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        lab_desc = QLabel(_('appdesc'))
        lab_desc.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        lab_desc.setWordWrap(True)
        lab_author = QLabel(_('written_by') + ' nKn (<a href=\'http://github.com/nkovacne\'>http://github.com/nkovacne</a>)')
        lab_author.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        lab_unoff = QLabel('<b>' + _('unofficial_project') + '</b>')
        lab_unoff.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        lab_unoff.setWordWrap(True)

        # OK button
        okButton = QPushButton(_("ok"))
        okButton.setMaximumWidth(100)
        okButton.setDefault(True)
        okButton.clicked.connect(self.done)

        # Grid layout with all the elements
        grid = QGridLayout()

        grid.addWidget(imageLabel, 1, 0, 4, 1)               # About image

        grid.addWidget(lab_appname, 1, 1, 1, 2)              # Several QLabels
        grid.addWidget(lab_desc, 2, 1, 1, 2)
        grid.addWidget(lab_author, 3, 1, 1, 2)
        grid.addWidget(lab_unoff, 4, 1, 1, 2)

        grid.addWidget(okButton, 6, 1)                       # Button
        
        self.setLayout(grid) 

        self.setModal(True)
        self.center()
        self.setWindowTitle(_('about'))
        self.show()

    def center(self):
        """
            Description: Just centers the window
            Arguments: None
            Returns: Nothing
        """

        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())
