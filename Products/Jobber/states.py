##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, unicode_literals

__all__ = (
    "PENDING", "RECEIVED", "STARTED", "SUCCESS", "FAILURE", "ABORTED",
    "REVOKED", "RETRY", "IGNORED", "READY_STATES", "UNREADY_STATES",
    "EXCEPTION_STATES", "PROPAGATE_STATES", "ALL_STATES",
    "precedence", "state",
)

from celery.states import (
    PENDING, RECEIVED, STARTED, SUCCESS, FAILURE,
    REVOKED, RETRY, IGNORED, READY_STATES, UNREADY_STATES,
    EXCEPTION_STATES, PROPAGATE_STATES, precedence, state,
)
from celery.contrib.abortable import ABORTED

ALL_STATES = frozenset({
    PENDING, RECEIVED, STARTED, SUCCESS, FAILURE, RETRY, REVOKED, ABORTED
})
