##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import errno
import logging
import logging.handlers
import os
import sys

import ZODB.config

from AccessControl.SecurityManagement import (
    newSecurityManager, noSecurityManager
)
from celery import Celery
from celery.signals import (
    setup_logging,  # worker_init,
    worker_ready, worker_shutting_down, worker_shutdown,
    worker_process_init, worker_process_shutdown,
    task_prerun, task_postrun
)
from celery.utils.log import LoggingProxy
from ZPublisher.HTTPRequest import HTTPRequest
from ZPublisher.HTTPResponse import HTTPResponse
from ZPublisher.BaseRequest import RequestContainer

from Products.ZenUtils.Utils import getObjByPath

from . import config

app = Celery("zenjobs")
app.config_from_object(config)

# Signal (event) Firing order
# ---------------------------
# worker_init
# setup_logging
# worker_process_init
# worker_ready
# ...
# worker_shutting_down
# worker_process_shutdown
# worker_shutdown


# @worker_init.connect
# def before_startup(sender=None, signal=None, **kw):
#     print("worker_init:", sender, signal, kw)


@worker_ready.connect
def after_startup(**kw):
    log = logging.getLogger("zen.zenjobs")
    log.info("worker_ready: %s", kw)


@worker_shutting_down.connect
def before_shutdown(**kw):
    log = logging.getLogger("zen.zenjobs")
    log.info("worker_shutting_down: %s", kw)


@worker_shutdown.connect
def before_exit(**kw):
    log = logging.getLogger("zen.zenjobs")
    log.info("worker_shutdown: %s", kw)


@worker_process_init.connect
def process_startup(**kw):
    log = logging.getLogger("zen.zenjobs")
    log.info("worker_process_init: %s", kw)
    log.info("worker_process_init: Initializing ZODB object")
    app.db = ZODB.config.databaseFromURL("file:///opt/zenoss/etc/zodb.conf")


@worker_process_shutdown.connect
def process_shutdown(**kw):
    log = logging.getLogger("zen.zenjobs")
    log.info("worker_process_shutdown: %s", kw)
    log.info("worker_process_shutdown: Closing ZODB object")
    app.db.close()


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

    logproxy = LoggingProxy(zenLog, logging.INFO)
    sys.__stdout__ = logproxy

    zenLog.info("setup_logging: Logging configured")


@task_prerun.connect
def setup_zodb(task=None, **kwargs):
    log = logging.getLogger("zen.zenjobs.tasks")
    # log.info("task_prerun: %s %s", task, kwargs)
    log.info("task_prerun: Setting up ZODB session")
    log.info(
        "task_prerun: request.userid: %s",
        task.request.userid
        if hasattr(task.request, "userid") else "<not found>"
    )
    try:
        task.connection = app.db.open()
        root = task.connection.root()
        application = getContext(root["Application"])
        dataroot = getObjByPath(application, "/zport/dmd")
        task.dmd = dataroot
        login(task.dmd)
    except Exception as ex:
        log.exception(
            "Failed to setup ZODB for task: (%s) %s", type(ex), ex
        )
        raise


@task_postrun.connect
def teardown_zodb(task=None, **kwargs):
    log = logging.getLogger("zen.zenjobs.tasks")
    # log.info("task_postrun: %s %s", task, kwargs)
    log.info("task_postrun: Tearing down ZODB session")
    task.connection.close()
    del task.dmd
    del task.connection
    noSecurityManager()


@task_prerun.connect
def setup_task_logger(task=None, **kwargs):
    log = logging.getLogger("zen.zenjobs.tasks")
    log.info("task_prerun: Setting up task logger")
    # Get log directory, ensure it exists
    # logdir = self._get_config('job-log-path')
    logdir = "/opt/zenoss/log/jobs"
    try:
        os.makedirs(logdir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    # Make the logfile path and store it in the backend for later retrieval
    logfile = os.path.join(logdir, '%s.log' % task.request.id)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    handler = logging.handlers.RotatingFileHandler(
        filename=logfile,
        maxBytes=10240 * 1024,
        backupCount=3
    )
    handler.setFormatter(formatter)

    joblog = logging.getLogger("zen.zenjobs.job")
    joblog.propagate = False
    joblog.setLevel(logging.INFO)
    joblog.addHandler(handler)
    task.log = joblog


@task_postrun.connect
def teardown_task_logger(task=None, **kwargs):
    log = logging.getLogger("zen.zenjobs.tasks")
    log.info("task_postrun: Tearing down task logger")
    # logdir = "/opt/zenoss/log/jobs"
    # logfile = os.path.join(logdir, '%s.log' % task.request.id)
    joblog = logging.getLogger("zen.zenjobs.job")
    for handler in joblog.handlers:
        handler.close()
    joblog.handlers = []


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
