##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import importlib
import logging

# from AccessControl.SecurityManagement import getSecurityManager
# from celery.signals import before_task_publish, after_task_publish

from .feature import requires, DMD
from .zenjobs import app


# @before_task_publish.connect
# def attach_userid(headers=None, **kwargs):
#     """Adds a 'userid' field to the task's headers.  The value of userid
#     is the ID of the user that sent the task.
#     """
#     log = logging.getLogger("zen.zenjobs")
#     log.info("before_task_publish: %s %s", headers, kwargs)
#     # Note: this method is invoked on the client side.
#     # Note: 'headers' is never None, but it's desired to mark 'headers'
#     # as a keyword argument rather than a positional argument.
#     userid = getSecurityManager().getUser().getId()
#     try:
#         headers["userid"] = userid
#     except TypeError as ex:
#         log = logging.getLogger("zen.zenjobs.tasks")
#         log.error("No headers for task?: %s", ex)


# @after_task_publish.connect
# def after_publish(**kw):
#     log = logging.getLogger("zen.zenjobs")
#     log.info("after_task_publish: %s", kw)


@app.task(bind=True, base=requires(DMD), ignore_result=False)
def legacy_job(self, jobclasspath, *args, **kwargs):
    """This task executes legacy Job based tasks.
    """
    moduleName, clsName = jobclasspath.rsplit(".", 1)
    module = importlib.import_module(moduleName)
    cls = getattr(module, clsName)
    job = cls(log=self.log, dmd=self.dmd, request=self.request)
    result = job.run(*args, **kwargs)
    self.log.info("result = %s", result)
    return result


@app.task(bind=True, ignore_result=False)
def job(self, *args, **kw):
    deviceNames = [
        device.id for device in self.dmd.Devices.Server.Linux.devices()
    ]
    # attrs = ", ".join(dir(self))
    log = logging.getLogger("zen.zenjobs.job")
    log.info("device names: %s", deviceNames)
    return deviceNames
