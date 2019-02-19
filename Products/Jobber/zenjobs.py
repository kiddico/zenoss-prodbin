##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import os

from celery import Celery

from . import config

app = Celery("zenjobs")
app.config_from_object(config)


class oswrap(object):

    @property
    def pid(self):
        return os.getpid()


osw = oswrap()
