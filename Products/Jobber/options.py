import logging
import re

from copy import copy
from optparse import (
    OptionParser, Option, OptionGroup,
    OptionValueError,
)
from Products.ZenUtils.Utils import zenPath


def checkLogLevel(option, opt, value):
    if re.match(r'^\d+$', value):
        value = int(value)
    else:
        intval = getattr(logging, value.upper(), None)
        if intval:
            value = intval
        else:
            raise OptionValueError('"%s" is not a valid log level.' % value)

    return value


class LogSeverityOption(Option):
    TYPES = Option.TYPES + ("loglevel",)
    TYPE_CHECKER = copy(Option.TYPE_CHECKER)
    TYPE_CHECKER["loglevel"] = checkLogLevel


usage = "%prog [options]"
version = "1.0"
parser = OptionParser(
    usage=usage,
    version="%prog " + version,
    option_class=LogSeverityOption
)


def options(self):
    self.parser.add_option(
        "--starttimeout",
        dest="starttimeout",
        type="int",
        help="Wait seconds for initial heartbeat",
    )
    self.parser.add_option(
        "--heartbeattimeout",
        dest="heartbeatTimeout",
        type="int",
        help="Set a heartbeat timeout in seconds for a daemon",
        default=900,
    )

    self.parser.add_option(
        "-C",
        "--configfile",
        dest="configfile",
        help="Use an alternate configuration file",
    )

    # self.parser.add_option(
    #     "--genconf",
    #     action="store_true",
    #     default=False,
    #     help="Generate a template configuration file",
    # )
    # self.parser.add_option(
    #     "--genxmltable",
    #     action="store_true",
    #     default=False,
    #     help="Generate a Docbook table showing command-line switches.",
    # )
    # self.parser.add_option(
    #     "--genxmlconfigs",
    #     action="store_true",
    #     default=False,
    #     help="Generate an XML file containing command-line switches.",
    # )

    self.parser.add_option(
        "--job-log-path",
        dest="job_log_path",
        default=zenPath("log", "jobs"),
        help="Directory in which to store individual job log files",
    )
    self.parser.add_option(
        "--max-jobs-per-worker",
        dest="max_jobs_per_worker",
        type="int",
        default=1,
        help="Number of jobs a worker process runs before it shuts down",
    )
    self.parser.add_option(
        "--concurrent-jobs",
        dest="num_workers",
        type="int",
        default=2,
        help="Number of jobs to process concurrently",
    )

    # group = OptionGroup(
    #     parser,
    #     "ZODB Options",
    #     "ZODB connection options and MySQL Adapter options.",
    # )
    # group.add_option(
    #     "--zodb-cachesize",
    #     dest="zodb_cachesize",
    #     default=1000,
    #     type="int",
    #     help="in memory cachesize default: 1000",
    # )
    # group.add_option(
    #     "--zodb-cacheservers",
    #     dest="zodb_cacheservers",
    #     default="",
    #     help="memcached servers to use for object cache "
    #     "(eg. 127.0.0.1:11211)",
    # )
    # group.add_option(
    #     "--zodb-cache-max-object-size",
    #     dest="zodb_cache_max_object_size",
    #     default=None,
    #     type="int",
    #     help="memcached maximum object size in bytes",
    # )
    # group.add_option(
    #     "--zodb-commit-lock-timeout",
    #     dest="zodb_commit_lock_timeout",
    #     default=30,
    #     type="int",
    #     help=(
    #         "Specify the number of seconds a database connection will "
    #         "wait to acquire a database 'commit' lock before failing "
    #         "(defaults to 30 seconds if not specified)."
    #     ),
    # )
    # parser.add_option_group(group)

    group = OptionGroup(self.parser, "Logging Options")
    group.add_option(
        "-v",
        "--logseverity",
        dest="logseverity",
        default="INFO",
        type="loglevel",
        help="Logging severity threshold",
    )
    group.add_option(
        "--logpath",
        dest="logpath",
        default=zenPath("log"),
        type="str",
        help="Override the default logging path; default $ZENHOME/log",
    )
    group.add_option(
        "--maxlogsize",
        dest="maxLogKiloBytes",
        default=10240,
        type="int",
        help="Max size of log file in KB; default 10240",
    )
    group.add_option(
        "--maxbackuplogs",
        dest="maxBackupLogs",
        default=3,
        type="int",
        help="Max number of back up log files; default 3",
    )
    self.parser.add_option_group(group)
