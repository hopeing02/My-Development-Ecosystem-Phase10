"""Deprecated compatibility alias for `mde.commands.new`."""
from importlib import import_module
import sys
_target = import_module("mde.commands.new")
sys.modules[__name__] = _target
