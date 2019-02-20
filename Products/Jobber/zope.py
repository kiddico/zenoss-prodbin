##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from AccessControl import ClassSecurityInfo
from AccessControl.class_init import InitializeClass


class ZClassSecurityInfo(object):

    def __init__(self):
        self.__csi = ClassSecurityInfo()

    def private(self, f):
        self.__csi.declarePrivate(f.func_name)
        return f

    def protected(self, permission):
        def wrap(f):
            self.__csi.declareProtected(permission, f.func_name)
            return f
        return wrap

    def __getattr__(self, name):
        return getattr(self.__csi, name)


def initialize_class(cls):
    InitializeClass(cls)
