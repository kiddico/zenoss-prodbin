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

__doc__='''Migrate

A small framework for data migration.

$Id$
'''

__version__ = "$Revision$"[11:-2]

import Globals
import transaction
from Products.ZenUtils.ZenScriptBase import ZenScriptBase
from Products.ZenUtils.Version import Version as VersionBase
from Products.ZenReports.ReportLoader import ReportLoader
from Products.ZenUtils.Utils import zenPath
from Products.ZenModel.ZVersion import VERSION

import sys
import logging
import operator
from textwrap import wrap
log = logging.getLogger("zen.migrate")

allSteps = []

class MigrationFailed(Exception): pass

class Version(VersionBase):
    def __init__(self, *args, **kw):
        VersionBase.__init__(self, 'Zenoss', *args, **kw)


def cleanup():
    "recursively remove all files ending with .pyc"
    import os
    count = 0
    for p, d, fs in os.walk(zenPath('Products')):
        for f in fs: 
            if f.endswith('.pyc'):
                fullPath = os.path.join(p, f)
                os.remove(fullPath)
                count += 1
    log.debug('removed %d .pyc files from Products' % count)


class Step:
    'A single migration step, to be subclassed for each new change'

    # Every subclass should set this so we know when to run it
    version = -1
    dependencies = None


    def __init__(self):
        "self insert ourselves in the list of all steps"
        allSteps.append(self)

    def __cmp__(self, other):
        result = cmp(self.version, other.version)
        if result:
            return result
        # if we're in the other dependency list, we are "less"
        if self in other.getDependencies():
            return -1
        # if other is in the out dependency list, we are "greater"
        if other in self.getDependencies():
            return 1
        return 0

    def getDependencies(self):
        if not self.dependencies:
            return []
        result = []
        for d in self.dependencies:
            if d is not self:
                result.append(d)
                result.extend(d.getDependencies())
            else:
                log.error("Circular dependency among migration Steps: "
                          "%s is listed as a dependency of %s ",
                          self.name(), d.name())
        return result

    def prepare(self):
        "do anything you must before running the cutover"
        pass

    def cutover(self, dmd):
        "perform changes to the database"
        raise NotImplementedError

    def cleanup(self):
        "remove any intermediate results"
        pass

    def revert(self):
        pass

    def name(self):
        return self.__class__.__name__


class Migration(ZenScriptBase):
    "main driver for migration: walks the steps and performs commit/abort"

    useDatabaseVersion = True

    def __init__(self, noopts=0):
        ZenScriptBase.__init__(self, noopts=noopts, connect=False)
        self.connect()
        self.allSteps = allSteps[:]
        self.allSteps.sort(lambda x,y: cmp(x.name(), y.name()))
        self.allSteps.sort()

    def message(self, msg):
        log.info(msg)

    def _currentVersion(self):
        """
        Return a VersionBase instance representing the version of the database.
        This also does some cleanup of dmd.version in case in is 
        nonexistant, empty or set to a float value.
        """
        if not hasattr(self.dmd, 'version') or not self.dmd.version:
            self.dmd.version = 'Zenoss ' + VERSION
        if type(self.dmd.version) == type(1.0):
            self.dmd.version = "Zenoss 0.%f" % self.dmd.version
        v = VersionBase.parse(self.dmd.version)
        v.name = 'Zenoss'
        return v

    def getEarliestAppropriateStepVersion(self, codeVers=None):
        """
        Return a Version instance that represents the earliest version
        of migrate step appropriate to run with this code base.
        The earliest version is basically the first sprint/alpha release
        for the current minor version.
        codeVers represents the current version of the code.  It exists
        for testing purposes and should usually not be passed in.
        """
        if codeVers is None:
            codeVers = VersionBase.parse('Zenoss %s' % VERSION)
        if codeVers.micro >= 70:
            # We are in a dev/beta release.  Anything back through the start
            # of this dev/beta cycle is appropriate.
            earliestAppropriate = Version(codeVers.major, codeVers.minor, 70)
        elif codeVers.minor > 0:
            # We are in a regular release that is not a  N.0 version.
            # Anything back through the previous dev/beta cycle is
            # appropriate
            earliestAppropriate = Version(codeVers.major, codeVers.minor-1, 70)
        else:
            # This is a X.0.Y release.  This is tough because we don't know
            # what the minor version was for the last release of version X-1.
            # We take the reasonable guess that the last version of X-1 that
            # we see migrate steps for was indeed the last minor release
            # of X-1.
            beforeThis = Version(codeVers.major)
            # self.allSteps is ordered by version, so just look back through
            # all steps for the first one that predates beforeThis.
            for s in reversed(self.allSteps):
                if s.version < beforeThis:
                    lastPrevious = s.version
                    break
            else:
                # We couldn't find any migrate step that predates codeVers.
                # Something is wrong, this should never happen.
                raise MigrationFailed('Unable to determine the appropriate '
                    'migrate script versions.')
            if lastPrevious.micro >= 70:
                earliestAppropriate = Version(lastPrevious.major,
                        lastPrevious.minor, 70)
            else:
                earliestAppropriate = Version(lastPrevious.major,
                        lastPrevious.minor-1, 70)
        return earliestAppropriate


    def determineSteps(self):
        """
        Return a list of steps from self.allSteps that meet the criteria
        for this migrate run
        """
        # Ensure all steps have version numbers
        for step in self.allSteps:
            if step.version == -1:
                raise MigrationFailed("Migration %s does not set "
                                      "the version number" %
                                      step.__class__.__name__)

        # Level was specified
        if self.options.level is not None:
            levelVers = VersionBase.parse('Zenoss ' + self.options.level)
            steps = [s for s in self.allSteps
                        if s.version >= levelVers]
            
        # Step was specified
        elif self.options.steps:
            import re
            def matches(name):
                for step in self.options.steps:
                    if re.match('.*' + step + '.*', name):
                        return True
                return False
            steps = [s for s in self.allSteps if matches(s.name())]

        else:
            currentDbVers = self._currentVersion()
            # The user did not specify steps to be run, so we run the default
            # steps.
            newDbVers = self.allSteps[-1].version
            if currentDbVers == newDbVers:
                # There are no steps newer than the current db version.
                # By default we rerun the steps for the current version.
                # If --newer was specified then we run nothing.
                if self.options.newer:
                    steps = []
                else:
                    steps = [s for s in self.allSteps 
                                if s.version == currentDbVers]
            else:
                # There are steps newer than the current db version.
                # Run the newer steps.
                steps = [s for s in self.allSteps
                            if s.version > currentDbVers]
                
                # Ideally migrate scripts are always run using the version of
                # the code that corresponds to the version in the migrate
                # step.  Problems can arise when executing migrate steps
                # using newer code than that for which they were intended.
                # See #2924
                if not self.options.force:
                    earliestAppropriateVers = \
                            self.getEarliestAppropriateStepVersion()
                    inappropriate = [s for s in steps if
                                        s.version < earliestAppropriateVers]
                    if inappropriate:
                        msg = []
                        msg.append('The following migrate steps were not '
                            'intended to run with the currently installed '
                            'version of the Zenoss code.  The installed '
                            'version is %s.' % VERSION)
                        msg.append(
                            'You can override this warning with the --force '
                            'option.')
                        for step in inappropriate:
                            msg.append('  %s (%s)'
                                        % (step.name(), step.version.short()))
                        self.message('\n'.join(msg))
                        sys.exit(-1)
        return steps


    def migrate(self):
        """
        Determine the correct migrate steps to run and apply them
        """        
        steps = self.determineSteps()
        if steps:
            for m in steps:
                m.prepare()
            currentDbVers = self._currentVersion()
            if steps[-1].version > currentDbVers:
                self.message('Database going to version %s'
                                                % steps[-1].version.long())
            for m in steps:
                self.message('Installing %s (%s)' 
                                % (m.name(), m.version.short()))
                m.cutover(self.dmd)
                if m.version > currentDbVers:
                    self.dmd.version = m.version.long()
            for m in steps:
                m.cleanup()
        cleanup()

        if not self.options.steps:
            self.message('Loading Reports')
            rl = ReportLoader(noopts=True, app=self.app)
            rl.options.force = True
            rl.options.logseverity = self.options.logseverity + 10
            rl.setupLogging()
            rl.loadDatabase()


    def cutover(self):
        '''perform the migration, applying all the new steps,
        recovering on error'''
        if not self.allSteps:
            self.message('There are no migrate scripts.')
            return
        self.backup()
        try:
            self.migrate()
            self.success()
        except Exception, ex:
            self.error("Recovering")
            self.recover()
            raise


    def error(self, msg):
        print >>sys.stderr, msg


    def backup(self):
        pass


    def recover(self):
        transaction.abort()
        steps = self.allSteps[:]
        current = self._currentVersion()
        while steps and steps[0].version < current:
            steps.pop(0)
        for m in steps:
            m.revert()


    def success(self):
        if self.options.commit:
            self.message('committing')
            transaction.commit()
        else:
            self.message('rolling back changes')
            self.recover()
        self.message("Migration successful")


    def parseOptions(self):
        ZenScriptBase.parseOptions(self)
        if self.args:
            if self.args == ['run']:
                sys.stderr.write('Use of "run" is depracated.\n')
            elif self.args == ['help']:
                sys.stderr.write('Use of "help" is depracated,'
                                    'use --help instead.\n')
                self.parser.print_help()
                self.parser.exit()
            elif self.args[0]:
                self.parser.error('Unrecognized option(s): %s\n' %
                    ', '.join(self.args) +
                    'Use --help for list of options.\n')


    def buildOptions(self):
        self.parser.add_option('--step',
                               action='append',
                               dest="steps",
                               help="Run the specified step.  This option "
                                    'can be specified multiple times to run '
                                    'more than on step.')
        # NB: The flag for this setting indicates a false value for the setting.
        self.parser.add_option('--dont-commit',
                               dest="commit",
                               action='store_false',
                               default=True,
                               help="Don't commit changes to the database")
        self.parser.add_option('--list',
                               action='store_true',
                               default=False,
                               dest="list",
                               help="List all the steps")
        self.parser.add_option('--level',
                               dest="level",
                               type='string',
                               default=None,
                               help="Run the steps for the specified level "
                                    ' and above.')
        self.parser.add_option('--newer',
                                dest='newer',
                                action='store_true',
                                default=False,
                                help='Only run steps with versions higher '
                                        'than the current database version.'
                                        'Usually if there are no newer '
                                        'migrate steps the current steps '
                                        'are rerun.')
        self.parser.add_option('--force',
                                dest='force',
                                action='store_true',
                                default=False,
                                help='Force version inappropriate migrate '
                                        'steps to run.  This can happen when '
                                        'trying to skip a minor version '
                                        'when upgrading.')
        ZenScriptBase.buildOptions(self)


    def orderedSteps(self):
        return self.allSteps

    def list(self):
        print ' Ver      Name        Description'
        print '-----+---------------+-----------' + '-'*40
        for s in self.allSteps:
            doc = s.__doc__
            if not doc:
                doc = sys.modules[s.__class__.__module__].__doc__ \
                                                        or 'Not Documented'
                doc.strip()
            indent = ' '*22
            doc = '\n'.join(wrap(doc, width=80,
                                 initial_indent=indent,
                                 subsequent_indent=indent))
            doc = doc.lstrip()
            print "%-8s %-15s %s" % (s.version.short(), s.name(), doc)

    def main(self):
        if self.options.list:
            self.list()
            return
                
        self.cutover()
