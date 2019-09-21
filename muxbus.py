from nmigen import *
from nmigen.cli import main
from nmigen.asserts import *


class Muxbus(Elaboratable):
    """Multiplexing bus.

    A bus of a given width, with an output port and a number of input
    ports. A selector signal chooses between the inputs.
    """

    def __init__(self, width, num_ports):
        self.output = Signal(width)
        self.inputs = Signal(width)
