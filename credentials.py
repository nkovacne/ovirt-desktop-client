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
import os
import ConfigParser
from os.path import isfile
from globalconf import conf
from PyQt5.QtWidgets import QProgressBar, QPushButton, QDesktopWidget, QDialog, QLabel, QLineEdit, QGridLayout, QCheckBox, QMessageBox
from PyQt5.QtGui import QImage, QPixmap 
from PyQt5.QtCore import QBasicTimer, Qt
from ovirtsdk.api import API
from ovirtsdk.infrastructure.errors import ConnectionError, RequestError

class CheckCreds(QDialog):
    """
        This class manages the authentication process for oVirt. If credentials are saved, they're
        tried automatically. If they are wrong, the username/password dialog is shown.
    """

    def __init__(self, parent, username, password, remember):
        QDialog.__init__(self, parent)
        self.uname = username
        self.pw = password
        self.remember = remember
        self.setModal(True)
        self.initUI()

    def initUI(self):
        """
            Description: A progress bar, a status message will be shown and a timer() method will
                         be invoked as part of the authentication process.
            Arguments: None
            Returns: Nothing
        """

        self.pbar = QProgressBar(self)
        self.pbar.setGeometry(30, 40, 200, 25)
        
        self.status = QLabel(self)
        self.status.setGeometry(30, 75, 200, 20)

        self.timer = QBasicTimer()
        self.step = 0
        
        self.setGeometry(300, 300, 255, 100)
        self.center()
        self.setWindowTitle(_('loading'))
        self.show()

        self.timer.start(100, self)
    
    def timerEvent(self, e):
        """
            Description: This method will be called periodically as part of the QBasicTimer() object. 
                         Authentication will be handled within this method.
            Arguments: The event. Won't be used, though.
            Returns: Nothing, just exits when progress bar reaches 100%
        """

        global conf

        err = QMessageBox()
        self.status.setText(_('authenticating'))

        if not conf.USERNAME:
            try:
                kvm = API(url=conf.CONFIG['ovirturl'], username=self.uname + '@' + conf.CONFIG['ovirtdomain'], password=self.pw, insecure=True, timeout=int(conf.CONFIG['conntimeout']), filter=True)
                conf.OVIRTCONN = kvm
                conf.USERNAME = self.uname
                conf.PASSWORD = self.pw
                self.status.setText(_('authenticated_and_storing'))
                self.step = 49
            except ConnectionError as e:
                err.critical(self, _('error'), _('ovirt_connection_error') + ': ' + str(e))
                self.status.setText(_('error_while_authenticating'))
                self.step = 100
            except RequestError as e:
                err.critical(self, _('error'), _('ovirt_request_error') + ': ' + str(e))
                self.status.setText(_('error_while_authenticating'))
                self.step = 100
        
        if self.step >= 100:
            # Authenticacion process has concluded
            self.timer.stop()
            self.close()
            return
        elif self.step == 50:
            # Credentials were ok, we check whether we should store them for further uses
            if self.remember:
                self.status.setText(_('storing_credentials'))
                with os.fdopen(os.open(conf.USERCREDSFILE, os.O_WRONLY | os.O_CREAT, 0600), 'w') as handle:
                    handle.write('[credentials]\nusername=%s\npassword=%s' % (self.uname, self.pw))
                    handle.close()
                self.step = 99
            else:
                self.status.setText(_('successfully_authenticated'))
                self.step = 99
            
        self.step = self.step + 1
        self.pbar.setValue(self.step)

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

class Credentials(QDialog):
    """
        This class shows the main credentials Dialog and prompts user for username and
        password. Also a checkbox is shown to store credentials.
    """

    def __init__(self, parent):
        QDialog.__init__(self, parent)
        self.initUI()

    def dismiss(self):
        """
            Description: Dismisses the QDialog box. Called on successful authentication.
            Arguments: None
            Returns: Nothing
        """

        global conf
        if conf.USERNAME:
            self.done(0)

    def check_creds(self):
        """
            Description: Checks whether username or password fields are empty, in which case
                         an error window is shown. Otherwise, try to authenticate vs. oVirt
            Arguments: None
            Returns: Nothing, just dismisses the main window on successful authentication.
        """

        err = QMessageBox()
        uname = self.edit_username.text()
        pw = self.edit_pw.text()

        if not uname or not pw:
            err.critical(self, _('error'), _('no_empty_creds'))
        else:
            cc = CheckCreds(self, uname, pw, self.remembercreds.isChecked())
            cc.finished.connect(self.dismiss)

    def confirm_quit(self):
        """
            Description: Confirm whether to quit or not application. This option must be present
                         in case the user cannot authenticate against oVirt, in which case the
                         main window won't be shown but the application will exit instead.
            Arguments: None
            Returns: Nothing, just quits if user confirms.
        """

        cq = QMessageBox.question(self, _('confirm'), _('confirm_quit'), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if cq == QMessageBox.Yes:
            quit()

    def closeEvent(self, event):
        """
            Description: Deactivation of the red 'x' to close the window. We enforce user to choose
                         whether to authenticate or exit the application.
            Arguments: The event.
            Returns: Nothing
        """

        event.ignore()

    def initUI(self):
        """
            Description: Deactivation of the red 'x' to close the window. We enforce user to choose
                         whether to authenticate or exit the application.
            Arguments: The event.
            Returns: Nothing
        """

        global conf

        self.setFixedSize(400, 150)

        # Keys image
        filename = 'imgs/credentials.png'
        image = QImage(filename)
        imageLabel = QLabel()
        imageLabel.setPixmap(QPixmap.fromImage(image))
        imageLabel.setAlignment(Qt.AlignCenter)

        # Labels for both username and password
        lab_username = QLabel(_('username'))
        lab_username.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lab_pw = QLabel(_('password'))
        lab_pw.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # LineEdits for both username and password
        self.edit_username = QLineEdit()
        self.edit_username.setFixedWidth(150)
        self.edit_pw = QLineEdit()
        self.edit_pw.setEchoMode(QLineEdit.Password)
        self.edit_pw.setFixedWidth(150)

        # QCheckBox for storing user + password
        self.remembercreds = QCheckBox(_('remember_username_and_password'))

        # OK and cancel buttons
        okButton = QPushButton(_("ok"))
        okButton.setMaximumWidth(100)
        okButton.clicked.connect(self.check_creds)
        cancelButton = QPushButton(_("cancel"))
        cancelButton.setMaximumWidth(100)
        cancelButton.clicked.connect(self.confirm_quit)

        # Grid layout with all the elements
        grid = QGridLayout()

        grid.addWidget(imageLabel, 1, 0, 2, 1)               # Keys image

        grid.addWidget(lab_username, 1, 1, 1, 1)             # Username
        grid.addWidget(self.edit_username, 1, 2, 1, 2)

        grid.addWidget(lab_pw, 2, 1, 1, 1)                   # Password
        grid.addWidget(self.edit_pw, 2, 2, 1, 2)

        grid.addWidget(self.remembercreds, 3, 1, 1, 3)       # Remember credentials

        grid.addWidget(okButton, 4, 1)                       # Buttons
        grid.addWidget(cancelButton, 4, 2)
        
        self.setLayout(grid) 

        self.setModal(True)
        self.center()
        self.setWindowTitle(_('credentials'))
        self.show()

        # If credentials file exists, we'll recover username and password fields
        # and try to authenticate with them
        if isfile(conf.USERCREDSFILE):
            config = ConfigParser.ConfigParser()
            config.read(conf.USERCREDSFILE)
            uname = config.get('credentials', 'username')
            pw = config.get('credentials', 'password')
            self.edit_username.setText(uname)
            self.edit_pw.setText(pw)
            self.check_creds()

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
