#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

from CollectorPlugin import CommandPlugin

class netstat_an(CommandPlugin):
    """
    Collect running ip services using netstat -an on a linux box.
    """
    maptype = "IpServicesMap" 
    command = 'netstat -an | grep 0.0.0.0:*'
    compname = "os"
    relname = "ipservices"
    modname = "Products.ZenModel.IpService"


    def condition(self, device, log):
        osver = device.os.getProductName()
        return osver.find("Linux") > -1


    def process(self, device, results, log):
        log.info('Collecting Ip Services for device %s' % device.id)
        rm = self.relMap()
        rlines = results.split("\n")
        services = {}
        # normalize on address 0.0.0.0 means all addresses
        for line in rlines:
            aline = line.split()
            if len(aline) < 5: continue
            try:
                proto = aline[0]
                addr, port = aline[3].split(":")
                if int(port) > 1024: continue #FIXME 
                if addr == "0.0.0.0" or not services.has_key(port):
                    services[port] = (addr, proto)
            except ValueError:
                log.exception("failed to parse ipservice information")
        for port, value in services.items():
            addr, proto = value
            if proto == "raw": continue
            om = self.objectMap()
            om.id = "-".join((addr, proto, port))
            om.ipaddress = addr
            om.setPort = int(port)
            om.setProtocol = proto
            om.discoveryAgent = self.name()
            rm.append(om)
        return rm
