from nmigen import *
from nmigen.asserts import *
from nmigen.hdl.ast import *
from nmigen.back import pysim


class EmbeddedThing(object):
    def __init__(self):
        self.thing = Signal(16)

    def ports(self):
        ps = [self.thing]
