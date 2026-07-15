"""Deprecated compatibility alias for `mde.task.model`."""
from importlib import import_module
import sys
_target = import_module("mde.task.model")
sys.modules[__name__] = _target
