
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import os
import re
import logging
log = logging.getLogger("zen.migrate")

from Products.ZenUtils.Utils import zenPath

import Migrate
import servicemigration as sm
from servicemigration import InstanceLimits

sm.require("1.1.10")


class FixZminionLogFilters(Migrate.Step):
    """Correct the LogFilters for zminion (ZEN-28077)"""

    version = Migrate.Version(200, 0, 0)

    def cutover(self, dmd):

        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        top = ctx.getTopService()
        log.info("Found top level service: '{0}'".format(top.name))
        if top.name.find("Zenoss") != 0 and top.name.find("UCS-PM") != 0:
            log.info("Top level service name isn't Zenoss or UCS-PM; skipping.")
            return

        services = filter(lambda s: s.name in ["zminion"], ctx.services)
        log.info("Found %d services named 'zminion'." % len(services))

        changed = False
        for service in services:
            servicePath = ctx.getServicePath(service)
            for logConfig in service.logConfigs:
                if logConfig.path == "/opt/zenoss/log/zminion.log":
                    if not logConfig.logTags:
                        log.info("Updating logtag for %s in %s", logConfig.path, servicePath)
                        monitor_tag = sm.logtag.LogTag("monitor", "{{(parent .).Name}}")
                        logConfig.logTags.append(monitor_tag)
                        changed = True

                    if logConfig.filters is None:
                        log.info("Updating logfilter for %s in %s", logConfig.path, servicePath)
                        logConfig.filters = ["glog"]
                        changed = True
                    else:
                        log.info("No updates necesary for the logfilter for %s", servicePath)

        filename = 'Products/ZenModel/migrate/data/glog-6.0.0.conf'
        with open(zenPath(filename)) as filterFile:
            try:
                filterDef = filterFile.read()
            except Exception as e:
                log.error("Error reading {0} logfilter file: {1}".format(filename, e))
                return
            filterName = "glog"
            log.info("Updating log filter named {0}".format(filterName))
            changed = True
            ctx.addLogFilter(filterName, filterDef)


        if changed:
            # Commit our changes.
            ctx.commit()


FixZminionLogFilters()
