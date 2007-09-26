###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import os, sys
if __name__ == '__main__':
  execfile(os.path.join(sys.path[0], 'framework.py'))

import transaction

from Products.ZenRelations.Exceptions import *
from Products.ZenRelations.tests.TestSchema import *
from Products.ZenTestCase.BaseTestCase import standard_permissions

from ZenRelationsBaseTest import ZenRelationsBaseTest

class FullZopeTestCases(ZenRelationsBaseTest):

    
    def afterSetUp(self):
        """setup schema manager and add needed permissions"""
        self.setRoles(['Manager'])
        perms = ["Add Relationship Managers","Delete objects","Copy or Move",]
        perms.extend(standard_permissions)
        self.setPermissions(perms)
        self.dataroot = create(self.folder, DataRoot, "dataroot")
        create(self.dataroot, DataRoot, "subfolder")


    def testCutPasteRM(self):
        """test cut and past of a RM make sure primarypath is set properly"""
        dev = build(self.dataroot, Device, "dev")
        transaction.savepoint()
        cookie = self.dataroot.manage_cutObjects( ids=('dev',) )
        self.dataroot.subfolder.manage_pasteObjects( cookie )
        self.failIf(self.dataroot._getOb('dev', False))
        self.failUnless(self.dataroot.subfolder._getOb('dev'))
        self.failUnless(self.dataroot.subfolder.getPhysicalPath() ==
                        dev.getPrimaryPath()[:-1])


    def testCutPasteRM2(self):
        """add contained relationship to cut/paste test"""
        dev = build(self.dataroot, Device, "dev")
        eth0 = create(dev.interfaces, IpInterface, "eth0")
        transaction.savepoint()
        cookie = self.dataroot.manage_cutObjects( ids=('dev',) )
        self.dataroot.subfolder.manage_pasteObjects( cookie )
        self.failIf(self.dataroot._getOb('dev', False))
        self.failUnless(self.dataroot.subfolder._getOb('dev'))
        self.failUnless(
            self.dataroot.subfolder.getPhysicalPath() ==
                dev.getPrimaryPath()[:-1])
        self.failUnless(eth0.getPrimaryUrlPath().find(
                dev.getPrimaryUrlPath()) == 0)


    def testdelObjectRMwRel(self):
        """delete an RM that has many relationships on it"""
        dev = build(self.dataroot, Server, "dev")
        loc = build(self.dataroot, Location, "loc")
        jim = build(self.dataroot, Admin, "jim")
        group = build(self.dataroot, Group, "group")
        dev.admin.addRelation(jim)
        dev.groups.addRelation(group)
        dev.location.addRelation(loc)
        self.dataroot._delObject("dev")
        self.failIf(self.dataroot._getOb('dev', False))


    def testCutPasteRMwRel(self):
        """cut and paste with relationships make sure they persist and
        that their keys are updated properly"""
        dev = build(self.dataroot, Server, "dev")
        loc = build(self.dataroot, Location, "loc")
        jim = build(self.dataroot, Admin, "jim")
        group = build(self.dataroot, Group, "group")
        dev.admin.addRelation(jim)
        dev.groups.addRelation(group)
        dev.location.addRelation(loc)
        transaction.savepoint()
        cookie = self.dataroot.manage_cutObjects( ids=('dev',) )
        self.dataroot.subfolder.manage_pasteObjects( cookie )
        self.failIf(self.dataroot._getOb('dev', False))
        self.failUnless(self.dataroot.subfolder._getOb('dev'))
        self.failUnless(dev in group.devices())
        self.failUnless(dev.admin() == jim)
        self.failUnless(dev.location() == loc)
        self.failUnless(loc.devices.hasobject(dev))
        self.failUnless(group.devices.hasobject(dev))


    def testCopyPasteRMPP(self):
        """test that primary path gets set correctly after copy and paste"""
        dev = build(self.dataroot, Device, "dev")
        transaction.savepoint()
        cookie = self.dataroot.manage_copyObjects(ids=('dev',))
        self.dataroot.subfolder.manage_pasteObjects( cookie )
        self.failUnless(self.dataroot.subfolder._getOb('dev'))
        copy = self.dataroot.subfolder._getOb("dev")
        self.failUnless(self.dataroot.subfolder.getPhysicalPath() ==
            copy.getPrimaryPath()[:-1])


    def testCopyPasteRMSamePath(self):
        """Copy/Paste RM in same folder as original"""
        dev = build(self.dataroot, Device, "dev")
        transaction.savepoint()
        cookie = self.dataroot.manage_copyObjects(ids=('dev',))
        self.dataroot.manage_pasteObjects( cookie )
        self.failUnless(self.dataroot._getOb('dev'))
        self.failUnless(self.dataroot._getOb('copy_of_dev'))


    def testCopyPasteProperties(self):
        """test that Properties are copied correctly"""
        dev = build(self.dataroot, Device, "dev")
        dev.pingStatus = 3
        transaction.savepoint()
        cookie = self.dataroot.manage_copyObjects(ids=('dev',))
        self.dataroot.manage_pasteObjects( cookie )
        self.failUnless(self.dataroot.copy_of_dev._getOb('pingStatus'))
        copy = self.dataroot._getOb("copy_of_dev")
        self.failUnless(dev.pingStatus == copy.pingStatus)
        self.failUnless(dev.pingStatus == 3)
        

    def testCopyPasteRMOneToOne(self):
        """Copy/paste to check RM with OneToOne relationship"""
        dev = build(self.dataroot, Server, "dev")
        jim = build(self.dataroot, Admin, "jim")
        dev.admin.addRelation(jim)
        transaction.savepoint()
        cookie = self.dataroot.manage_copyObjects(ids=('dev',))
        self.dataroot.subfolder.manage_pasteObjects( cookie )
        copy = self.dataroot.subfolder._getOb("dev")
        self.failUnless(dev.admin() == jim)
        self.failUnless(copy.admin() == None)


    def testLinkToMany(self):
        """link on to one side of a one to many relationship"""
        dev = create(self.dataroot, Device, "dev")
        anna = create(self.dataroot, Location, "anna")
        transaction.savepoint()
        cookie = self.dataroot.manage_copyObjects(ids=("anna",))
        self.failUnless(cookie)
        self.dataroot.dev.manage_linkObjects(ids=("location",),
            cb_copy_data=cookie)
        self.failUnless(dev in anna.devices())
        self.failUnless(dev.location() == anna)


    def testLinkToMany2(self):
        """link on to many side of a one to many relationship"""
        dev = create(self.dataroot, Device, "dev")
        anna = create(self.dataroot, Location, "anna")
        transaction.savepoint()
        cookie = self.dataroot.manage_copyObjects(ids=("dev",))
        self.failUnless(cookie)
        self.dataroot.anna.manage_linkObjects(ids=("devices",),
            cb_copy_data=cookie)
        self.failUnless(dev in anna.devices())
        self.failUnless(dev.location() == anna)


    def testLinkObjectsUI(self):
        """Test linking objects using the UI code, ids are lists"""
        dev = build(self.dataroot, Server, "dev")
        jim = build(self.dataroot, Admin, "jim")
        transaction.savepoint()
        cookie = self.dataroot.manage_copyObjects(ids=('jim',))
        self.failUnless(cookie)
        self.dataroot.dev.manage_linkObjects(ids="admin",
            cb_copy_data=cookie)
        self.failUnless(jim.server() == dev)
        self.failUnless(dev.admin() == jim)


    def testLinkObjectsUI2(self):
        """Test linking objects using the UI code, ids are strings"""
        dev = build(self.dataroot, Server, "dev")
        jim = build(self.dataroot, Admin, "jim")
        transaction.savepoint()
        cookie = self.dataroot.manage_copyObjects(ids='jim')
        self.failUnless(cookie)
        self.dataroot.dev.manage_linkObjects(ids="admin",
            cb_copy_data=cookie)
        self.failUnless(jim.server() == dev)
        self.failUnless(dev.admin() == jim)


    def testLinkObjectsUI3(self):
        """Test linking objects using the UI code, fail too many ids"""
        dev = build(self.dataroot, Server, "dev")
        jim = build(self.dataroot, Admin, "jim")
        transaction.savepoint()
        cookie = self.dataroot.manage_copyObjects(ids='jim')
        self.failUnless(cookie)
        self.failUnlessRaises(ZenRelationsError,
            self.dataroot.dev.manage_linkObjects,
            ids=("admin", "joe"), cb_copy_data=cookie)


    def test_setObjectOneToManyCont(self):
        """Place object into ToManyCont with _setObject"""
        dev = build(self.dataroot, Device, "dev")
        eth0 = create(self.dataroot, IpInterface, "eth0")
        dev.interfaces._setObject("eth0", eth0)
        self.failUnless(dev.interfaces._getOb("eth0") == eth0)
        self.failUnless("interfaces" in 
            dev.interfaces.eth0.getPrimaryPath())


    def testCopyPasteRMOneToMany(self):
        """Copy/paste to check RM with OneToMany relationship"""
        dev = build(self.dataroot, Device, "dev")
        anna = build(self.dataroot, Location, "anna")
        dev.location.addRelation(anna)
        transaction.savepoint()
        cookie = self.dataroot.manage_copyObjects(ids=('dev',))
        self.dataroot.subfolder.manage_pasteObjects( cookie )
        copy = self.dataroot.subfolder._getOb("dev")
        self.failUnless(copy.location() == anna)
        self.failUnless(dev.location() == anna)
        self.failUnless(len(anna.devices()) == 2)


    def testCopyPasteRMManyToMany(self):
        """Copy/paste to check RM with ManyToMany relationship"""
        dev = build(self.dataroot, Device, "dev")
        group = build(self.dataroot, Group, "group")
        dev.groups.addRelation(group)
        transaction.savepoint()
        cookie = self.dataroot.manage_copyObjects(ids=('dev',))
        self.dataroot.subfolder.manage_pasteObjects( cookie )
        copy = self.dataroot.subfolder._getOb("dev")
        self.failUnless(group in copy.groups())
        self.failUnless(group in dev.groups())
        self.failUnless(dev in group.devices())
        self.failUnless(copy in group.devices())


    def testRenameRMOneToOne(self):
        """Renameing RM that has a OneToOne relationship"""
        dev = build(self.dataroot, Server, "dev")
        jim = build(self.dataroot, Admin, "jim")
        dev.admin.addRelation(jim)
        transaction.savepoint()
        self.dataroot.manage_renameObject("dev", "newdev")
        self.failUnless(self.dataroot._getOb("newdev"))
        self.failUnless(dev.admin.hasobject(jim))
        self.failUnless(jim.server.hasobject(dev))


    def testCopyPasteRMOneToManyCont(self):
        """Copy/paste to check RM with OneToManyCont subobject"""
        dev = build(self.dataroot, Device, "dev")
        eth0 = create(dev.interfaces, IpInterface, "eth0")
        transaction.savepoint()
        self.dataroot.manage_renameObject("dev", "newdev")
        self.failUnless(self.dataroot._getOb("newdev"))
        self.failUnless(self.dataroot.getPhysicalPath() ==
            dev.getPrimaryPath()[:-1])
        self.failUnless(dev.getPrimaryPath() ==
            eth0.getPrimaryPath()[:-2])
        self.failUnless(eth0.device() == dev)


    def testRenameOneToMany(self):
        """Renaming RM that has a OneToMany relationship"""
        dev = build(self.dataroot, Device, "dev")
        anna = build(self.dataroot, Location, "anna")
        dev.location.addRelation(anna)
        self.failUnless(dev.location() == anna)
        transaction.savepoint()
        self.dataroot.manage_renameObject("dev", "newdev")
        self.failUnless(self.dataroot._getOb("newdev"))
        self.failUnless(anna.devices.hasobject(dev))
        self.failUnless(dev.location() == anna)


    def testCopyPasteRMManyToMany(self):
        """Copy/paste to check RM with ManyToMany relationship"""
        dev = build(self.dataroot, Device, "dev")
        group = build(self.dataroot, Group, "group")
        dev.groups.addRelation(group)
        transaction.savepoint()
        self.dataroot.manage_renameObject("dev", "newdev")
        self.failUnless(self.dataroot._getOb("newdev"))
        self.failUnless(group.devices.hasobject(dev))
        self.failUnless(dev.groups.hasobject(group))

    
    def testCopyPasteToFromOneToManyLink(self):
        """Copy/Paste to form a one to many link between device and location"""
        dev = build(self.dataroot, Device, "dev")
        loc = build(self.dataroot, Location, "loc")
        transaction.savepoint()
        cookie = self.dataroot.manage_copyObjects(ids=('dev',))
        self.dataroot.loc.devices.manage_pasteObjects(cookie )
        self.failUnless(dev.location() == loc)
        self.failUnless(dev in loc.devices())


# this doesn't work because there is no factory,product,etc for IpInterface
#     def testCutPasteIntoOneToManyCont(self):
#         """Cut/Paste into one to many cont between device and interface"""
#         dev = build(self.dataroot, Device, "dev")
#         eth0 = build(self.dataroot, IpInterface, "eth0")
#         cookie = self.dataroot.manage_cutObjects(ids=('eth0',))
#         self.dataroot.dev.interfaces.manage_pasteObjects(cookie)
#         self.failUnless(eth0 in dev.interfaces())
#         self.failUnless(eth0.device() == dev)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(FullZopeTestCases))
    return suite


if __name__ == '__main__':
    framework()
