from nmigen import *
from nmigen.asserts import *
from nmigen.hdl.ast import *
from nmigen.back import pysim


class EmbeddedThing(object):
    def __init__(self):
        self.thing = Signal(16)

    def ports(self):
        return [self.thing]


class ThingUnderTest(Elaboratable):
    def __init__(self, embedded=None):
        self.input = Signal(16)
        self.output = Signal(16)
        self.embedded = embedded

    def ports(self):
        return [self.input, self.output]

    def elaborate(self, platform):
        m = Module()
        m.submodules.bottom = bottom = BottomModule(embedded=embedded)

        m.d.comb += self.output.eq(self.input + bottom.output)

        return m


class BottomModule(Elaboratable):
    def __init__(self, embedded=None):
        self.output = Signal(16)
        self.embedded = embedded

    def elaborate(self, platform):
        m = Module()

        if self.embedded != None:
            m.d.comb += self.output.eq(1)
            m.d.pos += self.embedded.thing.eq(self.output)
        else:
            m.d.comb += self.output.eq(0)

        return m


if __name__ == "__main__":
    m = Module()

    embedded = EmbeddedThing()
    m.submodules.testmod = testmod = ThingUnderTest(embedded=embedded)

    m.d.comb += testmod.input.eq(0x9876)

    ports = testmod.ports()
    ports.extend(embedded.ports())

    with pysim.Simulator(
            m, vcd_file=open("top_thing.vcd", "w"),
            gtkw_file=open("top_thing.gtkw", "w"), traces=ports) as sim:
        sim.add_clock(1e-9, domain="pos")

        def process():
            # initial reset
            yield

        sim.add_sync_process(process(), domain="pos")
        sim.run()
