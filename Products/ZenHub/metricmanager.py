##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import os

from metrology import Metrology, registry

import Globals  # required to import zenoss Products

from Products.ZenUtils.Utils import unused
from Products.ZenUtils.MetricReporter import TwistedMetricReporter
from Products.ZenUtils.DaemonStats import DaemonStats
from Products.ZenUtils.metricwriter import (
    ThresholdNotifier,
    DerivativeTracker,
    MetricWriter,
    FilteredMetricWriter,
    AggregateMetricWriter,
)
from Products.ZenModel.BuiltInDS import BuiltInDS

from .metricpublisher.publisher import (
    RedisListPublisher,
    HttpPostPublisher
)

unused(Globals)


class MetricManager(object):
    '''General interface for storing and reporting metrics
    metric publisher: publishes metrics to an external system (redis, http)
    metric writer: drives metric pulisher(s), calling their .put method
    metric reporter: once its .start method is called,
        periodically calls writer.write_metric, to publish stored metrics
    '''

    def __init__(self, reporter, stats):
        """Initializes a MetricManager instance.

        @param reporter Publishes metrics periodically
        @param stats Used by reportStats to report specific metrics
        """
        self._reporter = reporter
        self._stats = stats
        self._counters = _Counters()

    def start(self):
        """Start periodic metric publishing.
        """
        self._reporter.start()

    def stop(self):
        """Stop periodic metric publishing.
        """
        self._reporter.stop()

    @property
    def counters(self):
        """Provides indexed access to counter metrics.
        """
        return self._counters

    gauge = Metrology.gauge
    counter = Metrology.counter
    meter = Metrology.meter
    derive = Metrology.derive
    timer = Metrology.timer

    def reportStats(self, metrics):
        """Report the specific metrics.

        The metrics parameter is expected to be a list of tuples containing
        three elements.  The tuple elements are:

            ("name-of-metric", "type-of-metric", value)

        Acceptable type-of-metric are "counter", "gauge", and "derive".
        """
        for name, mtype, value in metrics:
            method = getattr(self._stats, mtype, None)
            if method is None:
                raise ValueError("Unknown metric type: %s" % mtype)
            method(name, value)


def _internal_metric_filter(metric, value, timestamp, tags):
    return tags and tags.get("internal", False)


def buildMetricWriter():
    """Builds a suitable metric writer for ZenHub.
    """
    writer = MetricWriter(RedisListPublisher())

    cc = os.environ.get("CONTROLPLANE", "0") == "1"
    internal_url = os.environ.get("CONTROLPLANE_CONSUMER_URL", None)
    if cc and internal_url:
        username = os.environ.get("CONTROLPLANE_CONSUMER_USERNAME", "")
        password = os.environ.get("CONTROLPLANE_CONSUMER_PASSWORD", "")
        http_pub = HttpPostPublisher(username, password, internal_url)
        internal_writer = FilteredMetricWriter(
            http_pub, _internal_metric_filter
        )
        writer = AggregateMetricWriter([writer, internal_writer])

    return writer


def buildMetricReporter(writer, tags):
    """Builds a Twisted compatible metric reporter.
    """
    return TwistedMetricReporter(metricWriter=writer, tags=tags)


def buildStatsReporter(writer, hub_config, send_event):
    """Builds a DaemonStats object suitable for ZenHub.
    """
    rrd_stats = DaemonStats()
    thresholds = hub_config.getThresholdInstances(BuiltInDS.sourcetype)
    threshold_notifier = ThresholdNotifier(send_event, thresholds)
    derivative_tracker = DerivativeTracker()

    rrd_stats.config(
        'zenhub',
        hub_config.id,
        writer,
        threshold_notifier,
        derivative_tracker
    )

    return rrd_stats


class _Counters(object):
    """Simple wrapper for indexed retrieval of Metrology Counter instruments.
    """

    def __init__(self):
        self.__names = set([])

    def __getitem__(self, name):
        self.__names.add(name)
        return Counter(Metrology.counter(name))

    def items(self):
        return [
            (name, metric.count)
            for name, metric in registry
            if name in self.__names
        ]


class Counter(object):
    """Wraps a metrology.instruments.counter.Counter object to add the
    += and -= operators as aliases for the increment and decrement methods.
    """

    def __init__(self, counter):
        self._counter = counter
        # Attach method names
        self.clear = self._counter.clear
        self.increment = self._counter.increment
        self.decrement = self._counter.decrement

    def __iadd__(self, value):
        self._counter.increment(value)

    def __isub__(self, value):
        self._counter.decrement(value)

    @property
    def count(self):
        return self._counter.count
