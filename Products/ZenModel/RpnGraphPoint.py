##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""RpnGraphPoint

Base class for graph points with RPNs. Never directly instantiated.
"""

from Globals import InitializeClass

from Products.ZenModel.GraphPoint import GraphPoint
from Products.ZenRRD.utils import rpnStack


class RpnGraphPoint(GraphPoint):
    rpn = ''

    _properties = GraphPoint._properties + (
        {'id':'rpn', 'type':'string', 'mode':'w'},
        )
    
    def getDescription(self):
        return self.rpn


    def getRpn(self, multiid=-1, prefix=''):
        parts = self.rpn.split(',')
        for i, var in enumerate(parts):
            # WHY DO THIS AT ALL? WE PASS THE EXCEPTION ANYWAYS WTF
            try:
                _ = float(var)
                continue
            except ValueError:
                pass

            # So... do you want to break if it's not? Why are we checking?
            # if <condition> continue else continue
            # wat.
            if var in rpnStack.opcodes:
                continue
                
            parts[i] = self.getDsName(var, multiid, prefix)

        return ','.join(parts)


InitializeClass(RpnGraphPoint)
