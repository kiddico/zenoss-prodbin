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

from datetime import datetime

from AccessControl import getSecurityManager
from celery import states

from .exceptions import NoSuchJobException
from .jobs import Job
from .zenjobs import app

log = logging.getLogger("zen.JobManager")


def _getAsyncResult(task, task_id):
    if not isinstance(task, (str, unicode)):
        task = ".".join(task.__module__, task.__name__)
    instance = app.tasks.get(task)
    if instance is None:
        raise NoSuchJobException("%s not found" % task)
    return


class JobRecord(object):

    def __init__(self):
        self.__user = None
        self.__name = None
        self.__type = None
        self.__description = None
        self.__status = states.PENDING
        self.__schedule = None
        self.__started = None
        self.__done = None
        self.__result = None

    @property
    def _async_result(self):
        if not self.job_name:
            tasks = app.tasks.values()
            for task in (t for t in tasks if isinstance(t, Job)):
                if task.getJobType() == self.job_type:
                    self.job_name = task.name
                    break
            else:
                raise AttributeError(
                    "No job class associated with job %s" % self.id
                )
        return app.tasks[self.job_name].AsyncResult(self.getId())

    def abort(self):
        # This will occur immediately.
        return self._async_result.abort()

    def wait(self):
        return self._async_result.wait()

    def update(self, d):
        for k, v in d.iteritems():
            setattr(self, k, v)
        if self.isFinished():
            self.errors = self._parseErrors()

    def _parseErrors(self):
        if not hasattr(self, "logfile"):
            return ""
        try:
            with open(self.logfile, "r") as f:
                buffer = f.readlines()
                # look for error level log lines
                return "\n".join(
                    [line for line in buffer if "ERROR zen." in line]
                )
        except (IOError, AttributeError, TypeError):
            return ""

    def isFinished(self):
        return getattr(self, "status", None) in states.READY_STATES

    def getId(self):
        return self.task_id

    @property
    def uuid(self):
        return self.task_id

    @property
    def description(self):
        return self.job_description

    @property
    def type(self):
        return self.job_type

    @property
    def scheduled(self):
        return self.date_scheduled

    @property
    def started(self):
        return self.date_started

    @property
    def finished(self):
        return self.date_done


def _savejobrecord(self, job_id, job, desc, args, kwargs, **properties):
    # Put a pending job in the database. zenjobs will wait to run this
    # job until it exists.
    try:
        desc = desc if desc else job.getJobDescription(*args, **kwargs)
    except Exception:
        desc = "%s(%s, %s)" % (job.name, args, kwargs)

    user = getSecurityManager().getUser()
    if not isinstance(user, basestring):
        user = user.getId()

    # Add job metadata to the database
    meta = JobRecord(
        id=job_id,
        user=user,
        job_name=job.name,
        job_type=job.getJobType(),
        job_description=desc,
        date_scheduled=datetime.utcnow(),
    )
    for prop, propval in properties.iteritems():
        setattr(meta, prop, propval)
    self._setOb(job_id, meta)
    jobrecord = self._getOb(job_id)
    # self.getCatalog().catalog_object(jobrecord)
    log.info(
        "Created job %s: %s, description: %s", job, jobrecord.id, desc
    )
    return jobrecord
