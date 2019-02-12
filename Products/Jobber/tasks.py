##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import logging

from AccessControl.SecurityManagement import getSecurityManager
from celery import Task
from celery.signals import before_task_publish, after_task_publish
from celery.worker.request import Request

from .zenjobs import app


class ZenRequest(Request):

    pass


class ZenTask(Task):

    Request = ZenRequest
    abstract = True

    # def __call__(self, *args, **kwargs):
    #     log = logging.getLogger("zen.zenjobs.tasks")
    #     log.info(
    #         "request.userid: %s",
    #         self.request.userid
    #         if hasattr(self.request, "userid") else "<not found>"
    #     )
    #     try:
    #         log.info("Setting up a dmd instance")
    #         connection = self.db.open()
    #         root = connection.root()
    #         self.app = getContext(root["Application"])
    #         self.dataroot = getObjByPath(self.app, "/zport/dmd")
    #         self.dmd = self.dataroot
    #         login(self.dmd)
    #         return super(ZenTask, self).__call__(*args, **kwargs)
    #     except Exception as ex:
    #         print ex
    #     finally:
    #         log.info("cleaning up")
    #         del self.dmd
    #         del self.dataroot
    #         del self.app
    #         connection.close()
    #         noSecurityManager()


@before_task_publish.connect
def attach_userid(headers=None, **kwargs):
    """Adds a 'userid' field to the task's headers.  The value of userid
    is the ID of the user that sent the task.
    """
    log = logging.getLogger("zen.zenjobs")
    log.info("before_task_publish: %s %s", headers, kwargs)
    # Note: this method is invoked on the client side.
    # Note: 'headers' is never None, but it's desired to mark 'headers'
    # as a keyword argument rather than a positional argument.
    userid = getSecurityManager().getUser().getId()
    try:
        headers["userid"] = userid
    except TypeError as ex:
        log = logging.getLogger("zen.zenjobs.tasks")
        log.error("No headers for task?: %s", ex)


@after_task_publish.connect
def after_publish(**kw):
    log = logging.getLogger("zen.zenjobs")
    log.info("after_task_publish: %s", kw)


# @app.task(bind=True, base=ZenTask)
# def legacy_wrapper(self, jobcls, *args, **kwargs):
#     """This task executes legacy Job based tasks.
#     """
#     config = getGlobalConfiguration()
#     job = jobcls(
#         log=log, dmd=self.dmd, request=self.request, options=config
#     )
#     return job.run(*args, **kwargs)


@app.task(bind=True, ignore_result=False)
def job(self, *args, **kw):
    deviceNames = [
        device.id for device in self.dmd.Devices.Server.Linux.devices()
    ]
    # attrs = ", ".join(dir(self))
    log = logging.getLogger("zen.zenjobs.job")
    log.info("device names: %s", deviceNames)
    return deviceNames
