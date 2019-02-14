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

from AccessControl.SecurityManagement import (
    getSecurityManager, newSecurityManager, noSecurityManager
)
from celery import Task
from celery.signals import before_task_publish, after_task_publish
# from celery.worker.request import Request
from ZPublisher.HTTPRequest import HTTPRequest
from ZPublisher.HTTPResponse import HTTPResponse
from ZPublisher.BaseRequest import RequestContainer

from Products.ZenUtils.Utils import getObjByPath

from .logger import StyleAdapter
from .zenjobs import app, osw


# class ZenRequest(Request):
#
#     pass


# class Logger(object):
#
#     def __call__(self, *args, **kwargs):
#         try:
#             log = StyleAdapter(logging.getLogger("zen.zenjobs.tasks"))
#             log.info("[{0.pid}] Logger: Setting up task logger", osw)
#             # Get log directory, ensure it exists
#             # logdir = self._get_config('job-log-path')
#             logdir = "/opt/zenoss/log/jobs"
#             try:
#                 os.makedirs(logdir)
#             except OSError as e:
#                 if e.errno != errno.EEXIST:
#                     raise
#             # Make the logfile path and store it in the backend
#             # for later retrieval
#             logfile = os.path.join(logdir, '%s.log' % self.request.id)
#             formatter = logging.Formatter(
#                 "%(asctime)s %(levelname)s %(name)s: %(message)s"
#             )
#             handler = logging.handlers.RotatingFileHandler(
#                 filename=logfile,
#                 maxBytes=10240 * 1024,
#                 backupCount=3
#             )
#             handler.setFormatter(formatter)
#
#             joblog = logging.getLogger("zen.zenjobs.job")
#             joblog.propagate = False
#             joblog.setLevel(logging.INFO)
#             joblog.addHandler(handler)
#             self.log = joblog
#             return super(Logger, self).__call__(*args, **kwargs)
#         finally:
#             log.info("[{0.pid}] Logger: Tearing down task logger", osw)
#             del self.log
#             handler.close()
#             joblog.handlers = []


class DMD(object):

    def __call__(self, *args, **kwargs):
        log = StyleAdapter(logging.getLogger("zen.zenjobs.tasks"))
        log.info("[{0.pid}] task_prerun: {1} {2} {3}", osw, self, args, kwargs)
        log.info("DMD: Setting up ZODB session")
        log.info(
            "DMD: request.userid: {}",
            self.request.userid
            if hasattr(self.request, "userid") else "<not found>"
        )
        connection, self.dmd = self.__setup(log)
        try:
            return super(DMD, self).__call__(*args, **kwargs)
        finally:
            self.__teardown(log, connection)

    def __teardown(self, log, connection):
        log.info("DMD: Tearing down ZODB session")
        connection.close()
        del self.dmd
        noSecurityManager()

    def __setup(self, log):
        try:
            connection = app.db.open()
            root = connection.root()
            application = getContext(root["Application"])
            dataroot = getObjByPath(application, "/zport/dmd")
            login(dataroot)
            return connection, dataroot
        except Exception as ex:
            log.exception(
                "Failed to setup ZODB for task: ({}) {}", type(ex), ex
            )
            raise


def getContext(app):
    resp = HTTPResponse(stdout=None)
    env = {
        'SERVER_NAME': 'localhost',
        'SERVER_PORT': '8080',
        'REQUEST_METHOD': 'GET'
    }
    req = HTTPRequest(None, env, resp)
    return app.__of__(RequestContainer(REQUEST=req))


def login(context, name='admin', userfolder=None):
    """Authenticate user and configure credentials.
    """
    if userfolder is None:
        userfolder = context.getPhysicalRoot().acl_users
    user = userfolder.getUserById(name)
    if user is None:
        return
    if not hasattr(user, 'aq_base'):
        user = user.__of__(userfolder)
    newSecurityManager(None, user)
    return user


def requires(*features):
    superclasses = tuple(features) + (Task, object,)
    name = ''.join(t.__name__ for t in features) + "Task"
    basetask = type(name, superclasses, {})
    return basetask


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


@app.task(bind=True, base=requires(DMD), ignore_result=False)
def legacy_wrapper(self, jobclasspath, *args, **kwargs):
    """This task executes legacy Job based tasks.
    """
    moduleName, clsName = jobclasspath.rsplit(".", 1)
    module = importlib.import_module(moduleName)
    cls = getattr(module, clsName)
    job = cls(log=self.log, dmd=self.dmd, request=self.request)
    return job.run(*args, **kwargs)


@app.task(bind=True, ignore_result=False)
def job(self, *args, **kw):
    deviceNames = [
        device.id for device in self.dmd.Devices.Server.Linux.devices()
    ]
    # attrs = ", ".join(dir(self))
    log = logging.getLogger("zen.zenjobs.job")
    log.info("device names: %s", deviceNames)
    return deviceNames
