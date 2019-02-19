##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

from celery import signals


def job(_context, class_, name=None):
    pass


def signal(_context, name, handler):
    signal = getattr(signals, name, None)
    if signal is None:
        raise AttributeError("No such signal named '%s'" % name)
    handler_fn = _context.resolve(handler)
    signal.connect(handler_fn)
