"""Deprecated compatibility alias for `mde.commands.apply`."""
from importlib import import_module
import sys
_target = import_module("mde.commands.apply")
sys.modules[__name__] = _target
