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

import sys
import gettext
import ConfigParser
import urllib2
import threading
from time import sleep, time
from base64 import encodestring
from xml.etree import cElementTree as ET
from random import randint
from os import remove
from subprocess import Popen
from os.path import isfile
from ssl import _create_unverified_context
from globalconf import *
from credentials import Credentials
from about import About
from version import VERSION
from PyQt5.QtWidgets import QApplication, QDesktopWidget, QMessageBox, QGridLayout, QLabel, QWidget, QProgressBar, QScrollArea, QVBoxLayout, QAction, QToolBar
from PyQt5.QtGui import QImage, QPixmap, QIcon
from PyQt5.QtCore import Qt, QObjectCleanupHandler, pyqtSignal
from ovirtsdk.infrastructure.errors import ConnectionError, RequestError

class VmData:
    """
        A simple class whose objects will store (VMid, VMname, VMstatus, VMtype) tuples
    """

    vmid = None
    vmname = None
    vmstatus = None
    vmtype = None

class OvirtClient(QWidget):
    """
        This class will handle the main window where all user's VMs will be listed.
        This will be rendered only if authentication was successfull since it doesn't
        make sense otherwise. Additionally, a Thread will be started checking VM status
        changes and update the board accordingly.
    """

    stopThread = False                              # Sentinel for stopping the Thread execution
    autologoutWarn = False                          # Has the user been warned about autologout yet?
    openviewer_vms = []                             # Initiated VMs in terms of the viewer
    updatesignal = pyqtSignal(int, str)             # Signal to update the status icons on status changes
    reloadsignal = pyqtSignal()                     # Signal to reload the main widget
    warnlogoutsignal = pyqtSignal()                 # Signal to warn the user about an imminent autologout
    logoutsignal = pyqtSignal(bool)                 # Signal to logout the current user and require credentials again
    lastclick = int(time())                         # Timestamp of the last click. If a timeout policy is defined and
                                                    # the time exceeds this value, an autologout will be performed.

    def __init__(self):
        QWidget.__init__(self)
        self.initUI()

    def vm_based_resize(self, vmnum):
        """
            Description: Depending on the number of VMs which the user has permissions on,
                         we need to resize the main window accordingly in height.The fewer
                         they are, the smaller the window will be. If MAXHEIGHT is reached,
                         a scrollbar will also be shown (that's processed in a different
                         place, though)
            Parameters: The number of VMs.
            Returns: The actual window height.
        """

        global MAXHEIGHT

        if not vmnum:
            # If user has no machines, resize window to the minimum
            winheight = 150
            no_machines = QLabel(_('no_vms'))
            no_machines.setWordWrap(True)
            no_machines.setAlignment(Qt.AlignCenter)
            self.grid.addWidget(no_machines, 0, 0)
            self.setMinimumHeight(winheight)
        else:
            # User has at least one VM
            if vmnum > 5:
                # More than 5 means resizing the window to the maximum
                winheight = MAXHEIGHT
                self.setFixedHeight(winheight)
            else:
                # Otherwise, resize depending on the number of VMs
                winheight = vmnum * 100 + 50
                self.setFixedHeight(winheight)
        return winheight

    def get_os_icon(self, os):
        """
            Description: Depending on the VM's OS, this method returns
                         which icon should be used to illustrate it.
            Arguments: oVirt-style string representing the VM's OS
            Returns: The file name under IMGDIR that should be shown.
        """

        if 'ubuntu' in os:
            return 'ubuntu'
        elif 'rhel' in os:
            return 'redhat'
        elif 'centos' in os:
            return 'centos'
        elif 'debian' in os:
            return 'debian'
        elif 'linux' in os:
            return 'linux'
        elif 'win' in os:
            return 'windows'
        return 'unknown'

    def generate_toolbar(self):
        """
            Description: There will be a toolbar in the main widget with some buttons,
                         this method will render them.
            Arguments: None
            Returns: Nothing
        """

        global IMGDIR, conf

        self.toolBar = QToolBar(self)

        refreshAction = QAction(QIcon(IMGDIR + 'refresh.png'), _('refresh'), self)
        refreshAction.setShortcut('Ctrl+R')
        refreshAction.triggered.connect(self.refresh_grid)
        self.toolBar.addAction(refreshAction)
        
        self.forgetCredsAction = QAction(QIcon(IMGDIR + 'forget.png'), _('forget_credentials'), self)
        self.forgetCredsAction.setShortcut('Ctrl+F')
        self.forgetCredsAction.triggered.connect(self.forget_creds)
        if not isfile(conf.USERCREDSFILE):
            self.forgetCredsAction.setDisabled(True)
        self.toolBar.addAction(self.forgetCredsAction)

        aboutAction = QAction(QIcon(IMGDIR + 'about.png'), _('about'), self)
        aboutAction.setShortcut('Ctrl+I')
        aboutAction.triggered.connect(self.about)
        self.toolBar.addAction(aboutAction)

        exitAction = QAction(QIcon(IMGDIR + 'exit.png'), _('exit'), self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.triggered.connect(self.quit_button)
        self.toolBar.addAction(exitAction)

        self.grid.addWidget(self.toolBar, 0, 3, Qt.AlignRight)

    def make_button(self, filename, tooltip, alignment=Qt.AlignCenter):
        """
            Description: Creates a QLabel which will contain an image and will
                         simulate a button. No associated text will be shown.
            Arguments: 1. filename: The filename of the icon/image to show 
                       2. tooltip: Some text to show as a tooltip to the image
                       3. alignment: Alignment of the button (center by default)
            Returns: The created QLabel button
        """

        global STANDARDCELLCSS, IMGDIR

        filepath = '%s%s%s' % (IMGDIR, filename, '.png')
        icon = QImage(filepath)
        image = QLabel()
        image.setToolTip('<span style="color:#B9B900">%s</span>' % (tooltip))
        image.setStyleSheet(STANDARDCELLCSS)
        image.setPixmap(QPixmap.fromImage(icon))
        image.setAlignment(alignment)

        return image

    def compare_vms(self, vm1, vm2):
        """
            Description: VM list will be sorted by names. This method is the comparison
                         method for two VMs. We just sort them alphabetically.
            Arguments: Two VMs (oVirt VM objects)
            Returns: -1, 0 or 1 depending on the name-based sorting
        """

        if vm1.get_name().lower() < vm2.get_name().lower():
            return -1
        if vm1.get_name().lower() == vm2.get_name().lower():
            return 0
        return 1

    def current_vm_status(self, vmstatus):
        """
            Description: Single translation between oVirt-like status to human-readable status
            Arguments: oVirt-like status
            Returns: Human-readable status
        """

        if vmstatus == 'up':
            hrstatus = _('up')
        elif vmstatus == 'down':
            hrstatus = _('down')
        elif vmstatus == 'powering_down':
            hrstatus = _('powering_down')
        elif vmstatus == 'wait_for_launch':
            hrstatus = _('wait_for_launch')
        elif vmstatus == 'powering_up':
            hrstatus = _('powering_up')
        else:
            hrstatus = 'unknown'
        return hrstatus

    def toggle_vm_action(self, vmstatus):
        """
            Description: Returns the available action for the current VM's status. If machine is up,
                         available action is turn it off and viceversa.
            Arguments: Current vm status
            Returns: Toggle action for the current status.
        """

        if vmstatus == 'up':
            vmaction = _('shut_down')
        if vmstatus == 'down':
            vmaction = _('power_on')
        return vmaction

    def toggle_action_text(self, vmstatus):
        """
            Description: One of the columns shows the current VM's status. This method returns
                         the toggle tooltip text so the user know what will happen if they click
                         on the status icon.
            Arguments: Current vm status
            Returns: The tooltip's informative text.
        """

        rettxt = '%s <b>%s</b>.' % (_('current_vm_status'), self.current_vm_status(vmstatus))

        if vmstatus == 'up':
            rettxt += ' %s %s' % (_('click_to_action'), _('shut_down'))
        if vmstatus == 'down':
            rettxt += ' %s %s' % (_('click_to_action'), _('power_on'))

        return rettxt

    def change_status(self, rowid):
        """
            Description: If the user clicks on the column which determines VM's status, we'll allow them
                         to change VM's status. This method shows a confirmation dialog and if accepted,
                         it will be notified to oVirt.
            Arguments: The row id that has been clicked. This relationship is stored using the VmData class.
            Returns: Nothing
        """

        global conf

        self.lastclick = int(time())         # Last click timestamp update

        curvmstatus = self.vmdata[rowid].vmstatus
        if curvmstatus != 'up' and curvmstatus != 'down':
            QMessageBox.warning(None, _('apptitle') + ': ' + _('warning'), _('vm_in_unchangeable_status'))
            return

        reply = QMessageBox.question(None, _('apptitle') + ': ' + _('confirm'), '%s <b>%s</b>. %s: <b>%s</b>.' % (_('current_vm_status'), self.current_vm_status(curvmstatus), _('confirm_vm_status_change'), self.toggle_vm_action(curvmstatus)), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            try:
                vm = conf.OVIRTCONN.vms.get(id=self.vmdata[rowid].vmid)
            except ConnectionError:
                QMessageBox.critical(None, _('apptitle') + ': ' + _('error'), _('unexpected_connection_drop'))
                quit()

            if curvmstatus == 'up':
                try:
                    vm.shutdown()
                    QMessageBox.information(None, _('apptitle') + ': ' + _('success'), _('shutting_down_vm'))
                except RequestError:
                    QMessageBox.warning(None, _('apptitle') + ': ' + _('warning'), _('vm_in_unchangeable_status'))
            if curvmstatus == 'down':
                try:
                    vm.start()
                    QMessageBox.information(None, _('apptitle') + ': ' + _('success'), _('powering_up_vm'))
                except RequestError:
                    QMessageBox.warning(None, _('apptitle') + ': ' + _('warning'), _('vm_in_unchangeable_status'))

    def get_viewer_ticket(self, vmid):
        """
            Description: Connecting to the machine involves two steps, the first one is obtaining a 'ticket' string
                         for the connection request. This is done making a request to the oVirt API and then parsing
                         the resulting XML document to get the ticket hash. Also, the request may return more than
                         one ticket: One for SPICE and another for VNC. In this case, we'll return the one that
                         the user defined in the settings file (SPICE as default).
            Arguments: The VM UUID in oVirt-format
            Returns: The ticket hash string
        """

        global conf

        req = urllib2.Request('%s/%s/%s/%s' % (conf.CONFIG['ovirturl'], 'vms', vmid, 'graphicsconsoles'))
        base64str = encodestring('%s:%s' % (conf.USERNAME + '@' + conf.CONFIG['ovirtdomain'], conf.PASSWORD)).replace('\n', '')
        req.add_header('Authorization', 'Basic ' + base64str)
        req.add_header('filter', 'true')

        context = _create_unverified_context()
        tickethash = urllib2.urlopen(req, context=context).read()
        xmlcontent = ET.fromstring(tickethash)

        ticket = None
        for data in xmlcontent.findall('graphics_console'):
            proto = data.findall('protocol')[0]

            if proto.text.lower() == conf.CONFIG['prefproto'].lower():
                return data.get('id')
            else:
                ticket = data.get('id')

        return ticket

    def store_vv_file(self, vmid, ticket):
        """
            Description: Connecting to the machine involves two steps, the second one is obtaining a 'vv' file with the
                         connection parameters, which we can later pipe to virt-viewer and the connection will be opened.
            Arguments: 1. vmid: The VM UUID in oVirt-format.
                       2. ticket: The ticket obtained in the first step (method get_viewer_ticket)
            Returns: The temporary filename with all the parameters to connect to the machine (piped to virt-viewer)
        """

        global conf

        if not ticket:
            return False

        req = urllib2.Request('%s/%s/%s/%s/%s' % (conf.CONFIG['ovirturl'], 'vms', vmid, 'graphicsconsoles', ticket))
        base64str = encodestring('%s:%s' % (conf.USERNAME + '@' + conf.CONFIG['ovirtdomain'], conf.PASSWORD)).replace('\n', '')
        req.add_header('Authorization', 'Basic ' + base64str)
        req.add_header('Content-Type', 'application/xml')
        req.add_header('Accept', 'application/x-virt-viewer')
        req.add_header('filter', 'true')

        context = _create_unverified_context()
        contents = urllib2.urlopen(req, context=context).read()
        if conf.CONFIG['fullscreen'] == '1':
           contents = contents.replace('fullscreen=0', 'fullscreen=1')
        filename = '/tmp/viewer-' + str(randint(10000, 99999))
        f = open(filename, 'w')
        f.write(contents)
        f.close()

        return filename

    def viewer_exit(self, vmname):
        self.openviewer_vms.remove(vmname)         # Remove the VM from the list of opened viewers
        self.reloadsignal.emit()                   # Enforce a reload signal to update the status icon ASAP

    def create_viewer_thread(self, vmname, filename):
        def runInThread(vmname, onExit, popenArgs):
            viewer = Popen(popenArgs)
            viewer.wait()
            onExit(vmname)
            return

        thread = threading.Thread(target=runInThread, args=(vmname, self.viewer_exit, ['/usr/bin/remote-viewer', '-t', vmname, '-f', '--', 'file://%s' % (filename)]))
        thread.start()

        # Returns immediately after the thread starts
        return thread

    def connect2machine(self, vmid, vmname):
        """
            Description: Connecting to the machine involves two steps, this method does both and
                         makes sure everything is ok to call virt-viewer afterwards.
            Arguments: 1. vmid: The VM UUID in oVirt-format.
                       2. vmname: Just for displaying purposes, the VM name
            Returns: Nothing. Opens the view-viewer display.
        """

        viewer_ticket = self.get_viewer_ticket(vmid)
        filename = self.store_vv_file(vmid, viewer_ticket)

        if filename:
            self.create_viewer_thread(vmname, filename)
        else:
            QMessageBox.critical(None, _('apptitle') + ': ' + _('error'), _('no_viewer_file'))

    def connect(self, rowid):
        """
            Description: Whenever the user clicks on the 'connect' row, this method will make
                         sure the VM status is up and only then will call the connect2machine method.
            Arguments: The row id that has been clicked. This relationship is stored using the VmData class.
            Returns: Nothing
        """

        self.lastclick = int(time())         # Last click timestamp update

        vmid = self.vmdata[rowid].vmid
        vmname = self.vmdata[rowid].vmname
        vmstatus = self.vmdata[rowid].vmstatus

        if vmstatus != 'up':
            QMessageBox.warning(None, _('apptitle') + ': ' + _('warning'), _('cannot_connect_if_vm_not_up'))
            return

        if vmname in self.openviewer_vms:
            QMessageBox.critical(None, _('apptitle') + ': ' + _('error'), _('cannot_open_more_viewer_sessions'))
            return

        self.openviewer_vms.append(vmname)
        self.refresh_grid()                  # Enforce a dashboard reload to make the icon refresh

        self.connect2machine(vmid, vmname)
    
    def acquire_vm_from_vmpool(self, rowid):
        """
            Description: A machine will be acquired by a user if they click on the icon of a VmPool
            Arguments: The row id that has been clicked. This relationship is stored using the VmData class.
            Returns: Nothing
        """
        
        self.lastclick = int(time())         # Last click timestamp update

        vmtype = self.vmdata[rowid].vmtype

        if vmtype == 'vmpool':
            try:
                QMessageBox.information(None, _('apptitle') + ': ' + _('info'), _('acquiring_vm_from_pool'))
                vmp = conf.OVIRTCONN.vmpools.get(id=self.vmdata[rowid].vmid)
                vmp.allocatevm()
                self.refresh_grid()
            except ConnectionError:
                QMessageBox.critical(None, _('apptitle') + ': ' + _('error'), _('unexpected_connection_drop'))
                quit()
            except RequestError:
                QMessageBox.critical(None, _('apptitle') + ': ' + _('error'), _('cannot_attach_vm_to_user'))
        else:
            QMessageBox.warning(None, _('apptitle') + ': ' + _('warning'), _('object_is_not_a_vmpool'))

    def refresh_grid(self):
        """
            Description: Invoked when the user clicks on the 'Refresh' button in the toolbar. Reloads the board.
            Arguments: None
            Returns: Nothing
        """
        
        self.lastclick = int(time())         # Last click timestamp update
        self.load_vms()

    def about(self):
        """
            Description: Invoked when the user clicks on the 'About' button in the toolbar.
            Arguments: None
            Returns: Nothing
        """
        
        self.lastclick = int(time())         # Last click timestamp update
        About()
    
    def forget_creds(self):
        """
            Description: Invoked when the user clicks on the 'Forget credentials' button in the toolbar.
            Arguments: None
            Returns: Nothing
        """

        global conf
        
        self.lastclick = int(time())         # Last click timestamp update

        reply = QMessageBox.question(None, _('apptitle') + ': ' + _('confirm'), _('confirm_forget_creds'), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            remove(conf.USERCREDSFILE)
            self.forgetCredsAction.setDisabled(True)
            QMessageBox.information(None, _('apptitle') + ': ' + _('success'), _('creds_forgotten'))

    def list_vmpools(self, row, delta, step, vmpools):
        """
            Description: Creates one row per VmPool that the user has access to.
            Arguments: 1. The index of the first row to loop over.
                       2. Delta step to sum to the progress bar.
                       3. The current step of the progress bar
                       4. The oVirt list of VmPools.
            Returns: The final step of the progress bar
        """

        # For cleanness reasons, we'll firstly show available VmPools
        for vm in vmpools:
            vmname = vm.get_name()

            # OS icon
            ostype = 'vmpool'
            imageOsicon = self.make_button(ostype, '<b>' + _('vmpool') + '</b>')

            # Machine name
            gridvmname = QLabel(vmname)
            gridvmname.setStyleSheet(STANDARDCELLCSS)
            gridvmname.setAlignment(Qt.AlignCenter)

            # Acquire VM button
            connect = self.make_button('grab', _('grab_vm_vmpool'));
            connect.mousePressEvent = lambda x, r=row: self.acquire_vm_from_vmpool(r)

            # Fill row with known info
            self.grid.addWidget(imageOsicon, row, 0)
            self.grid.addWidget(gridvmname, row, 1)
            self.grid.addWidget(connect, row, 2)

            # Store the correspondence between row number <-> VMPool data
            vmd = VmData()
            vmd.vmid = vm.get_id()
            vmd.vmname = vm.get_name()
            vmd.vmstatus = None
            vmd.vmtype = 'vmpool'
            self.vmdata[row] = vmd

            row += 1

            step += delta
            self.pbar.setValue(step)

        return step

    def list_vms(self, row, delta, step, vms):
        """
            Description: Creates one row per VM that the user has access to.
            Arguments: 1. The index of the first row to loop over.
                       2. Delta step to sum to the progress bar.
                       3. The current step of the progress bar
                       4. The oVirt list of VMs.
            Returns: Nothing
        """
        # Now we'll show up the VMs
        for vm in vms:
            vmname = vm.get_name()
            vmstatus = vm.get_status().get_state() 

            # OS icon
            ostype = self.get_os_icon(vm.get_os().get_type().lower())
            imageOsicon = self.make_button(ostype, '<b>%s</b> OS' % (ostype.capitalize()))

            # Machine name
            gridvmname = QLabel(vmname)
            gridvmname.setStyleSheet(STANDARDCELLCSS)
            gridvmname.setAlignment(Qt.AlignCenter)

            # Connect button. Depending on whether it has already been hit, a different icon
            # will be shown and the behavior will also be different.
            if vmname not in self.openviewer_vms:
                connect = self.make_button('connect', _('connect'));
                connect.mousePressEvent = lambda x, r=row: self.connect(r)
            else:
                connect = self.make_button('viewer', _('viewer_already_opened'));

            # Status icon
            curaction = self.current_vm_status(vmstatus)
            imageSticon = self.make_button(vmstatus, self.toggle_action_text(vmstatus))
            imageSticon.mousePressEvent = lambda x, r=row: self.change_status(r)

            # Fill row with known info
            self.grid.addWidget(imageOsicon, row, 0)
            self.grid.addWidget(gridvmname, row, 1)
            self.grid.addWidget(imageSticon, row, 2)
            self.grid.addWidget(connect, row, 3)

            # Store the correspondence between row number <-> VM data
            vmd = VmData()
            vmd.vmid = vm.get_id()
            vmd.vmname = vm.get_name()
            vmd.vmstatus = vmstatus
            vmd.vmtype = 'vm'
            self.vmdata[row] = vmd

            row += 1

            step += delta
            self.pbar.setValue(step)

    def load_vms(self):
        """
            Description: Main core VM loader method. Will connect to oVirt, get the VM list and render them.
            Arguments: None
            Returns: Nothing
        """

        global conf, MAXHEIGHT, BACKGROUNDCSS, STANDARDCELLCSS


        QObjectCleanupHandler().add(self.layout())
        if not conf.USERNAME:
            quit()

        # Used to store row <-> VM correspondence
        self.vmdata = {}

        step = 0

        self.pbarlayout = QGridLayout(self)
        self.pbar = QProgressBar(self)
        self.grid = QGridLayout()
        self.grid.setHorizontalSpacing(0)

        # Initially, set the layout to the progress bar
        self.pbar.setGeometry(250, 250, 200, 100)
        self.pbar.setValue(0)
        self.pbarlayout.addWidget(self.pbar, 0, 0)
        self.setLayout(self.pbarlayout)

        self.setStyleSheet(BACKGROUNDCSS)

        try:
            # Try getting the VM list from oVirt
            vms = sorted(conf.OVIRTCONN.vms.list(), cmp=self.compare_vms)
            vmpools = sorted(conf.OVIRTCONN.vmpools.list(), cmp=self.compare_vms)
        except ConnectionError:
            QMessageBox.critical(None, _('apptitle') + ': ' + _('error'), _('unexpected_connection_drop'))
            quit()

        # Set the main widget height based on the number of VMs 
        winheight = self.vm_based_resize(len(vms) + len(vmpools))
        delta = int(100 / (len(vms) + len(vmpools)))

        if vmpools:
            step = self.list_vmpools(1, delta, step, vmpools)
        if vms:
            self.list_vms(len(vmpools) + 1, delta, step, vms)
            
        # Once loading has concluded, progress bar is dismissed and the layout set to the QGridLayout
        self.pbar.hide()
        QObjectCleanupHandler().add(self.layout())

        # First row is special: Number of VMs + Toolbar
        total_machines = QLabel(_('total_machines') + ': <font color="#AA8738">' + str(len(vms)) + '</font>, ' + _('total_vmpools') + ': <font color="#AA8738">' + str(len(vmpools)) + '</font>', self)
        self.grid.addWidget(total_machines, 0, 0, 1, 3, Qt.AlignCenter)
        self.generate_toolbar()

        # We wrap the main widget inside another widget with a vertical scrollbar
        wrapper = QWidget()
        wrapper.setLayout(self.grid)
        scroll = QScrollArea()
        scroll.setWidget(wrapper)
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(winheight)
        layout = QVBoxLayout()
        layout.addWidget(scroll)

        layout.setContentsMargins(0, 0, 0, 20)
        self.setLayout(layout) 

    def update_status_icon(self, i, newstatus):
        """
            Description: Invoked when the background thread emits the signal announcing a status
                         change, so the corresponding VM status icon should be updated.
            Arguments: i: Row that has changed their status. The VM can be matched with VmData().
                       newstatus: The new status for the VM.
            Returns: Nothing
        """

        imageSticon = self.make_button(newstatus, self.toggle_action_text(newstatus))
        imageSticon.mousePressEvent = lambda x, r=i: self.change_status(r)
        self.grid.addWidget(imageSticon, i, 2)

    def logout_warn(self):
        """
            Description: Called if the warn_autologout setting has been set in the config. It
                         will warn user to reset their idle, otherwise an enforced logout will
                         be performed by calling the logout() method.
            Arguments: None
            Returns: Nothing
        """

        self.autologoutwarnwin = QMessageBox(None)
        self.autologoutwarnwin.setIcon(QMessageBox.Warning)

        self.autologoutwarnwin.setText(_('auto_logout_warn'))
        self.autologoutwarnwin.setWindowTitle(_('auto_logout_warn_title'))
        self.autologoutwarnwin.setStandardButtons(QMessageBox.Ok)
        self.autologoutwarnwin.buttonClicked.connect(self.autologoutwarn_accepted)
        self.autologoutwarnwin.exec_()

    def logout(self, reconnect=False):
        """
            Description: Invoked when the autologout parameter is set in the config and the
                         idle time is overreached. This should require authentication again.
            Arguments: None
            Returns: Nothing
        """

        if conf.OVIRTCONN:
            try:
                conf.OVIRTCONN.disconnect()
            except ConnectionError:
                pass

        self.stopThread = True
        conf.USERNAME = None
        self.autologoutWarn = False

        # Hide the layout so next user doesn't see the previous content
        self.hide()

        try:
            self.autologoutwarnwin.accept()
        except AttributeError:
            # Usually when the notify_autologout setting has not been set
            pass

        # This will be called upon autologout events
        if reconnect:
            creds = Credentials(None)
            creds.finished.connect(self.start_vmpane)
            creds.exec_()

    def autologoutwarn_accepted(self):
        """
            Description: Callback issued when the user accepts the message box warning
                         about an imminent autologout event.
            Arguments: None
            Returns: Nothing
        """
        self.lastclick = int(time())
        self.autologoutWarn = False   # This will make the warning be shown next times as well

    def refresh_statuses(self):
        """
            Description: Background thread that will look for VM status changes and
                         send a signal to the main thread so the corresponding icons
                         are updated. Also, if there's a change in the number of VMs
                         that the user controls, the main Widgets will be reloaded.
                         It'll also check the autologout setting & act accordingly.
            Arguments: None
            Returns: Nothing ("infinite" loop)
        """

        global UPDATESLEEPINTERVAL

        autologout = False
        while 1 and not self.stopThread:
            if conf.OVIRTCONN:
                try:
                    ovirt_num_machines = len(conf.OVIRTCONN.vms.list())
                except ConnectionError:
                    sys.exit('[ERROR] ' + _('unexpected_connection_drop'))

                if ovirt_num_machines != len(self.vmdata):
                     # If the number of VMs has changed, we should reload the main widget
                     self.reloadsignal.emit()
                else:
                    for i in self.vmdata:
                        vmid = self.vmdata[i].vmid
                        vmstatus = self.vmdata[i].vmstatus
                        try:
                            ovirtvm = conf.OVIRTCONN.vms.get(id=vmid)
                        except ConnectionError:
                            sys.exit('[ERROR] ' + _('unexpected_connection_drop'))

                        if ovirtvm:
                            curstatus = ovirtvm.get_status().get_state()
                            if vmstatus != curstatus:
                                # If there has been a status change, emit the signal to update icons
                                self.vmdata[i].vmstatus = curstatus
                                self.updatesignal.emit(i, curstatus)

                # If the autologout warning has not been shown yet and it's configured, we do so
                if conf.CONFIG['autologout'] != 0 and conf.CONFIG['notify_autologout'] != 0 and not self.autologoutWarn and \
                   (int(time() - self.lastclick) >= (conf.CONFIG['autologout'] - conf.CONFIG['notify_autologout']) * 60):
                       self.autologoutWarn = True
                       self.warnlogoutsignal.emit()

                # If there's no credentials file and autologout is set, we check for the last
                # click and if surpassed, a logout will be performed.
                if conf.CONFIG['autologout'] != 0 and not isfile(conf.USERCREDSFILE):
                    if (int(time()) - self.lastclick) >= (conf.CONFIG['autologout'] * 60):
                        self.stopThread = True
                        autologout = True

                sleep(UPDATESLEEPINTERVAL)
            else:
                return

        if autologout:
            self.logoutsignal.emit(True)

    def restart_thread(self):
        """
            Description: Simply starts or restarts the background thread
            Arguments: None
            Returns: Nothing
        """

        self.stopThread = False
        self.lastclick = int(time())
        self.thread = threading.Thread(target=self.refresh_statuses, args=())
        self.thread.daemon = True                            # Daemonize thread
        self.thread.start()

    def start_vmpane(self):
        """
            Description: This method will be called when the Credentials dialog is closed.
                         This should happen on successful authentication. We should then
                         load the main widget and fill it with the VMs that the user has
                         permissions on. Additionally, a background thread will be started
                         to check VM status changed so the main widget is updated should
                         this happen.
            Arguments: None
            Returns: Nothing
        """

        self.show()

        self.load_vms()
        self.center()

        self.restart_thread()

    def confirm_quit(self):
        """
            Description: Asks for confirmation from the user's side to close the app.
            Arguments: None
            Returns: True if the user wants to close the app, False otherwise.
        """

        global conf

        reply = QMessageBox.question(None, _('apptitle') + ': ' + _('confirm'), _('confirm_quit'), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            self.logout(reconnect=False)
            return True
        else:
            return False

    def quit_button(self):
        """
            Description: Triggered when the Exit button in the Toolbar is hit. Confirmation will
                         be required.
            Arguments: None
            Returns: Nothing, exits if user confirms.
        """

        self.lastclick = int(time())         # Last click timestamp update

        if self.confirm_quit():
            quit()

    def closeEvent(self, event):
        """
            Description: The red 'x'. If the user hits it, we'll ask for confirmation.
            Arguments: None
            Returns: Nothing, exits if users confirms.
        """

        if self.confirm_quit():
            event.accept()
        else:
            event.ignore()

    def initUI(self):
        """
            Description: Sets the size of the widget, the window title, centers
                         the window, connects signals to methods and opens the
                         Credentials dialog if needed.
            Arguments: None
            Returns: Nothing.
        """

        global conf, MAXWIDTH, MAXHEIGHT, IMGDIR, VERSION

        self.setFixedSize(MAXWIDTH, MAXHEIGHT)
        self.center()

        self.setWindowTitle(_('apptitle') + ' ' + VERSION)
        self.setWindowIcon(QIcon(IMGDIR + 'appicon.png'))
        self.show()

        self.updatesignal.connect(self.update_status_icon)
        self.logoutsignal.connect(self.logout)
        self.warnlogoutsignal.connect(self.logout_warn)
        self.reloadsignal.connect(self.load_vms)

        if not conf.USERNAME:
            creds = Credentials(self)
            creds.finished.connect(self.start_vmpane)
            creds.exec_()

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

def checkConfig():
    """
        Description: Loads configuration from config file. Also checks for syntax.
        Arguments: None
        Returns: The gettext object (lang)
    """

    global conf

    if not isfile(conf.CONFIGFILE):
        sys.exit("[ERROR] Configuration file (%s) does not exist" % (conf.CONFIGFILE))

    config = ConfigParser.ConfigParser()
    config.read(conf.CONFIGFILE)

    try:
        ovirturl = config.get('ovirt', 'url')
    except ConfigParser.NoOptionError:
        sys.exit("[ERROR] Configuration file (%s) is missing a missing parameter: Section: ovirt, parameter: url. Check config." % (conf.CONFIGFILE))

    try:
        ovirtdomain = config.get('ovirt', 'domain')
    except ConfigParser.NoOptionError:
        sys.exit("[ERROR] Configuration file (%s) is missing a missing parameter: Section: ovirt, parameter: domain. Check config." % (conf.CONFIGFILE))

    try:
        applang = config.get('app', 'lang')
    except ConfigParser.NoOptionError:
        applang = 'en'

    try:
        conntimeout = config.get('app', 'connection_timeout')
    except ConfigParser.NoOptionError:
        conntimeout = 15

    try:
        prefproto = config.get('app', 'preferred_protocol')
        if not prefproto:
            prefproto = 'spice'
        elif prefproto.lower() != 'vnc' and prefproto.lower() != 'spice':
            prefproto = 'spice'
    except ConfigParser.NoOptionError:
        prefproto = 'spice'

    try:
        fullscreen = config.get('app', 'fullscreen')
        if fullscreen != '0' and fullscreen != '1':
            fullscreen = '0'
    except ConfigParser.NoOptionError:
        fullscreen = '0'

    try:
        allow_remember = config.get('app', 'allow_remember')
        if allow_remember != '0' and allow_remember != '1':
            allow_remember = '0'
    except ConfigParser.NoOptionError:
        allow_remember = '1'

    try:
        autologout = int(config.get('app', 'autologout'))
    except ValueError:
        autologout = 0
    except ConfigParser.NoOptionError:
        autologout = 0

    try:
        notify_autologout = int(config.get('app', 'notify_autologout'))
        if (autologout and notify_autologout >= autologout) or (not autologout):
            notify_autologout = 0
    except ValueError:
        notify_autologout = 0
    except ConfigParser.NoOptionError:
        notify_autologout = 0

    # Config OK, storing values
    conf.CONFIG['ovirturl'] = ovirturl
    conf.CONFIG['ovirtdomain'] = ovirtdomain
    conf.CONFIG['applang'] = applang
    conf.CONFIG['conntimeout'] = conntimeout
    conf.CONFIG['prefproto'] = prefproto
    conf.CONFIG['fullscreen'] = fullscreen
    conf.CONFIG['allow_remember'] = allow_remember
    conf.CONFIG['autologout'] = autologout
    conf.CONFIG['notify_autologout'] = notify_autologout

    lang = gettext.translation(conf.CONFIG['applang'], localedir='lang', languages=[conf.CONFIG['applang']])
    return lang

if __name__ == '__main__':
    lang = checkConfig()
    lang.install()

    app = QApplication(sys.argv)
    OvirtClient()
    sys.exit(app.exec_())
