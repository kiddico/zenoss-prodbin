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
import ZODB.config

from AccessControl.SecurityManagement import (
    getSecurityManager, newSecurityManager, noSecurityManager
)
from celery import Task
from celery.signals import before_task_publish
from celery.worker.request import Request
# from celery.utils.log import get_task_logger
from ZPublisher.HTTPRequest import HTTPRequest
from ZPublisher.HTTPResponse import HTTPResponse
from ZPublisher.BaseRequest import RequestContainer

from Products.ZenUtils.Utils import getObjByPath


@before_task_publish.connect
def attach_userid(headers=None, **kwargs):
    """Adds a 'userid' field to the task's headers.  The value of userid
    is the ID of the user that sent the task.
    """
    # Note: this method is invoked on the client side.
    userid = getSecurityManager().getUser().getId()
    try:
        headers["userid"] = userid
    except TypeError as ex:
        log = logging.getLogger("zen.zenjobs.tasks")
        log.error("No headers for task?: %s", ex)


class ZenRequest(Request):

    pass


class ZenTask(Task):

    Request = ZenRequest
    abstract = True
    _db = None

    @property
    def db(self):
        if self._db is None:
            print("Initializing ZODB object")
            self._db = ZODB.config.databaseFromURL(
                "file:///opt/zenoss/etc/zodb.conf"
            )
        return self._db

    def __call__(self, *args, **kwargs):
        log = logging.getLogger("zen.zenjobs.tasks")
        log.info(
            "request.userid: %s",
            self.request.userid
            if hasattr(self.request, "userid") else "<not found>"
        )
        try:
            log.info("Setting up a dmd instance")
            connection = self.db.open()
            root = connection.root()
            self.app = getContext(root["Application"])
            self.dataroot = getObjByPath(self.app, "/zport/dmd")
            self.dmd = self.dataroot
            login(self.dmd)
            return super(ZenTask, self).__call__(*args, **kwargs)
        except Exception as ex:
            print ex
        finally:
            log.info("cleaning up")
            del self.dmd
            del self.dataroot
            del self.app
            connection.close()
            noSecurityManager()


def getContext(app):
    resp = HTTPResponse(stdout=None)
    env = {
        'SERVER_NAME': 'localhost',
        'SERVER_PORT': '8080',
        'REQUEST_METHOD': 'GET'
    }
    req = HTTPRequest(None, env, resp)
    return app.__of__(RequestContainer(REQUEST=req))


def login(context, name='admin', userfolder=None):
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
