##############################################################################
#
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import sys
import pkg_resources


def _get_zenoss_pkg():
    pkg = next((
        dist
        for path in sys.path
        for dist in pkg_resources.find_distributions(path)
        if dist.project_name == "Zenoss"
    ), None)
    return pkg.version if pkg else "0.0.0"


VERSION = _get_zenoss_pkg()
BUILD_NUMBER = "DEV"
