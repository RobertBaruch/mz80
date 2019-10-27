from nmigen import *
from nmigen.cli import main
from nmigen.asserts import *
import sys
import itertools

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
        self.unf_in = Signal()
        self.unf_out = Signal()

    def elaborate(self, platform):
        pos = Signal()
        neg = Signal()
        rst = ResetSignal("pos")

        m = Module()

        m.d.comb += self.unf_out.eq(~self.unf_in)

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
    rst = Signal(reset = 1, reset_less = True)

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

    # This is required because of a bug (https://github.com/m-labs/nmigen/issues/28)
    # phase = Signal()
    # m.d.sync += phase.eq(~phase)
    # edgelord = EnableInserter({"pos":~phase,"neg":phase})(edgelord)
    # edgelord = DomainRenamer({"pos":"sync","neg":"sync"})(edgelord)

    m.submodules.edgelord = edgelord

    # with pysim.Simulator(m,
    #                      vcd_file=open("edgelord.vcd", "w"),
    #                      gtkw_file=open("edgelord.gtkw", "w"),
    #                      traces=[clk, rst, edgelord.clk_state]) as sim:
    #     sim.add_clock(1e-9, domain="pos")
    #     sim.add_clock(1e-9, domain="neg")

    #     # sim.add_clock(1e-9)


    #     def process():
    #         yield rst.eq(1)
    #         yield Delay(5e-9)
    #         yield rst.eq(0)

    #     sim.add_process(process())
    #     sim.run_until(20e-9, run_passive=True)

    cycle = Signal(8, reset_less=True)
    m.d.pos += cycle.eq(cycle + 1)

    unf_in = Signal(reset=1, reset_less = True)
    m.d.comb += edgelord.unf_in.eq(unf_in)

    def delay(d):
        for _ in range(d):
            yield None

    def generate_signals(gen):
        with m.Switch(cycle+1):
            c = 0
            ss = []
            for s in gen():
                if s is not None:
                    ss.append([s])
                    continue
                c += 1
                ss = list(itertools.chain(*ss)) # Flatten list
                if len(ss) > 0:
                    with m.Case(c):
                        m.d.pos += ss
                ss = []

    def signal_generator():
        yield from delay(3)
        yield rst.eq(0)
        yield [unf_in.eq(0)]
        yield from delay(1)

    generate_signals(signal_generator)

    m.d.comb += Cover(cycle == 10)
    main(m, ports=[clk, rst, edgelord.clk_state, edgelord.unf_in, edgelord.unf_out])
