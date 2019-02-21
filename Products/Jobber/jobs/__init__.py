##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

__all__ = (
    "Job",
    "SubJob",
    "FacadeMethodJob",
    "PruneJob",
    "DeviceSetLocalRolesJob",
    "SubprocessJob",
)

from .job import Job, SubJob
from .facade import FacadeMethodJob
from .prune import PruneJob
from .roles import DeviceSetLocalRolesJob
from .subprocess import SubprocessJob


class DeviceListJob(Job):

    @classmethod
    def getJobDescription(cls, *args, **kwargs):
        return "some description"

    def _run(self, *args, **kw):
        deviceNames = [
            device.id for device in self.dmd.Devices.Server.Linux.devices()
        ]
        # attrs = ", ".join(dir(self))
        self.log.info("device names: %s", deviceNames)
        return deviceNames
