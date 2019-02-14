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
import logging.config
import os
import sys

import ZODB.config

# from AccessControl.SecurityManagement import (
#     newSecurityManager, noSecurityManager
# )
from celery import Celery
from celery.signals import (
    setup_logging,  # worker_init,
    worker_ready, worker_shutting_down, worker_shutdown,
    worker_process_init, worker_process_shutdown,
    task_prerun, task_postrun,
    task_success
)
from celery.utils.log import LoggingProxy
# from ZPublisher.HTTPRequest import HTTPRequest
# from ZPublisher.HTTPResponse import HTTPResponse
# from ZPublisher.BaseRequest import RequestContainer

# from Products.ZenUtils.Utils import getObjByPath

from . import config
from .logger import StyleAdapter

app = Celery("zenjobs")
app.config_from_object(config)


class oswrap(object):

    @property
    def pid(self):
        return os.getpid()


osw = oswrap()

# Signal Firing order (process) + handler(s)
# ----------------------------------------
#  1. worker_init (worker)
#
#  2. setup_logging (worker)
#     + configure_logging
#
#  3. worker_process_init (worker process)
#     + setup_zodb
#
#  4. worker_ready (worker)
#
# before_task_publish (client)
#
# after_task_publish (client)
#
#  5. task_prerun (worker process)
#     + setup_zodb_session
#     + setup_task_logger
#
#  6. task_retry (worker process)
#  6. task_success (worker process)
#  6. task_failure (worker process)
#  6. task_revoked (worker process)
#  6. task_unknown (worker process)
#  6. task_rejected (worker process)
#
#  7. task_postrun (worker process)
#     + teardown_zodb_session
#     + teardown_task_logger
#
#  8. worker_shutting_down (worker)
#
#  9. worker_process_shutdown (worker process)
#     + teardown_zodb
#
# 10. worker_shutdown (worker)


# @worker_init.connect
# def before_startup(sender=None, signal=None, **kw):
#     print("worker_init:", sender, signal, kw)


@worker_ready.connect
def after_startup(**kw):
    log = StyleAdapter(logging.getLogger("zen.zenjobs"))
    log.info("[{0.pid}] worker_ready: {1}", osw, kw)


@worker_shutting_down.connect
def before_shutdown(**kw):
    log = StyleAdapter(logging.getLogger("zen.zenjobs"))
    log.info("[{0.pid}] worker_shutting_down: {1}", osw, kw)


@worker_shutdown.connect
def before_exit(**kw):
    log = StyleAdapter(logging.getLogger("zen.zenjobs"))
    log.info("[{0.pid}] worker_shutdown: {1}", osw, kw)


@worker_process_init.connect
def setup_zodb(**kw):
    log = StyleAdapter(logging.getLogger("zen.zenjobs"))
    log.info("[{0.pid}] worker_process_init: {1}", osw, kw)
    log.info("worker_process_init: Initializing ZODB object")
    app.db = ZODB.config.databaseFromURL("file:///opt/zenoss/etc/zodb.conf")


@worker_process_shutdown.connect
def teardown_zodb(**kw):
    log = StyleAdapter(logging.getLogger("zen.zenjobs"))
    log.info("[{0.pid}] worker_process_shutdown: {1}", osw, kw)
    log.info("worker_process_shutdown: Closing ZODB object")
    app.db.close()


log_config = {
    "version": 1,
    "formatters": {
        "default": {
            "format": "%(asctime)s %(levelname)s %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "/opt/zenoss/log/zenjobs.log",
            "maxBytes": 10240 * 1024,
            "backupCount": 3,
            "mode": "a",
        },
    },
    "loggers": {
        "zen": {
            "level": logging.INFO,
        },
    },
    "root": {
        "level": logging.WARN,
        "handlers": ["default"],
    },
}


@setup_logging.connect
def configure_logging(**ignored):
    """
    Create formating for log entries and set default log level
    """
    logging.config.dictConfig(log_config)

    zenLog = logging.getLogger("zen")
    logproxy = LoggingProxy(zenLog, logging.INFO)
    sys.__stdout__ = logproxy

    StyleAdapter(zenLog).info(
        "[{0.pid}] setup_logging: Logging configured", osw
    )


# @task_prerun.connect
# def setup_zodb_session(task=None, **kwargs):
#     log = StyleAdapter(logging.getLogger("zen.zenjobs.tasks"))
#     log.info("[{0.pid}] task_prerun: {1} {2}", osw, task, kwargs)
#     log.info("task_prerun: Setting up ZODB session")
#     log.info(
#         "task_prerun: request.userid: {}",
#         task.request.userid
#         if hasattr(task.request, "userid") else "<not found>"
#     )
#     try:
#         task.connection = app.db.open()
#         root = task.connection.root()
#         application = getContext(root["Application"])
#         dataroot = getObjByPath(application, "/zport/dmd")
#         task.dmd = dataroot
#         login(task.dmd)
#     except Exception as ex:
#         log.exception(
#             "Failed to setup ZODB for task: ({}) {}", type(ex), ex
#         )
#         raise


# @task_postrun.connect
# def teardown_zodb_session(task=None, **kwargs):
#     log = StyleAdapter(logging.getLogger("zen.zenjobs.tasks"))
#     log.info("[{0.pid}] task_postrun: {1} {2}", osw, task, kwargs)
#     log.info("task_postrun: Tearing down ZODB session")
#     task.connection.close()
#     del task.dmd
#     del task.connection
#     noSecurityManager()


@task_prerun.connect
def setup_task_logger(task=None, **kwargs):
    log = StyleAdapter(logging.getLogger("zen.zenjobs.tasks"))
    log.info("[{0.pid}] task_prerun: Setting up task logger", osw)
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
    log = StyleAdapter(logging.getLogger("zen.zenjobs.tasks"))
    log.info("[{0.pid}] task_postrun: Tearing down task logger", osw)
    # logdir = "/opt/zenoss/log/jobs"
    # logfile = os.path.join(logdir, '%s.log' % task.request.id)
    joblog = logging.getLogger("zen.zenjobs.job")
    for handler in joblog.handlers:
        handler.close()
    joblog.handlers = []


@task_success.connect
def handle_success(*args, **kw):
    log = StyleAdapter(logging.getLogger("zen.zenjobs.tasks"))
    log.info("[{0.pid}] task_success: task succeeded {1} {2}", osw, args, kw)


# def getContext(app):
#     resp = HTTPResponse(stdout=None)
#     env = {
#         'SERVER_NAME': 'localhost',
#         'SERVER_PORT': '8080',
#         'REQUEST_METHOD': 'GET'
#     }
#     req = HTTPRequest(None, env, resp)
#     return app.__of__(RequestContainer(REQUEST=req))


# def login(context, name='admin', userfolder=None):
#     """Authenticate user and configure credentials.
#     """
#     if userfolder is None:
#         userfolder = context.getPhysicalRoot().acl_users
#     user = userfolder.getUserById(name)
#     if user is None:
#         return
#     if not hasattr(user, 'aq_base'):
#         user = user.__of__(userfolder)
#     newSecurityManager(None, user)
#     return user
