#!/usr/bin/env python

# Copyright (c) 2015, Palo Alto Networks
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

# Author: Brian Torres-Gil <btorres-gil@paloaltonetworks.com>

# import modules
import logging
import xml.etree.ElementTree as ET

from base import PanObject, Root, MEMBER, ENTRY
from base import VarPath as Var
import network

# set logging to nullhandler to prevent exceptions if logging not enabled
try:
    # working for python 2.7 and higher
    logging.getLogger(__name__).addHandler(logging.NullHandler())
except AttributeError as e:
    # python 2.6 doesn't have a null handler, so create it
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass
    logging.NullHandler = NullHandler
    logging.getLogger(__name__).addHandler(logging.NullHandler())

logger = logging.getLogger(__name__)


class HighAvailabilityInterface(PanObject):
    """Base class for high availability interface classes

    Do not instantiate this class.  Use its subclasses

    """
    # TODO: Support encryption
    def __init__(self,
                 ip_address=None,
                 netmask=None,
                 port=None,
                 gateway=None,
                 link_speed="auto",
                 link_duplex="auto",
                 ):
        if type(self) == HighAvailabilityInterface:
            raise AssertionError("Do not instantiate a HighAvailabilityInterface. Please use a subclass.")
        super(HighAvailabilityInterface, self).__init__()
        self._port = port
        self.ip_address = ip_address
        self.netmask = netmask
        self.gateway = gateway
        self.link_speed = link_speed
        self.link_duplex = link_duplex

        # This is used by setup_interface method to remove old interfaces
        self.old_port = None

    @property
    def port(self):
        return self._port

    @port.setter
    def port(self, value):
        self.old_port = self._port
        self._port = value

    @staticmethod
    def vars():
        return (
            Var("port"),
            Var("ip-address"),
            Var("netmask"),
            Var("gateway"),
            Var("link-speed"),
            Var("link-duplex"),
        )

    def setup_interface(self):
        """Setup the interface itself as an HA interface"""
        pandevice = self.pandevice()
        if pandevice is None:
            return None
        if isinstance(self.port, basestring):
            intname = self.port
        else:
            intname = str(self.port)
        intconfig_needed = False
        if intname.startswith("ethernet"):
            intprefix = "ethernet"
            inttype = network.HAEthernetInterface
            intconfig_needed = True
        elif intname.startswith("ae"):
            intprefix = "ae"
            inttype = network.HAAggregateInterface
            intconfig_needed = True
        elif not intname.startswith("dedicated"):
            self.link_speed = None
            self.link_duplex = None
        interface = None
        if intconfig_needed:
            apply_needed = False
            interface = pandevice.find(intname, (network.EthernetInterface, network.AggregateInterface))
            if interface is None:
                interface = pandevice.add(inttype(name=intname))
                apply_needed = True
            elif not isinstance(interface, network.HAInterfaceMixin):
                self.parent.remove(interface)
                interface = pandevice.add(inttype(name=intname))
                apply_needed = True
            if self.link_speed is not None:
                if interface.link_speed != self.link_speed:
                    interface.link_speed = self.link_speed
                    apply_needed = True
                self.link_speed = None
            if self.link_duplex is not None:
                if interface.link_duplex != self.link_duplex:
                    interface.link_duplex = self.link_duplex
                    apply_needed = True
                self.link_duplex = None
            if apply_needed:
                interface.apply()
            return interface

    def delete_old_interface(self):
        if self.old_port is not None:
            self.delete_interface(self.old_port)
            self.old_port = None

    def delete_interface(self, interface=None, pandevice=None):
        """Delete the HA interface from the list of interfaces"""
        if pandevice is None:
            pandevice = self.pandevice()
        if pandevice is None:
            return None
        port = interface if interface is not None else self.port
        if isinstance(port, basestring):
            intname = port
        else:
            intname = str(port)
        intconfig_needed = False
        if intname.startswith("ethernet"):
            intprefix = "ethernet"
            inttype = network.HAEthernetInterface
            intconfig_needed = True
        elif intname.startswith("ae"):
            intprefix = "ae"
            inttype = network.HAAggregateInterface
            intconfig_needed = True
        elif not intname.startswith("dedicated"):
            self.link_speed = None
            self.link_duplex = None
        if intconfig_needed:
            interface = pandevice.find_or_create(intname, inttype)
            interface.delete()


class HA1(HighAvailabilityInterface):
    """HA1 interface class

    TODO: Encryption

    """

    XPATH = "/interface/ha1"

    def __init__(self,
                 ip_address=None,
                 netmask=None,
                 port="dedicated-ha1",
                 gateway=None,
                 link_speed="auto",
                 link_duplex="auto",
                 monitor_hold_time=3000,
                 ):
        super(HA1, self).__init__(ip_address, netmask, port, gateway, link_speed, link_duplex)
        self.monitor_hold_time=monitor_hold_time

    @staticmethod
    def vars():
        return super(HA1, HA1).vars() + (
            Var("monitor-hold-time", vartype="int"),
        )


class HA1Backup(HighAvailabilityInterface):
    XPATH = "/interface/ha1-backup"

    def __init__(self,
                 ip_address=None,
                 netmask=None,
                 port=None,
                 gateway=None,
                 link_speed="auto",
                 link_duplex="auto",
                 ):
        super(HA1Backup, self).__init__(ip_address, netmask, port, gateway, link_speed, link_duplex)


class HA2(HighAvailabilityInterface):
    XPATH = "/interface/ha2"

    def __init__(self,
                 ip_address=None,
                 netmask=None,
                 port="dedicated-ha2",
                 gateway=None,
                 link_speed="auto",
                 link_duplex="auto",
                 ):
        super(HA2, self).__init__(ip_address, netmask, port, gateway, link_speed, link_duplex)


class HA2Backup(HighAvailabilityInterface):
    XPATH = "/interface/ha2-backup"

    def __init__(self,
                 ip_address=None,
                 netmask=None,
                 port=None,
                 gateway=None,
                 link_speed="auto",
                 link_duplex="auto",
                 ):
        super(HA2Backup, self).__init__(ip_address, netmask, port, gateway, link_speed, link_duplex)


class HA3(HighAvailabilityInterface):
    XPATH = "/interface/ha3"

    def __init__(self,
                 port=None,
                 ):
        super(HA3, self).__init__(ip_address=None,
                                  netmask=None,
                                  port=port,
                                  gateway=None,
                                  link_speed=None,
                                  link_duplex=None,
                                  )

    @staticmethod
    def vars():
        return (
            Var("port"),
        )


class HighAvailability(PanObject):

    ROOT = Root.DEVICE
    XPATH = "/deviceconfig/high-availability"
    CHILDTYPES = (
        HA1,
        HA1Backup,
        HA2,
        HA2Backup,
        HA3,
    )

    ACTIVE_PASSIVE = "active-passive"
    ACTIVE_ACTIVE = "active-active"

    def __init__(self,
                 peer_ip=None,
                 enabled=True,
                 mode=ACTIVE_PASSIVE,
                 config_sync=True,
                 state_sync=True,
                 ha2_keepalive=False,
                 group_id=(1,),
                 description=None,
                 ):
        super(HighAvailability, self).__init__()
        self.peer_ip = peer_ip
        self.enabled = enabled
        self.mode = mode
        self.config_sync = config_sync
        self.state_sync = state_sync
        self.ha2_keepalive = ha2_keepalive
        self.group_id = list(group_id)
        self.description = description

        # Other settings that can be modified after instantiation
        self.passive_link_state = "auto"
        self.ha2_keepalive_action = "log-only"
        self.ha2_keepalive_threshold = 10000

    @staticmethod
    def vars():
        return (
            # Enabled flag
            Var("enabled", vartype="bool"),
            # Group
            Var("group", "group_id", vartype="entry"),
            Var("{{group_id}}/description"),
            Var("{{group_id}}/configuration-synchronization/enabled", "config_sync", vartype="bool"),
            Var("{{group_id}}/peer-ip"),
            # HA Mode (A/P, A/A)
            Var("{{group_id}}/mode/(active-passive|active-active)", "mode"),
            Var("{{group_id}}/mode/{{mode}}/passive-link-state", init=False),
            # State Synchronization
            Var("{{group_id}}/state-synchronization/enabled", "state_sync", vartype="bool"),
            # HA2 Keep-alive
            Var("{{group_id}}/state-synchronization/ha2-keep-alive/enabled", "ha2_keepalive", vartype="bool"),
            Var("{{group_id}}/state-synchronization/ha2-keep-alive/action", "ha2_keepalive_action", init=False),
            Var("{{group_id}}/state-synchronization/ha2-keep-alive/threshold", "ha2_keepalive_threshold", vartype="int", init=False),
            Var("interface", vartype="none"),
            Var("interface/ha1", vartype="none"),
            Var("interface/ha1-backup", vartype="none"),
            Var("interface/ha2", vartype="none"),
            Var("interface/ha2-backup", vartype="none"),
            Var("interface/ha3", vartype="none"),
        )


