##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import ZODB.config

from AccessControl.SecurityManagement import (
    getSecurityManager, newSecurityManager, noSecurityManager
)
from celery import Task
from celery.worker.request import Request
from celery.utils.log import get_task_logger
from ZPublisher.HTTPRequest import HTTPRequest
from ZPublisher.HTTPResponse import HTTPResponse
from ZPublisher.BaseRequest import RequestContainer

from Products.ZenUtils.Utils import getObjByPath


class ZenRequest(Request):

    pass


class ZenTask(Task):

    Request = ZenRequest
    abstract = True
    _db = None

    def apply_async(self, *args, **kw):
        # Note: this method is invoked on the client side.
        userid = getSecurityManager().getUser().getId()
        kw.setdefault("headers", {})["userid"] = userid
        return super(ZenTask, self).apply_async(*args, **kw)

    @property
    def db(self):
        if self._db is None:
            print("Initializing ZODB object")
            self._db = ZODB.config.databaseFromURL(
                "file:///opt/zenoss/etc/zodb.conf"
            )
        return self._db

    def __call__(self, *args, **kwargs):
        log = get_task_logger("zentask")
        log.error(
            "request.userid: %s",
            self.request.userid
            if hasattr(self.request, "userid") else "<not found>"
        )
        try:
            log.error("Setting up a dmd instance")
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
            log.error("cleaning up")
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
