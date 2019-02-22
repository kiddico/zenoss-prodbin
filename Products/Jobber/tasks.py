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
import json
import logging
import redis
import sys
import time

from Products.ZenUtils.Utils import InterruptableThread

from . import states
from .exceptions import JobAborted
from .feature import requires, DMD
from .zenjobs import app


@app.task(bind=True, ignore_result=False)
def job(self, *args, **kw):
    deviceNames = [
        device.id for device in self.dmd.Devices.Server.Linux.devices()
    ]
    # attrs = ", ".join(dir(self))
    log = logging.getLogger("zen.zenjobs.job")
    log.info("device names: %s", deviceNames)
    return deviceNames


@app.task(bind=True, base=requires(DMD), ignore_result=False)
def legacy_job(self, jobclasspath, *args, **kwargs):
    """This task executes legacy Job based tasks.
    """
    moduleName, clsName = jobclasspath.rsplit(".", 1)
    module = importlib.import_module(moduleName)
    cls = getattr(module, clsName)
    job = cls(log=self.log, dmd=self.dmd, request=self.request)
    result = job.run(*args, **kwargs)
    self.log.info("result = %s", result)
    return result


@app.task(bind=True)
def abortable_job(self, jobclasspath, *args, **kwargs):
    """This task executes legacy abortable Job based tasks.
    """
    moduleName, clsName = jobclasspath.rsplit(".", 1)
    module = importlib.import_module(moduleName)
    cls = getattr(module, clsName)
    job = cls(log=self.log, dmd=self.dmd, request=self.request)

    try:
        rc = redis.Redis(host="localhost", db=1)
        rc.ping()
        runner = _JobRunner(job, args=args, kwargs=kwargs)
        aborter = _JobAborter(self.request.id, rc, runner)
        aborter.start()
        runner.start()

        while runner.is_alive():
            time.sleep(0.1)
        runner.join()
        if aborter.is_alive():
            aborter.kill()
        aborter.join()
    finally:
        rc.shutdown()


class _JobAborter(InterruptableThread):

    def __init__(self, jobid, client, runner):
        """
        """
        self.__jobid = jobid
        self.__client = client
        self.__runner = runner
        super(_JobAborter, self).__init__(name="JobAborter")

    def run(self):
        while True:
            try:
                raw = self.__client.get("zenjobs:job:%s" % self.__jobid)
                if raw is None:
                    continue
                record = json.loads(raw)
                status = record.get("status")
            except Exception:
                status = states.ABORTED
            if status == states.ABORTED:
                self.__runner.interrupt(JobAborted)
                break
            time.sleep(0.1)


class _JobRunner(InterruptableThread):

    def __init__(self, job, request, args=None, kwargs=None):
        self.__job = job
        self.__request = request
        self.__args = args
        self.__kwargs = kwargs
        super(_JobRunner, self).__init__(name="JobRunner")

    def run(self):
        args = self.__args or ()
        kwargs = self.__kwargs or {}
        job_id = self.__request.id

        # Run it!
        self.log.info("Starting job %s (%s)", job_id, self.__job.name)
        try:
            # Make request available to self.request property
            # (because self.request is thread local)
            # self.__job.request_stack.push(request)
            try:
                result = self._run(*args, **kwargs)
                self.log.info(
                    "Job %s finished with result %s", job_id, result
                )
                self._result_queue.put(result)
            except JobAborted:
                self.log.warning("Job %s aborted.", job_id)
                # re-raise JobAborted to allow celery to perform job
                # failure and clean-up work.  A monkeypatch has been
                # installed to prevent this exception from being written to
                # the log.
                raise
        except Exception as e:
            e.exc_info = sys.exc_info()
            self._result_queue.put(e)
        # finally:
            # Remove the request
            # self.request_stack.pop()
