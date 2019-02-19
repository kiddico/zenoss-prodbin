from __future__ import absolute_import, print_function

import errno
import logging
import logging.handlers
import logging.config
import os
import sys

import ZODB.config

from AccessControl.SecurityManagement import getSecurityManager
from celery.utils.log import LoggingProxy, get_task_logger

from .logger import FormatStringAdapter, log_config, configure_task_logger
from .zenjobs import app, osw


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


def attach_userid(headers=None, **kwargs):
    """Adds a 'userid' field to the task's headers.  The value of userid
    is the ID of the user that sent the task.
    """
    # log = logging.getLogger("zen.zenjobs")
    log = get_task_logger(__name__)
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


def after_publish(**kw):
    # log = logging.getLogger("zen.zenjobs")
    log = get_task_logger(__name__)
    log.info("after_task_publish: %s", kw)


# def before_startup(sender=None, signal=None, **kw):
#     print("worker_init:", sender, signal, kw)


# def after_startup(**kw):
#     log = FormatStringAdapter(logging.getLogger("zen.zenjobs"))
#     log.info("[{0.pid}] worker_ready: {1}", osw, kw)


# def before_shutdown(**kw):
#     log = FormatStringAdapter(logging.getLogger("zen.zenjobs"))
#     log.info("[{0.pid}] worker_shutting_down: {1}", osw, kw)


# def before_exit(**kw):
#     log = FormatStringAdapter(logging.getLogger("zen.zenjobs"))
#     log.info("[{0.pid}] worker_shutdown: {1}", osw, kw)


def setup_zodb(**kw):
    # log = FormatStringAdapter(logging.getLogger("zen.zenjobs"))
    log = FormatStringAdapter(logging.getLogger(__name__))
    log.info("[{0.pid}] worker_process_init: {1}", osw, kw)
    log.info("worker_process_init: Initializing ZODB object")
    app.db = ZODB.config.databaseFromURL("file:///opt/zenoss/etc/zodb.conf")


def teardown_zodb(**kw):
    # log = FormatStringAdapter(logging.getLogger("zen.zenjobs"))
    log = FormatStringAdapter(logging.getLogger(__name__))
    log.info("[{0.pid}] worker_process_shutdown: {1}", osw, kw)
    log.info("worker_process_shutdown: Closing ZODB object")
    app.db.close()


def configure_logging(**ignored):
    """
    Create formating for log entries and set default log level
    """
    logging.config.dictConfig(log_config)

    zenLog = logging.getLogger("zen")
    logproxy = LoggingProxy(zenLog, logging.INFO)
    sys.__stdout__ = logproxy

    FormatStringAdapter(zenLog).info(
        "[{0.pid}] setup_logging: Logging configured", osw
    )


def setup_task_logger(task=None, **kwargs):
    # log = FormatStringAdapter(logging.getLogger("zen.zenjobs.tasks"))
    log = FormatStringAdapter(logging.getLogger(__name__))
    log.info("[{0.pid}] task_prerun: Setting up task logger", osw)
    # # Get log directory, ensure it exists
    # # logdir = self._get_config('job-log-path')
    # logdir = "/opt/zenoss/log/jobs"
    # try:
    #     os.makedirs(logdir)
    # except OSError as e:
    #     if e.errno != errno.EEXIST:
    #         raise
    # # Make the logfile path and store it in the backend for later retrieval
    # logfile = os.path.join(logdir, '%s.log' % task.request.id)
    # formatter = logging.Formatter(
    #     "%(asctime)s %(levelname)s %(name)s: %(message)s"
    # )
    # handler = logging.handlers.RotatingFileHandler(
    #     filename=logfile,
    #     maxBytes=10240 * 1024,
    #     backupCount=3
    # )
    # handler.setFormatter(formatter)
    # joblog = logging.getLogger("zen.zenjobs.job")
    # joblog.propagate = False
    # joblog.setLevel(logging.INFO)
    # joblog.addHandler(handler)
    log = get_task_logger(__name__)
    configure_task_logger(log, task.request.id, task.name)
    task.log = log


def teardown_task_logger(task=None, **kwargs):
    # log = FormatStringAdapter(logging.getLogger("zen.zenjobs.tasks"))
    log = FormatStringAdapter(logging.getLogger(__name__))
    log.info("[{0.pid}] task_postrun: Tearing down task logger", osw)
    # logdir = "/opt/zenoss/log/jobs"
    # logfile = os.path.join(logdir, '%s.log' % task.request.id)
    # joblog = logging.getLogger("zen.zenjobs.job")
    print(
        "task.log.handlers -> %s"
        % (', '.join(str(h) for h in task.log.handlers))
    )
    for handler in task.log.handlers:
        print("Closing %s" % handler)
        print(dir(handler))
        if hasattr(handler, "baseFilename"):
            fn = handler.baseFilename
            print("baseFileName -> (%s) %s" % (
                "exists" if os.path.exists(fn) else "missing", fn
            ))

        handler.flush()
        handler.close()
    task.log.handlers = []
    del task.log


def config_logger(
    logger=None, loglevel=None, logfile=None, format=None, colorize=None,
    **kw
):
    logger.info(
        "<after_setup_logger> handlers %s",
        ", ".join(str(h) for h in logger.handlers)
    )
    # logging.config.dictConfig(log_config)
    # zenLog = logging.getLogger("zen")
    # logproxy = LoggingProxy(zenLog, logging.INFO)
    # sys.__stdout__ = logproxy


def config_task_logger(
    logger=None, loglevel=None, logfile=None, format=None, colorize=None,
    **kw
):
    logger.info(
        "<after_setup_task_logger> handlers %s",
        ", ".join(str(h) for h in logger.handlers)
    )
    for handler in logger.handlers:
        if hasattr(handler, "close"):
            handler.close()
    logger.handlers = []
    # print("logger.name      ->", logger.name)
    # print("logger.propagate ->", logger.propagate)
    # print("logger.parent    ->", logger.parent)
    # print(dir(logger))
    # print("=====\n", dir(logger.manager))


# @task_success.connect
# def handle_success(*args, **kw):
#     log = FormatStringAdapter(logging.getLogger("zen.zenjobs.tasks"))
#     log.info("[{0.pid}] task_success: task succeeded {1} {2}", osw, args, kw)
