##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from inspect import getargspec
from zope.dottedname.resolve import resolve

from ..exceptions import FacadeMethodJobFailed
from .job import Job


class FacadeMethodJob(Job):
    """Execute a method of a Zuul.facades.* facade object.
    """

    @classmethod
    def getJobType(cls):
        return "Python API"

    @classmethod
    def getJobDescription(cls, facadefqdn, method, *args, **kwargs):
        facade = facadefqdn.split(".")[-1]
        return "%s.%s %s" % (facade, method, args[0] if args else "")

    def _run(self, facadefqdn, method, *args, **kwargs):
        # Pass the job log to the facade method so that it can log
        # to the job log.
        kwargs["joblog"] = self.log
        self.args = args
        self.kwargs = kwargs
        facadeclass = resolve(facadefqdn)
        facade = facadeclass(self.dmd)
        bound_method = getattr(facade, method)
        accepted = fun_takes_kwargs(bound_method, kwargs)
        kwargs = dict((k, v) for k, v in kwargs.iteritems() if k in accepted)
        result = bound_method(*args, **kwargs)

        # Expect result = {'success': boolean, 'message': string}
        # Some old facade method jobs return None.
        if result:
            try:
                if not result["success"]:
                    raise FacadeMethodJobFailed
                return result["message"]
            except FacadeMethodJobFailed:
                raise
            except (TypeError, KeyError):
                self.log.error(
                    "The output from job {} is not in the right format.",
                    self.request.id
                )


def fun_takes_kwargs(fun, kwlist=[]):
    # Copied from Celery source
    spec = getattr(fun, 'argspec', getargspec(fun))
    if spec.keywords is not None:
        return kwlist
    return [kw for kw in kwlist if kw in spec.args]
