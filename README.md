# oVirt Desktop Client

### Description

This project is a simple oVirt-related desktop client. The application will communicate with oVirt via its Python API and provide a list of VMs about which the user has usage privileges, allowing two essential operations:

 1. _Manage power_: Users will be able to shutdown and start their machines.
 2. _Connect to the machine_: The application makes use of _virt-viewer_ to connect to the VM. Both VNC and SPICE protocols are supported.

This application is written in *PyQT5*, and has been verified to be working with oVirt 4.0.0 (should work with any version >= 3.5.0).

This project is also accessible from the URL https://ovirt-desktop-client.click

**Disclaimer**: This is an **unofficial** oVirt-related project. 

### Installation

1. On Debian/Ubuntu environments, make sure to install these packages: 
   ```
   python python-dev python-virtualenv qt5-default libcurl4-openssl-dev libxml2 libxml2-dev libxslt1-dev libssl-dev virt-viewer
   ```

   On RHEL environments, make sure to install these packages:
   ```
   python python-devel python-virtualenv python-pip gcc gcc-c++ qt5-qtbase qt5-qtbase-devel libcurl-devel libxml2 libxml2-devel libxslt-devel openssl-devel virt-viewer
   ```

2. Create the project directory and create a *virtualenv* inside:
   ```
   mkdir ovirt-desktop-client
   cd ovirt-desktop-client
   virtualenv --always-copy venv
   . venv/bin/activate
   ```

3. You have to download the SIP and PyQT5 projects and install them manually. Starting with SIP, [download](https://sourceforge.net/projects/pyqt/files/sip/) the *tar.gz* file to your ~/ovirt_client directory, uncompress it and compile it.
   ```
   tar zxvf sip-X.X.X.tar.gz
   cd sip-X.X.X
   python configure.py
   make
   make install
   cd ..
   ```

4. Let's do the same with [PyQT5](https://www.riverbankcomputing.com/software/pyqt/download5).
   ```
   tar zxvf PyQt-gpl-X.X.tar.gz
   cd PyQt-gpl-X.X
   python configure.py
   make
   make install
   cd ..
   ```

5. Clone the oVirt-desktop-client project:
   ```
   git clone https://github.com/nkovacne/ovirt-desktop-client.git
   ```

6. Install the Python requisites with `pip`:
   ```
   pip install -r ovirt-desktop-client/requisites.txt
   ```

7. You're done. Even if you have not configured settings yet, you can try to start the application just to see if it works.
   ```
   python ovirt-desktop-client/ovirtclient.py
   ```
#### Installation troubleshooting

Some environments seem to have their own peculiarities and installing SIP or PyQT5 might not go as smoothly as described above. Here are some known potholes.

##### SIP: Permission denied on make install

This happens when you're working inside a *virtualenv*, probably with an unprivileged user and *make install* will still try to copy files inside `/usr/local/...` instead of your virtualenv. You'll see something like this:

```
make[1]: entering directory « /stck2/stck2.2/ptoniato/python/pip/virtualenv-1.10.1/provaenv/build/SIP/sipgen »
cp -f sip /stck2/stck2.2/ptoniato/python/pip/virtualenv-1.10.1/provaenv/bin/sip
make[1]: leaving directory « /stck2/stck2.2/ptoniato/python/pip/virtualenv-1.10.1/provaenv/build/SIP/sipgen »
make[1]: entering « /stck2/stck2.2/ptoniato/python/pip/virtualenv-1.10.1/provaenv/build/SIP/siplib »
cp -f sip.so /stck2/stck2.2/ptoniato/python/pip/virtualenv-1.10.1/provaenv/lib/python2.7/site-packages/sip.so
strip /stck2/stck2.2/ptoniato/python/pip/virtualenv-1.10.1/provaenv/lib/python2.7/site-packages/sip.so
cp -f /stck2/stck2.2/ptoniato/python/pip/virtualenv-1.10.1/provaenv/build/SIP/siplib/sip.h /usr/local/python/include/python2.7/sip.h
cp: cannot create regular file « /usr/local/python/include/python2.7/sip.h »: Permission denied
make[1]:  [install] Error 1
make[1]: leaving directory « /stck2/stck2.2/ptoniato/python/pip/virtualenv-1.10.1/provaenv/build/SIP/siplib »
make:  [install] Error 2
```

To solve it, run `python configure.py` specifying the include dir (i.e., your virtualenv's include dir where files should actually be installed).

   ```
   python configure.py --incdir=../venv/include/python2.7
   ```

Then, run `make` and `make install` again.

##### PyQT5: Error: Make sure you have a working sip on your PATH or use the --sip argument to explicitly specify a working sip.

This error shows up when the `configure.py` file is unable to find a valid SIP include directory. To solve it, simply force it specifying the `--sip-incdir` option:

   ```
   python configure.py --sip-incdir ../sip-X.X.X/siplib
   ```

### Configuration

To run the application, a file named `settings.conf` must exist in the same directory where the application resides. This file contains 2 sections with a few parameters in each. You can find a `settings.conf.example` file inside the repository so you can base your configuration on it (don't forget to copy/rename it to `settings.conf`).

#### ovirt section

The beggining of this section is marked with the `[ovirt]` line and references some settings that are directly related to the oVirt infrastructure that you mean to connect to. It only has 2 parameters, and both are **mandatory**:

 * **url**: You oVirt infrastructure API URL. If you're using oVirt version 3.6.x, URL should be somewhat like: `https://myovirt.mydomain.com/api`. If you're using oVirt version 4.0.x or greater, URL should be somewhat like: `https://myovirt.mydomain.com/ovirt-engine/api`.
 * **domain**: The domain under which your users will authenticate. When you create an AAA authenticator (LDAP, Kerberos, ...), a domain name is created to match it. This value goes here, so users will authenticate as `username@domain` (Ex: LDAP, MyCompany, ...). It's the 'Profile' field value when you're logging into the oVirt web-based API.
 
#### app section

The beggining of this section is marked with the `[app]` line and references some settings that are directly related to the oVirt desktop client behavior. All of them are **optional** but have some default values.

* **lang**: Chooses the application language. Available languages are stored under the `lang` folder. If you don't see your language, you can translate it and send a push request so I can merge it into the project. Default: en.
* **connection_timeout**: Establishes the number of seconds to wait after sending a request to your oVirt infrastructure after which the request will be considered timed out. Default: 15
* **preferred_protocol**: Some VMs have more than one graphics protocols enabled (i.e, VNC and SPICE) at a time. These VMs allow choosing which one you prefer to use when opening a console window. In case that the VM only has one protocol enabled, this will be used disregarding this parameter. Possible values: spice, vnc. Default: spice
* **fullscreen**: Enables opening the console window as fullscreen or the default size. Possible values: 1 (full screen), 0 (default size). Default: 0
* **allow_remember**: Defines whether show or not the "Remember credentials" checkbox. Some environments might prefer not enabling it (for example, thin-client fashioned terminals). Possible values: 1 (enable the remembering credentials checkbox), 0 (disable the remembering credentials checkbox). Default: 1
* **autologout**: Time in minutes of idleness after which the session is forcibly closed. If set to 0, the autologout feature is disabled. Only works if there are not any credentials stored (also with allow_remember = 0), which is incompatible with this feature. Default: 0
* **notify_autologout**: The time before *autologout* in minutes before a warning window will be shown to the user alerting them about an imminent forced logout event. Accepting the warning means resetting the idle time. This setting needs to have a lower value than *autologout*. If this setting is set and 'autologout' is not, or if the value of *notify_autologout* is lower than the value in *autologout*, this setting will be set to the default value. A value of 0 means that no warning windows will be shown to the user. _Example_: If *autologout* is 15 and *notify_autologout* is 5, means that 5 minutes before reaching the 15 minutes limit of idleness a warning window will be shown. If the user accepts the warning within the next 5 minutes limit, the idleness count will be reset. Otherwise the enforced logout will be performed. Default: 0

## Current version

Current stable version is 1.0.4. You can find a CHANGELOG file inside your directory to see news.
