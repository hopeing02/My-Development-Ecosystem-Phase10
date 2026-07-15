"""Deprecated compatibility alias for `mde.logging.logger`."""
from importlib import import_module
import sys
_target = import_module("mde.logging.logger")
sys.modules[__name__] = _target
