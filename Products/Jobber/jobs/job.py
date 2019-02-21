##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import abc

from Products.ZenUtils.GlobalConfig import getGlobalConfiguration

from ..utils import abstractclassmethod
from ..zenjobs import app

_MARKER = object()


class Job(object):
    """Base class for jobs.
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, *args, **kwargs):
        """Initializes a Job instance.

        @param log {Logger} The task logger
        @param dmd {/zport/dmd} ZODB
        @param request {celery.Request} The Celery request
        """
        self.log = kwargs.pop("log")
        self.dmd = kwargs.pop("dmd")
        self.request = kwargs.pop("request")
        super(Job, self).__init__(*args, **kwargs)

    @abstractclassmethod
    def getJobDescription(cls, *args, **kwargs):
        raise NotImplementedError(
            "Abtract classmethod not implemented: %s.getJobDescription"
            % cls.__name__
        )

    @abc.abstractmethod
    def _run(self, *args, **kw):
        """Subclasses override this method to implement the work of the job.
        """
        raise NotImplementedError(
            "Abtract method not implemented: %s._run"
            % self.__class__.__name__
        )

    @classmethod
    def getJobType(cls):
        return cls.__name__

    @classmethod
    def makeSubJob(cls, args=None, kwargs=None, description=None, **options):
        """Return a SubJob instance that wraps the given job and its arguments
        and options.
        """
        job = app.tasks[cls.name]
        return SubJob(
            job, args=args, kwargs=kwargs,
            description=description, options=options
        )

    @property
    def name(self):
        return type(self).__name__

    def setProperties(self, **properties):
        # deprecated
        pass

    def _get_config(self, key, default=_MARKER):
        sanitized_key = key.replace("-", "_")
        value = getGlobalConfiguration().get(sanitized_key, _MARKER)
        if value is _MARKER:
            raise ValueError("Config option %s is not defined" % key)
        return value

    def run(self, *args, **kwargs):
        job_id = self.request.id
        self.log.info("Job %s (%s) received", job_id, self.name)
        return self._run(*args, **kwargs)


class SubJob(object):
    """
    Container for a job invocation.  Use the Job.makeSubJob method to create
    instances of this class.
    """

    def __init__(
            self, job, args=None, kwargs=None, description=None, options={}):
        """
        Initialize an instance of SubJob.

        The supported options are:
            immutable - {bool} Set True to 'freeze' the job's arguments.
            ignoreresult - {bool} Set True to drop the result of the job.

        @param job {Job} The job instance to execute.
        @param args {sequence} Arguments to pass to the job.
        @param kwargs {dict} Keyword/value arguments to pass to the job.
        @param description {str} Description of job (for JobRecord)
        @options {dict} Options to control the job.
        """
        self.job = job
        self.args = args or ()
        self.kwargs = kwargs or {}
        self.description = description
        self.options = options.copy()
