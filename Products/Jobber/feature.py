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

from AccessControl.SecurityManagement import (
    newSecurityManager, noSecurityManager
)
from celery import Task
from ZPublisher.HTTPRequest import HTTPRequest
from ZPublisher.HTTPResponse import HTTPResponse
from ZPublisher.BaseRequest import RequestContainer

from Products.ZenUtils.Utils import getObjByPath

from .logger import FormatStringAdapter
from .zenjobs import app, osw


def requires(*features):
    """Dynamically creates and returns a custom Task class based on the
    feature classes given as arguments.
    """
    superclasses = tuple(features) + (Task, object,)
    name = ''.join(t.__name__ for t in features) + "Task"
    basetask = type(name, superclasses, {})
    return basetask


class DMD(object):
    """Feature class that attaches a ZODB dataroot object, named 'dmd',
    to the task instance.
    """

    def __call__(self, *args, **kwargs):
        log = FormatStringAdapter(logging.getLogger("zen.zenjobs.tasks"))
        log.info("[{0.pid}] task_prerun: {1} {2} {3}", osw, self, args, kwargs)
        log.info("DMD: Setting up ZODB session")
        log.info(
            "DMD: request.userid: {}",
            self.request.userid
            if hasattr(self.request, "userid") else "<not found>"
        )
        connection, self.dmd = self.__setup(log)
        try:
            return super(DMD, self).__call__(*args, **kwargs)
        finally:
            self.__teardown(log, connection)

    def __teardown(self, log, connection):
        log.info("DMD: Tearing down ZODB session")
        connection.close()
        del self.dmd
        noSecurityManager()

    def __setup(self, log):
        try:
            connection = app.db.open()
            root = connection.root()
            application = _getContext(root["Application"])
            dataroot = getObjByPath(application, "/zport/dmd")
            _login(dataroot)
            return connection, dataroot
        except Exception as ex:
            log.exception(
                "Failed to setup ZODB for task: ({}) {}", type(ex), ex
            )
            raise


def _getContext(app):
    resp = HTTPResponse(stdout=None)
    env = {
        'SERVER_NAME': 'localhost',
        'SERVER_PORT': '8080',
        'REQUEST_METHOD': 'GET'
    }
    req = HTTPRequest(None, env, resp)
    return app.__of__(RequestContainer(REQUEST=req))


def _login(context, name='admin', userfolder=None):
    """Authenticate user and configure credentials.
    """
    if userfolder is None:
        userfolder = context.getPhysicalRoot().acl_users
    user = userfolder.getUserById(name)
    if user is None:
        return
    if not hasattr(user, 'aq_base'):
        user = user.__of__(userfolder)
    newSecurityManager(None, user)
    return user
