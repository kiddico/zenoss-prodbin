###########################################################################
#       
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#       
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#       
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
from zope.viewlet.interfaces import IViewletManager, IViewlet
from zope.publisher.interfaces.browser import IBrowserRequest

class IPrimaryNavigationMenu(IViewletManager):
    """
    Navigation menu viewlet manager.
    """

class ISecondaryNavigationMenu(IViewletManager):
    """
    Navigation menu viewlet manager.
    """

class INavigationItem(IViewlet):
    """
    A navigable item.
    """

class IZenossNav(IBrowserRequest):
    """
    Marker interface for our nav layer
    """
