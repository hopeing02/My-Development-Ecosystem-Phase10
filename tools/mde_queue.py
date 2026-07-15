"""Deprecated compatibility alias for `mde.task.queue`."""
from importlib import import_module
import sys
_target = import_module("mde.task.queue")
sys.modules[__name__] = _target
