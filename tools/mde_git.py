"""Deprecated compatibility alias for `mde.git.repository`."""

from importlib import import_module
import sys

_target = import_module("mde.git.repository")
sys.modules[__name__] = _target
