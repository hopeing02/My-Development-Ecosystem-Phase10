"""Deprecated compatibility alias for `mde.agent.runner`."""
from importlib import import_module
import sys
_target = import_module("mde.agent.runner")
sys.modules[__name__] = _target
