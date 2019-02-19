##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import errno
import logging
import os

from Products.ZenUtils.Utils import zenPath

# This implementation is based on the StyleAdapter example given in
# https://docs.python.org/3/howto/logging-cookbook.html


class FormatStringAdapter(logging.LoggerAdapter):
    """This adapter supports the use of '{}' format strings for
    log messages.

    Usage:

        log = FormatStringAdapter(log.getLogger("zen"))
        log.info("Hello {}!", "world")

        d = {'a': 1234}
        log.info("Value of a -> {0[a]}", d)  # Value of a -> 1234
    """

    def __init__(self, logger, extra=None):
        """Initialize an instance of FormatStringAdapter.

        @param logger {Logger} The logger to adapt.
        @param extra {dict} Additional context variables to appy to the
            message template string (not the message itself).
        """
        super(FormatStringAdapter, self).__init__(logger, extra or {})

    def log(self, level, msg, *args, **kwargs):
        if self.isEnabledFor(level):
            msg, kwargs = self.process(msg, kwargs)
            self.logger._log(level, _Message(msg, args), (), **kwargs)

    def debug(self, msg, *args, **kwargs):
        self.log(logging.DEBUG, msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.log(logging.INFO, msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.log(logging.WARNING, msg, *args, **kwargs)

    def warn(self, msg, *args, **kwargs):
        self.log(logging.WARN, msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.log(logging.ERROR, msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        if self.isEnabledFor(logging.ERROR):
            msg, kwargs = self.process(msg, kwargs)
            kwargs["exc_info"] = 1
            self.logger._log(logging.ERROR, _Message(msg, args), (), **kwargs)

    def critical(self, msg, *args, **kwargs):
        self.log(logging.CRITICAL, msg, *args, **kwargs)


class _Message(object):

    def __init__(self, fmt, args):
        self.fmt = fmt
        self.args = args

    def __str__(self):
        return self.fmt.format(*self.args)


log_config = {
    "version": 1,
    "formatters": {
        "worker": {
            "format": (
                "%(asctime)s %(levelname)s "
                "%(processName)s "
                "%(name)s: %(message)s"
            ),
            "datefmt": "%Y-%m-%dT%H:%M:%S",
        },
    },
    "handlers": {
        "worker": {
            "formatter": "worker",
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
        "handlers": ["worker"],
    },
}


class ZenJobsLoggingFilter(logging.Filter):
    """Extends the standard LogRecord to include the Celery worker name
    and the name of the Celery Task.
    """

    def __init__(self, taskid, taskname):
        self._taskid = taskid
        self._taskname = taskname

    def filter(self, record):
        record.taskid = self._taskid
        record.taskname = self._taskname
        return True  # keep the record


_formatter = logging.Formatter(
    # "%(asctime)s %(levelname)s %(processName)s/%(taskname)s "
    "%(asctime)s %(levelname)s %(processName)s "
    "%(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S"
)


def configure_task_logger(logger, task_id, name):
    """Configure and return a logger.
    """
    # logdir = self._get_config('job-log-path')
    logdir = zenPath("log", "jobs")
    print("#### logdir -> %s" % logdir)
    try:
        os.makedirs(logdir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    logfile = os.path.join(logdir, '%s.log' % task_id)
    print("#### logfile -> %s" % logfile)
    handler = logging.handlers.RotatingFileHandler(
        filename=logfile,
        maxBytes=10240 * 1024,
        backupCount=3
    )
    handler.setFormatter(_formatter)
    logger.addHandler(handler)
    # tfilter = ZenJobsLoggingFilter(task_id, name)
    # logger.addFilter(tfilter)
    # logger.propagate = False
    logger.setLevel(logging.INFO)
