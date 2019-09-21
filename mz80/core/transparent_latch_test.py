from nmigen import *
from nmigen.asserts import *
from nmigen.hdl.ast import *
from nmigen.back import pysim

from transparent_latch import TransparentLatch

if __name__ == "__main__":
    latch = TransparentLatch(8)
    ports = latch.ports()

    with pysim.Simulator(
            latch,
            vcd_file=open("transparent_latch.vcd", "w"),
            gtkw_file=open("transparent_latch.gtkw", "w"),
            traces=ports) as sim:
        sim.add_clock(1e-9, domain="pos")

        def process():
            # initial reset
            yield latch.input.eq(0)
            yield latch.en.eq(0)
            yield
            yield
            yield latch.input.eq(0xFF)
            yield
            yield latch.en.eq(1)
            yield
            yield latch.en.eq(0)
            yield

        sim.add_sync_process(process(), domain="pos")
        sim.run()
