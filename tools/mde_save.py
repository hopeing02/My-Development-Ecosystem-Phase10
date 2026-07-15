"""Deprecated compatibility alias for `mde.commands.save`."""
from importlib import import_module
import sys
_target = import_module("mde.commands.save")
sys.modules[__name__] = _target
