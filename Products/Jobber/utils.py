##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import os

from AccessControl import ClassSecurityInfo
from AccessControl.class_init import InitializeClass as initClass


class ZClassSecurityInfo(object):
    """Use AccessControl.ClassSecurityInfo as a function decorator.
    """

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


def ZInitializeClass(cls):
    """Use AccessControl.class_init.InitializeClass as a class decorator.
    """
    initClass(cls)
    return cls


class abstractclassmethod(classmethod):
    """Decorator to specify an abstract classmethod.
    """

    __isabstractmethod__ = True

    def __init__(cls, method):
        method.__isabstractmethod__ = True
        super(abstractclassmethod, cls).__init__(method)


class abstractstaticmethod(classmethod):
    """Decorator to specify an abstract staticmethod.
    """

    __isabstractmethod__ = True

    def __init__(cls, method):
        method.__isabstractmethod__ = True
        super(abstractstaticmethod, cls).__init__(method)


class oswrap(object):
    """Wraps the os module to expose various 'get' functions as properties.

    The use case for this class is format strings, e.g. rather than writing

        "The pid is {}".format(os.getpid())

    instead, write this:

        "This pid is {0.pid}".format(osw)

    This defers calling the function until the string is evaluated.
    """

    @property
    def pid(self):
        return os.getpid()


osw = oswrap()
