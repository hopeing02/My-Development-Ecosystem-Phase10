"""Deprecated compatibility alias for `mde.agent.lock`."""

from importlib import import_module
import sys

_target = import_module("mde.agent.lock")
sys.modules[__name__] = _target
