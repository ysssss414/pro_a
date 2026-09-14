"""Synthetic acceptance subprocess: exit after canonical commit before file receipt."""
import os
from pathlib import Path
import sys
from pro_a.operational_operator import Operator, OperatorConfig

operator = Operator(OperatorConfig.load(Path(sys.argv[1])))
def crash(point, _):
    if point == 'after_commit': os._exit(73)
operator.execute(sys.argv[2], confirm=sys.argv[2], fault=crash)
