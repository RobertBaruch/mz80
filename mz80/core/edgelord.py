from nmigen import *
from nmigen.cli import main
from nmigen.asserts import *


# module edgelord outputs the state of the clock without using
# the clock in combinatorial logic. This is a good thing in
# FPGAs, where the clock is a special signal that might get
# badly routed if it has to go through anything other than the
# clock inputs of flipflops.
#
# The reset signal MUST be held high for both edges,
# otherwise the clk_state will be inverted.
class Edgelord(Elaboratable):
    def __init__(self):
        self.clk_state = Signal()

    def elaborate(self, platform):
        pos = Signal()
        neg = Signal()
        rst = ResetSignal("pos")

        m = Module()

        # Verilog equivalent:
        #
        # assign clk_state = reset || !(pos ^ neg);
        m.d.comb += self.clk_state.eq(rst | ~(pos ^ neg))

        # Verilog equivalent:
        #
        # always @(posedge clk) begin
        #     if (reset) pos <= 0;
        #     else pos <= !(pos ^ clk_state);
        # end
        #
        # always @(negedge clk) begin
        #     if (reset) neg <= 0;
        #     else neg <= neg ^ clk_state;
        # end
        with m.If(rst):
            m.d.pos += pos.eq(0)
            m.d.neg += neg.eq(0)
        with m.Else():
            m.d.pos += pos.eq(~(pos ^ self.clk_state))
            m.d.neg += neg.eq(neg ^ self.clk_state)

        if platform == "formal":
            self.formal(m)

        return m

    def formal(self, m):
        cycle = Signal(8, reset_less=True)
        rst = ResetSignal("pos")
        clk = ClockSignal("pos")

        m.d.pos += cycle.eq(cycle + (cycle != 255))

        m.d.comb += Assume(rst == (cycle < 2))
        with m.If(rst == 0):
            m.d.comb += Assert(clk == self.clk_state)


if __name__ == "__main__":
    clk = Signal()
    rst = Signal()

    pos = ClockDomain()
    pos.clk = clk
    pos.rst = rst

    neg = ClockDomain(clk_edge="neg")
    neg.clk = clk
    neg.rst = rst

    edgelord = Edgelord()

    m = Module()
    m.domains.pos = pos
    m.domains.neg = neg
    m.submodules.edgelord = edgelord

    main(m, ports=[clk, rst, edgelord.clk_state], platform="formal")
