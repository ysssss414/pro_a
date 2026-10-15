"""Compatibility import for the shared read model."""
import sys
from pro_a.read_model import review_schemas as _shared

sys.modules[__name__] = _shared
