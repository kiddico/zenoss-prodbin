##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import os

from datetime import datetime, timedelta
from logging import getLogger
from uuid import uuid4

import transaction

from celery import chain, states

from Products.Five.browser import BrowserView

from Products.ZenModel.ZenModelRM import ZenModelRM
from ZODB.POSException import ConflictError

from Products.ZenModel.ZenossSecurity import ZEN_MANAGE_DMD

from .exceptions import NoSuchJobException
from .jobs import PruneJob
from .tasks import legacy_job
from .utils import ZClassSecurityInfo, ZInitializeClass

log = getLogger("zen.JobManager")

CATALOG_NAME = "job_catalog"


def manage_addJobManager(context, id="JobManager"):
    jm = JobManager(id)
    context._setObject(id, jm)
    return getattr(context, id)


@ZInitializeClass
class JobManager(ZenModelRM):

    meta_type = portal_type = "JobManager"
    # lastPruneJobAddTime = datetime.now()
    # lastPruneTime = lastPruneJobAddTime
    security = ZClassSecurityInfo()

    @security.protected(ZEN_MANAGE_DMD)
    def addJobChain(self, *joblist, **options):
        """Submit a list of SubJob objects that will execute in list order.

        If options are specified, they are applied to each subjob; options
        that were specified directly on the subjob are not overridden.

        Supported options include:
            immutable {bool} Set True to 'freeze' the job arguments.
            ignoreresult {bool} Set True to drop the result of the jobs.

        If both options are not set, they default to False, which means the
        result of the prior job is passed to the next job as argument(s).

        @returns A list of JobRecord objects.
        """
        subtasks = []
        records = []
        for subjob in joblist:
            task_id = str(uuid4())
            opts = dict(task_id=task_id, **options)
            opts.update(subjob.options)
            subtask = subjob.job.subtask(
                args=subjob.args, kwargs=subjob.kwargs, **opts
            )
            records.append(
                self._savejobrecord(
                    task_id,
                    subjob.job,
                    subjob.description,
                    subjob.args,
                    subjob.kwargs,
                )
            )
            subtasks.append(subtask)
        task = chain(*subtasks)

        task.s().apply_async()

        return records

    @security.protected(ZEN_MANAGE_DMD)
    def addJob(
        self, jobclass,
        description=None, args=None, kwargs=None, properties=None,
    ):
        """Submit a job to run.

        @param jobclass {Job} The job to run
        @param description {str} The job's description
        @param args {tuple} position arguments to job
        @param kwargs {dict} keyword arguments to job
        @param properties {dict} Modifiers on running the job
        @return {JobRecord} A JobRecord object
        """
        args = args or ()
        kwargs = kwargs or {}
        properties = properties or {}

        # Create the task ID here (tell Celery to use this ID)
        job_id = str(uuid4())

        # Build the task's signature (i.e. call signature)
        clspath = ".".join((jobclass.__module__, jobclass.__name__))
        s = legacy_job.s(
            clspath, *args, **kwargs
        ).set(task_id=job_id)

        # Defer sending the task until transaction has been committed
        hook = _SendTask(s)
        transaction.get().addAfterCommitHook(hook)

        return job_id

    # def wait(self, job_id):
    #     return self.getJob(job_id).wait()

    def update(self, job_id, **kwargs):
        log.debug("Updating job %s with %s", job_id, kwargs)
        jobrecord = self.getJob(job_id)
        jobrecord.update(kwargs)
        # self.getCatalog().catalog_object(jobrecord)

    def getJob(self, jobid):
        """
        Return a L{JobRecord} object that matches the id specified.

        @param jobid: id of the L{JobRecord}.
        @type jobid: str
        @return: A matching L{JobRecord} object,
            or raises a NoSuchJobException if none is found
        @rtype: L{JobRecord}, None
        """
        if not jobid:
            raise NoSuchJobException(jobid)
        try:
            return self._getOb(jobid)
        except AttributeError:
            raise NoSuchJobException(jobid)

    def deleteJob(self, jobid):
        job = self.getJob(jobid)
        if not job.isFinished():
            job.abort()
        # Clean up the log file
        if getattr(job, "logfile", None) is not None:
            try:
                os.remove(job.logfile)
            except (OSError, IOError):
                # Did our best!
                pass
        # self.getCatalog().uncatalog_object("/".join(job.getPhysicalPath()))
        return self._delObject(jobid)

    def _getByStatus(self, statuses, jobtype=None):
        def _normalizeJobType(typ):
            if typ is not None and isinstance(typ, type):
                if hasattr(typ, "getJobType"):
                    return typ.getJobType()
                else:
                    return typ.__name__
            return typ

        # build additional query qualifiers based on named args
        query = {}
        if jobtype is not None:
            query["type"] = _normalizeJobType(jobtype)

        # for b in self.getCatalog()(status=list(statuses), **query):
        #     yield b.getObject()

    def getUnfinishedJobs(self, type_=None):
        """
        Return JobRecord objects that have not yet completed, including those
        that have not yet started.

        @return: All jobs in the requested state.
        @rtype: generator
        """
        return self._getByStatus(states.UNREADY_STATES, type_)

    def getRunningJobs(self, type_=None):
        """
        Return JobRecord objects that have started but not finished.

        @return: All jobs in the requested state.
        @rtype: generator
        """
        return self._getByStatus((states.STARTED, states.RETRY), type_)

    def getPendingJobs(self, type_=None):
        """
        Return JobRecord objects that have not yet started.

        @return: All jobs in the requested state.
        @rtype: generator
        """
        return self._getByStatus((states.RECEIVED, states.PENDING), type_)

    def getFinishedJobs(self, type_=None):
        """
        Return JobRecord objects that have finished.

        @return: All jobs in the requested state.
        @rtype: generator
        """
        return self._getByStatus(states.READY_STATES, type_)

    def getAllJobs(self, type_=None):
        """
        Return all .

        @return: All jobs in the requested state.
        @rtype: generator
        """
        return self._getByStatus(states.ALL_STATES, type_)

    @security.protected(ZEN_MANAGE_DMD)
    def deleteUntil(self, untiltime):
        """
        Delete all jobs older than untiltime.
        """
        for b in self.getCatalog()()[:]:
            try:
                ob = b.getObject()
                if ob.finished is not None and ob.finished < untiltime:
                    self.deleteJob(ob.getId())
                elif ob.status == states.ABORTED and (
                    ob.started is None or ob.started < untiltime
                ):
                    self.deleteJob(ob.getId())
            except ConflictError:
                pass

    @security.protected(ZEN_MANAGE_DMD)
    def clearJobs(self):
        """
        Clear out all finished jobs.
        """
        for b in self.getCatalog()():
            self.deleteJob(b.getObject().getId())

    @security.protected(ZEN_MANAGE_DMD)
    def killRunning(self):
        """
        Abort running jobs.
        """
        for job in self.getUnfinishedJobs():
            job.abort()

    @security.protected(ZEN_MANAGE_DMD)
    def pruneOldJobs(self):
        if datetime.now() - self.lastPruneTime > timedelta(
            hours=1
        ) and datetime.now() - self.lastPruneJobAddTime > timedelta(hours=1):
            self.lastPruneJobAddTime = datetime.now()
            self._addJob(
                PruneJob,
                kwargs=dict(untiltime=datetime.now() - timedelta(weeks=1)),
            )


class _SendTask(object):
    """Dispatches the Celery task when invoked
    """

    def __init__(self, signature):
        self.__s = signature

    def __call__(self, status, **kw):
        log.debug("Commit hook status: %s args: %s", status, kw)
        if status:
            self.__s.apply_async()


class JobLogDownload(BrowserView):
    def __call__(self):
        response = self.request.response
        try:
            jobid = self.request.get("job")
            jobrecord = self.context.JobManager.getJob(jobid)
            logfile = jobrecord.logfile
        except (KeyError, AttributeError, NoSuchJobException):
            response.setStatus(404)
        else:
            response.setHeader("Content-Type", "text/plain")
            response.setHeader(
                "Content-Disposition",
                "attachment;filename=%s" % os.path.basename(logfile),
            )
            with open(logfile, "r") as f:
                return f.read()
