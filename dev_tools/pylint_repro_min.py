# -*- coding: utf-8 -*-
"""Generic optional-value example for inspecting local pylint diagnostics.

Run with the flags documented in dev_tools/README.md. Diagnostic behavior
depends on pylint version; this fixture is not platform parity evidence.
It is a host-side example and must not be bundled into a behavior pack.
"""


class RecordStore(object):
    def __init__(self):
        self.records = []

    def optional_subscript(self):
        latest = None
        for record in self.records:
            if latest is None or record['timestamp'] >= latest['timestamp']:
                latest = record
        return latest

    def separate_comparison_value(self):
        latest = None
        latest_time = None
        for record in self.records:
            timestamp = record['timestamp']
            if latest_time is None or timestamp >= latest_time:
                latest = record
                latest_time = timestamp
        return latest
