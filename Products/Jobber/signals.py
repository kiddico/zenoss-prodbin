##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import logging

import ZODB.config

from AccessControl.SecurityManagement import getSecurityManager
from celery.utils.log import get_task_logger

from .logger import FormatStringAdapter
from .utils import osw
from .zenjobs import app

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


# @task_success.connect
# def handle_success(*args, **kw):
#     log = FormatStringAdapter(logging.getLogger("zen.zenjobs.tasks"))
#     log.info("[{0.pid}] task_success: task succeeded {1} {2}", osw, args, kw)
