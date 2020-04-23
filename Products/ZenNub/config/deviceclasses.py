##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import yaml


# This file is built by update_zenpacks.py and includes all of the zenpack-
# defined device classes, monitoring templates, etc.
DEVICECLASS_YAML = "/opt/zenoss/etc/nub/system/deviceclasses.yaml"
MONITORINGTEMPLATE_YAML = "/opt/zenoss/etc/nub/system/monitoringtemplates.yaml"

def load_yaml():
    return (
        yaml.load(file(DEVICECLASS_YAML, 'r')),
        yaml.load(file(MONITORINGTEMPLATE_YAML, 'r')),
    )

