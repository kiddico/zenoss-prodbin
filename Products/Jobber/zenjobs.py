##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import logging
import logging.handlers

from celery import Celery
from celery.signals import setup_logging, worker_init

from . import config

app = Celery("zenjobs")
app.config_from_object(config)


@worker_init.connect
def before_startup(*args, **kw):
    print "args %s; kw %s" % (args, kw)


@setup_logging.connect
def configure_logging(**ignored):
    """
    Create formating for log entries and set default log level
    """
    rootLog = logging.getLogger()
    rootLog.setLevel(logging.WARN)
    rootLog.handlers = []

    zenLog = logging.getLogger('zen')
    zenLog.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    handler = logging.handlers.RotatingFileHandler(
        filename="/opt/zenoss/log/zenjobs.log",
        maxBytes=10240 * 1024,
        backupCount=3
    )
    handler.setFormatter(formatter)
    rootLog.addHandler(handler)
