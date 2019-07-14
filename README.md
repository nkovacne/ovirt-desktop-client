# oVirt Desktop Client

### Description

This project is a simple oVirt-related desktop client. The application will communicate with oVirt via its Python API and provide a list of VMs and VmPools on which the user has usage privileges, allowing two essential operations:

 1. _Manage power_: Users will be able to shutdown and start their machines.
 2. _Connect to the machine_: The application makes use of _virt-viewer_ to connect to the VM. Both VNC and SPICE protocols are supported.

This application is written in *PyQT5*, and has been verified to be working with oVirt version >= 4.0.0. It won't work with 3.6.0 versions of oVirt correctly.

This project is also accessible from https://ovirt-desktop-client.click

**Disclaimer**: This is an **unofficial** oVirt-related project. 

### Installation

As of version 2.0.0 of oVirt Desktop Client, the installation process is much simpler, because Python3 allows using native PyQt5-sip and PyQt libraries. In previous versions this had to be built manually.

Below you'll find the installation steps. You can also find a [Troubleshooting guide](https://github.com/nkovacne/ovirt-desktop-client/wiki/Install-process). If you find a different problem please feel free to report it.

On Debian/Ubuntu environments, make sure to install these packages: 
```
python python-dev python-virtualenv qt5-default libcurl4-openssl-dev libxml2 libxml2-dev libxslt1-dev libssl-dev virt-viewer
```

On RHEL environments, make sure to install these packages:
```
python python-devel python-virtualenv python-pip gcc gcc-c++ qt5-qtbase qt5-qtbase-devel libcurl-devel libxml2 libxml2-devel libxslt-devel openssl-devel virt-viewer
```

Now just clone, install a virtualenv with Python3 as the Python executable and install the requirements for the project.

```
git clone https://github.com/nkovacne/ovirt-desktop-client.git
virtualenv -p python3 --always-copy venv
. venv/bin/activate
cd ovirt-desktop-client
pip install -r requirements.txt
```

### Upgrading from version 1.x to 2.x

In previous versions, SIP and PyQt packages needed to be built manually. Furthermore, it was based on Python 2, whereas version >= 2.0.0 is Python 3 based. To upgrade, the fastest way is to `pull` the 2.0.0 version, destroy the virtualenv and recreate it. Just follow these commands to upgrade.

```
deactivate (in case you're working in the virtualenv)
rm -rf venv
virtualenv -p python3 --always-copy venv
. venv/bin/activate
cd ovirt-desktop-client
git pull
pip install -r requirements.txt
```

### Configuration

To run the application, a file named `settings.conf` must exist in the same directory where the application resides. This file contains 2 sections with a few parameters in each. You can find a `settings.conf.example` file inside the repository so you can base your configuration on it (don't forget to copy/rename it to `settings.conf`).

#### ovirt section

The beggining of this section is marked with the `[ovirt]` line and references some settings that are directly related to the oVirt infrastructure that you mean to connect to. It only has 2 parameters, and both are **mandatory**:

 * **url**: You oVirt infrastructure API URL. If you're using oVirt version 4.0.x or greater, URL should be somewhat like: `https://myovirt.mydomain.com/ovirt-engine/api`.
 * **domain**: The domain under which your users will authenticate. When you create an AAA authenticator (LDAP, Kerberos, ...), a domain name is created to match it. This value goes here, so users will authenticate as `username@domain` (Ex: LDAP, MyCompany, ...). It's the 'Profile' field value when you're logging into the oVirt web-based API.
 
#### app section

The beggining of this section is marked with the `[app]` line and references some settings that are directly related to the oVirt desktop client behavior. All of them are **optional** but have some default values.

* **lang**: Chooses the application language. Available languages are stored under the `lang` folder. If you don't see your language, you can translate it and send a push request so I can merge it into the project. Default: en.
* **connection_timeout**: Establishes the number of seconds to wait after sending a request to your oVirt infrastructure after which the request will be considered timed out. Default: 15
* **preferred_protocol**: Some VMs have more than one graphics protocol enabled (i.e, VNC and SPICE) at a time. These VMs allow choosing which one you prefer to use when opening a console window. In case that the VM only has one protocol enabled, this will be used disregarding this parameter. Possible values: spice, vnc. Default: spice
* **fullscreen**: Enables opening the console window as fullscreen or the default size. Possible values: 1 (full screen), 0 (default size). Default: 0
* **allow_remember**: Defines whether show or not the "Remember credentials" checkbox. Some environments might prefer not enabling it (for example, thin-client fashioned terminals). Possible values: 1 (enable the remembering credentials checkbox), 0 (disable the remembering credentials checkbox). Default: 1
* **autologout**: Time in minutes of idleness after which the session is forcibly closed. If set to 0, the autologout feature is disabled. Only works if there are not any credentials stored (also with allow_remember = 0), which is incompatible with this feature. Default: 0
* **notify_autologout**: The time before *autologout* in minutes before a warning window will be shown to the user alerting them about an imminent forced logout event. Accepting the warning means resetting the idle time. This setting needs to have a lower value than *autologout*. If this setting is set and 'autologout' is not, or if the value of *notify_autologout* is lower than the value in *autologout*, this setting will be set to the default value. A value of 0 means that no warning windows will be shown to the user. _Example_: If *autologout* is 15 and *notify_autologout* is 5, means that 5 minutes before reaching the 15 minutes limit of idleness a warning window will be shown. If the user accepts the warning within the next 5 minutes limit, the idleness count will be reset. Otherwise the enforced logout will be performed. Default: 0
* **remote_viewer_path**: The path to the remote-viewer binary. By default, it's set to a path that is compatible with most systems. However, you can set a customized path here. If set to an invalid path, the app will still try to find the correct binary. Will exit if no suitable binary was found. Default: /usr/bin/remote-viewer

### How to run

Just run the `virtualenv` and the `ovirtclient.py` executable.

```
. venv/bin/activate
cd ovirt-desktop-client
python ovirtclient.py
```

### Current version

Current stable version is 2.0.0. You can find a CHANGELOG file inside your directory to see news.
