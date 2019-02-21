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
import Queue
import signal
import sys
import time

from threading import Thread

import transaction

from AccessControl.SecurityManagement import (
    newSecurityManager, noSecurityManager
)
from Products.CMFCore.utils import getToolByName
from ZODB.transact import transact

from Products.ZenUtils.Utils import InterruptableThread

from .. import states
from ..exceptions import NoSuchJobException, JobAborted
from .job import Job


class Abortable(Job):
    """
    Base class for jobs.
    """

    _runner_thread = None
    _aborter_thread = None
    _result_queue = Queue.Queue()
    _log = None
    _aborted_tasks = set()
    acks_late = True
    _origsigtermhandler = None


    def run(self, *args, **kwargs):
        job_id = self.request.id
        self.log.info("Job %s (%s) received", job_id, self.name)

        self._aborter_thread = InterruptableThread(
                target=self._check_aborted, args=(job_id,)
            )
        # Forward the request to the thread because the self.request
        # property is a thread-local value.
        self._runner_thread = InterruptableThread(
                target=self._do_run, args=(self.request,),
                kwargs={'args': args, 'kwargs': kwargs}
            )

        try:
            # Install a SIGTERM handler so that the 'runner_thread' can be
            # interrupted/aborted when the TERM signal is received.
            self._origsigtermhandler = signal.signal(
                    signal.SIGTERM, self._sigtermhandler
                )

            self._runner_thread.start()
            self._aborter_thread.start()

            # A blocking join() call also blocks the thread from calling
            # signal handlers, so use a timeout join and loop until the
            # thread exits to allow the thread an opportunity to call
            # signal handlers.
            self.log.debug("Monitoring _runner_thread existence")
            while self._runner_thread.is_alive():
                self._runner_thread.join(0.01)
            self.log.debug("_runner_thread has exited")

            result = self._result_queue.get_nowait()
            if isinstance(result, Exception):
                cls, instance, tb = result.exc_info[0:3]
                if not isinstance(result, JobAborted):
                    self.log.error("Job %s failed with an exception" % job_id)
                    self.log.error(tb)
                links = []
                if self.request.callbacks:
                    for callback in self.request.callbacks:
                        links.extend(callback.flatten_links())
                for link in links:
                    link.type.update_state(
                        task_id=link.options['task_id'],
                        state=states.ABORTED
                    )
                if links:
                    self.log.info(
                        "Dependent job(s) %s aborted",
                        ', '.join(link.options['task_id'] for link in links)
                    )
                raise cls, instance, tb

            return result
        except Queue.Empty:
            return None
        finally:
            # Remove our signal handler and re-install the original handler
            if signal.getsignal(signal.SIGTERM) == self._sigtermhandler:
                signal.signal(signal.SIGTERM, self._origsigtermhandler)
            # Kill the aborter
            try:
                self._aborter_thread.kill()
                self._aborter_thread.join(0.5)
            except ValueError:
                pass
            # Clean up the logger
            try:
                del self._log.logger.manager.loggerDict[self.request.id]
            except (AttributeError, KeyError):
                pass
            for handler in self._log.handlers:
                handler.close()
            self._log = None

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        # Because JobAborted is an exception, celery will change the state to
        # FAILURE once the task completes. Since we want it to remain ABORTED,
        # we'll set it back here.
        if isinstance(exc, JobAborted):
            self.update_state(state=states.ABORTED)

    def _sigtermhandler(self, signum, frame):
        self.log.debug("%s received signal %s", self, signum)
        # Interrupt the runner_thread.
        self._runner_thread.interrupt(JobAborted)
        # Wait for the runner_thread to exit.
        while self._runner_thread.is_alive():
            time.sleep(0.01)
        # Install the original SIGTERM handler
        signal.signal(signal.SIGTERM, self._origsigtermhandler)
        # Send this process a SIGTERM signal
        os.kill(os.getpid(), signal.SIGTERM)


class _CheckAbortThread(Thread):

    def __init__(self, jobid, backend, worker):
        """
        """
        self.__jobid = jobid
        self.__backend = backend
        self.__worker = worker
        super(_CheckAbortThread, self).__init__(name="AbortChecker")

    def run(self):
        while True:
            try:
                status = self.__backend.get_status(self.__jobid)
            except NoSuchJobException:
                status = states.ABORTED
            if status == states.ABORTED:
                self.__worker.interrupt(JobAborted)
                break
            time.sleep(0.25)


class _WorkerThread(InterruptableThread):

    def __init__(self, job, request, args=None, kwargs=None):
        self.__job = job
        self.__request = request
        self.__args = args
        self.__kwargs = kwargs
        self.__job.request = request
        super(_CheckAbortThread, self).__init__(name="JobRunner")

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
