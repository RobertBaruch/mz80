from enum import Enum, unique
from nmigen import *
from nmigen.cli import main
from nmigen.asserts import *

from .edgelord import Edgelord
from .muxing import MCycle

class MCycler(Elaboratable):
    def __init__(self):
        self.LATCHING = 0

        #
        # Signals eventually going outside
        #

        self.A = Signal(16)
        self.Dout = Signal(8)
        self.mreq = Signal()
        self.iorq = Signal()
        self.rd = Signal()
        self.wr = Signal()
        self.m1 = Signal()
        self.rfsh = Signal()
        self.busack = Signal()
        # Sets the data direction: 0 = in, 1 = out
        self.ddir = Signal()
        # Sets the address, data, and tristate control lines to high impedance.
        self.hiz = Signal()

        #
        # Signals coming from the outside
        #

        # Data coming in from the external bus
        self.Din = Signal(8)

        # Requests the bus from the processor. Sampled on the rising edge of
        # the last clock period of any machine cycle. On the rising edge of
        # the next clock cycle, the address, data and tristate control lines
        # will be set to the high impedance state, and the busack signal
        # will be asserted.
        #
        # Once the bus is released, the signal is sampled on every rising edge
        # of the clock. If low, then the busack signal is deasserted on the
        # # next negative edge of the clock, and on the following rising edge,
        # the next machine cycle is initiated and the address, data, and tristate
        # control lines are taken out of the high impedance state.
        self.busreq = Signal()

        # Adds a wait state to a memory or I/O read or write cycle. This includes
        # a fetch cycle.
        self.buswait = Signal()

        #
        # Signals coming from the sequencer
        #

        self.extend = Signal()
        self.cycle = Signal.enum(MCycle)
        self.addr = Signal(16)
        self.refresh_addr = Signal(16)
        self.wdata = Signal(8)

        #
        # Signals going into the sequencer
        #

        # Tells the sequencer that all the actions it set up are to be
        # registered on the positive edge of the clock.
        self.act = Signal()
        self.rdata = Signal(8)

        # Signals indicating state
        self.mcycle = Signal.enum(MCycle)
        self.mcycle_done = Signal()
        self.tcycle = Signal(4)
        self.tcycles = Signal(4)

    def ports(self):
        return [
            self.A, self.Din, self.Dout, self.ddir, self.busreq, self.buswait,
            self.mreq, self.iorq, self.rd, self.wr, self.A, self.m1, self.rfsh,
            self.busack, self.hiz, self.extend, self.cycle, self.addr,
            self.refresh_addr, self.wdata, self.act, self.rdata, self.mcycle,
            self.tcycle, self.tcycles
        ]

    def elaborate(self, platform):
        m = Module()
        m.submodules.edgelord = edgelord = Edgelord()

        self.waitstated = Signal()
        m.d.neg += self.waitstated.eq(self.buswait)

        self.busrequested = Signal()
        m.d.pos += self.busrequested.eq(self.busreq)

        self.neg_latched_Din = Signal(8)
        m.d.neg += self.neg_latched_Din.eq(self.Din)

        self.latched_rdata = Signal(8)

        self.c = edgelord.clk_state
        self.cycle_to_start = Signal.enum(MCycle)

        self.latched_addr = Signal(16)
        self.latched_refresh_addr = Signal(16)
        self.latched_wdata = Signal(8)
        with m.If(self.mcycle_done):
            m.d.pos += [
                self.latched_addr.eq(self.addr),
                self.latched_refresh_addr.eq(self.refresh_addr),
                self.latched_wdata.eq(self.wdata),
            ]

        with m.FSM(domain="pos", reset="RESET") as fsm:
            # Defaults
            m.d.comb += [
                self.mcycle_done.eq(0),
                self.tcycle.eq(0),
                self.ddir.eq(0),
                self.hiz.eq(0),
                self.A.eq(0),
                self.Dout.eq(0),
                self.mreq.eq(0),
                self.iorq.eq(0),
                self.m1.eq(0),
                self.rd.eq(0),
                self.wr.eq(0),
                self.rfsh.eq(0),
                self.busack.eq(0),
                self.act.eq(~self.waitstated & ~self.hiz),
                self.rdata.eq(0),
            ]

            with m.State("RESET"):
                m.d.comb += [
                    self.mcycle.eq(MCycle.NONE),
                    self.mcycle_done.eq(1),
                    self.hiz.eq(1),
                ]
                with m.If(~ResetSignal("pos")):
                    m.d.pos += self.tcycles.eq(0)
                    self.endCycle(m, MCycle.M1)

            with m.State("M1_1"):
                m.d.comb += [
                    self.mcycle.eq(MCycle.M1),
                    self.tcycle.eq(1),
                    self.A.eq(Mux(self.LATCHING, self.latched_addr, self.addr)),
                    self.mreq.eq(~self.c),
                    self.m1.eq(1),
                    self.rd.eq(~self.c),
                ]
                m.d.pos += self.tcycles.eq(1)
                m.next = "M1_2"

            with m.State("M1_2"):
                m.d.comb += [
                    self.mcycle.eq(MCycle.M1),
                    self.tcycle.eq(2),
                    self.A.eq(Mux(self.LATCHING, self.latched_addr, self.addr)),
                    self.mreq.eq(1),
                    self.m1.eq(1),
                    self.rd.eq(1),
                ]
                with m.If(self.waitstated):
                    m.next = "M1_2"
                with m.Else():
                    m.d.pos += [
                        self.latched_rdata.eq(self.Din),
                        self.tcycles.eq(2),
                    ]
                    m.next = "M1_3"

            with m.State("M1_3"):
                m.d.comb += [
                    self.mcycle.eq(MCycle.M1),
                    self.tcycle.eq(3),
                    self.A.eq(Mux(self.LATCHING, self.latched_refresh_addr, self.refresh_addr)),
                    self.mreq.eq(~self.c),
                    self.rdata.eq(self.latched_rdata),
                ]
                m.d.pos += self.tcycles.eq(3)
                m.next = "M1_4"

            with m.State("M1_4"):
                m.d.comb += [
                    self.mcycle.eq(MCycle.M1),
                    self.tcycle.eq(4),
                    self.A.eq(Mux(self.LATCHING, self.latched_refresh_addr, self.refresh_addr)),
                    self.mreq.eq(self.c),
                    self.rdata.eq(self.latched_rdata),
                ]
                self.endCycle(m, self.cycle)

            with m.State("M1_EXT"):
                m.d.comb += [
                    self.mcycle.eq(MCycle.M1),
                    self.tcycle.eq(5),
                    self.A.eq(Mux(self.LATCHING, self.latched_refresh_addr, self.refresh_addr)),
                    self.rdata.eq(self.latched_rdata),
                ]
                self.endCycle(m, self.cycle)

            with m.State("MEMRD_1"):
                m.d.comb += [
                    self.mcycle.eq(MCycle.MEMRD),
                    self.tcycle.eq(1),
                    self.A.eq(Mux(self.LATCHING, self.latched_addr, self.addr)),
                    self.mreq.eq(~self.c),
                    self.rd.eq(~self.c),
                    self.rdata.eq(self.latched_rdata),
                ]
                m.d.pos += self.tcycles.eq(1)
                m.next = "MEMRD_2"

            with m.State("MEMRD_2"):
                m.d.comb += [
                    self.mcycle.eq(MCycle.MEMRD),
                    self.tcycle.eq(2),
                    self.A.eq(Mux(self.LATCHING, self.latched_addr, self.addr)),
                    self.mreq.eq(~self.c),
                    self.rd.eq(~self.c),
                    self.rdata.eq(self.latched_rdata),
                ]
                m.d.pos += self.tcycles.eq(2)
                with m.If(self.waitstated):
                    m.next = "MEMRD_2"
                with m.Else():
                    m.next = "MEMRD_3"

            with m.State("MEMRD_3"):
                m.d.comb += [
                    self.mcycle.eq(MCycle.MEMRD),
                    self.tcycle.eq(3),
                    self.A.eq(Mux(self.LATCHING, self.latched_addr, self.addr)),
                    self.mreq.eq(self.c),
                    self.rd.eq(self.c),
                    self.rdata.eq(self.neg_latched_Din),
                ]
                m.d.pos += self.latched_rdata.eq(self.neg_latched_Din)
                self.endCycle(m, self.cycle)

            with m.State("MEMRD_EXT"):
                m.d.comb += [
                    self.mcycle.eq(MCycle.MEMRD),
                    self.tcycle.eq(4),
                    self.A.eq(Mux(self.LATCHING, self.latched_addr, self.addr)),
                    self.rdata.eq(self.latched_rdata),
                ]
                self.endCycle(m, self.cycle)

            with m.State("MEMWR_1"):
                m.d.comb += [
                    self.mcycle.eq(MCycle.MEMWR),
                    self.tcycle.eq(1),
                    self.ddir.eq(~self.c),
                    self.A.eq(Mux(self.LATCHING, self.latched_addr, self.addr)),
                    self.Dout.eq(Mux(self.LATCHING, self.latched_wdata, self.wdata)),
                    self.mreq.eq(~self.c),
                ]
                m.d.pos += self.tcycles.eq(1)
                m.next = "MEMWR_2"

            with m.State("MEMWR_2"):
                m.d.comb += [
                    self.mcycle.eq(MCycle.MEMWR),
                    self.tcycle.eq(2),
                    self.ddir.eq(1),
                    self.A.eq(Mux(self.LATCHING, self.latched_addr, self.addr)),
                    self.Dout.eq(Mux(self.LATCHING, self.latched_wdata, self.wdata)),
                    self.mreq.eq(1),
                    self.wr.eq(~self.c),
                ]
                m.d.pos += self.tcycles.eq(2)
                with m.If(self.waitstated):
                    m.next = "MEMWR_WAIT"
                with m.Else():
                    m.next = "MEMWR_3"

            with m.State("MEMWR_WAIT"):
                m.d.comb += [
                    self.mcycle.eq(MCycle.MEMWR),
                    self.tcycle.eq(2),
                    self.ddir.eq(1),
                    self.A.eq(Mux(self.LATCHING, self.latched_addr, self.addr)),
                    self.Dout.eq(Mux(self.LATCHING, self.latched_wdata, self.wdata)),
                    self.mreq.eq(1),
                    self.wr.eq(1),
                ]
                m.d.pos += self.tcycles.eq(2)
                with m.If(self.waitstated):
                    m.next = "MEMWR_WAIT"
                with m.Else():
                    m.next = "MEMWR_3"

            with m.State("MEMWR_3"):
                m.d.comb += [
                    self.mcycle.eq(MCycle.MEMWR),
                    self.tcycle.eq(3),
                    self.ddir.eq(1),
                    self.A.eq(Mux(self.LATCHING, self.latched_addr, self.addr)),
                    self.Dout.eq(Mux(self.LATCHING, self.latched_wdata, self.wdata)),
                    self.mreq.eq(self.c),
                    self.wr.eq(self.c),
                ]
                self.endCycle(m, self.cycle)

            with m.State("MEMWR_EXT"):
                m.d.comb += [
                    self.mcycle.eq(MCycle.MEMWR),
                    self.tcycle.eq(4),
                    self.A.eq(Mux(self.LATCHING, self.latched_addr, self.addr)),
                    self.Dout.eq(Mux(self.LATCHING, self.latched_wdata, self.wdata)),
                ]
                self.endCycle(m, self.cycle)

            with m.State("IORD_1"):
                m.d.comb += [
                    self.mcycle.eq(MCycle.IORD),
                    self.tcycle.eq(1),
                    self.A.eq(Mux(self.LATCHING, self.latched_addr, self.addr)),
                    self.rdata.eq(self.latched_rdata),
                ]
                m.d.pos += self.tcycles.eq(1)
                m.next = "IORD_2"

            with m.State("IORD_2"):
                m.d.comb += [
                    self.mcycle.eq(MCycle.IORD),
                    self.tcycle.eq(2),
                    self.A.eq(Mux(self.LATCHING, self.latched_addr, self.addr)),
                    self.iorq.eq(1),
                    self.rd.eq(1),
                    self.rdata.eq(self.latched_rdata),
                ]
                m.d.pos += self.tcycles.eq(2)
                m.next = "IORD_WAIT"

            with m.State("IORD_WAIT"):
                m.d.comb += [
                    self.mcycle.eq(MCycle.IORD),
                    self.tcycle.eq(2),
                    self.A.eq(Mux(self.LATCHING, self.latched_addr, self.addr)),
                    self.iorq.eq(1),
                    self.rd.eq(1),
                    self.rdata.eq(self.latched_rdata),
                ]
                m.d.pos += self.tcycles.eq(3)
                with m.If(self.waitstated):
                    m.next = "IORD_WAIT"
                with m.Else():
                    m.next = "IORD_3"

            with m.State("IORD_3"):
                m.d.comb += [
                    self.mcycle.eq(MCycle.IORD),
                    self.tcycle.eq(3),
                    self.A.eq(Mux(self.LATCHING, self.latched_addr, self.addr)),
                    self.iorq.eq(self.c),
                    self.rd.eq(self.c),
                    self.rdata.eq(self.neg_latched_Din),
                ]
                m.d.pos += self.latched_rdata.eq(self.neg_latched_Din)
                self.endCycle(m, self.cycle)

            with m.State("IORD_EXT"):
                m.d.comb += [
                    self.mcycle.eq(MCycle.IORD),
                    self.tcycle.eq(4),
                    self.A.eq(Mux(self.LATCHING, self.latched_addr, self.addr)),
                    self.rdata.eq(self.latched_rdata),
                ]
                self.endCycle(m, self.cycle)

            with m.State("IOWR_1"):
                m.d.comb += [
                    self.mcycle.eq(MCycle.IOWR),
                    self.tcycle.eq(1),
                    self.ddir.eq(~self.c),
                    self.A.eq(Mux(self.LATCHING, self.latched_addr, self.addr)),
                    self.Dout.eq(Mux(self.LATCHING, self.latched_wdata, self.wdata)),
                ]
                m.d.pos += self.tcycles.eq(1)
                m.next = "IOWR_2"

            with m.State("IOWR_2"):
                m.d.comb += [
                    self.mcycle.eq(MCycle.IOWR),
                    self.tcycle.eq(2),
                    self.ddir.eq(1),
                    self.A.eq(Mux(self.LATCHING, self.latched_addr, self.addr)),
                    self.Dout.eq(Mux(self.LATCHING, self.latched_wdata, self.wdata)),
                    self.iorq.eq(1),
                    self.wr.eq(1),
                ]
                m.d.pos += self.tcycles.eq(2)
                m.next = "IOWR_WAIT"

            with m.State("IOWR_WAIT"):
                m.d.comb += [
                    self.mcycle.eq(MCycle.IOWR),
                    self.tcycle.eq(2),
                    self.ddir.eq(1),
                    self.A.eq(Mux(self.LATCHING, self.latched_addr, self.addr)),
                    self.Dout.eq(Mux(self.LATCHING, self.latched_wdata, self.wdata)),
                    self.iorq.eq(1),
                    self.wr.eq(1),
                ]
                m.d.pos += self.tcycles.eq(3)
                with m.If(self.waitstated):
                    m.next = "IOWR_WAIT"
                with m.Else():
                    m.next = "IOWR_3"

            with m.State("IOWR_3"):
                m.d.comb += [
                    self.mcycle.eq(MCycle.IOWR),
                    self.tcycle.eq(3),
                    self.ddir.eq(1),
                    self.A.eq(Mux(self.LATCHING, self.latched_addr, self.addr)),
                    self.Dout.eq(Mux(self.LATCHING, self.latched_wdata, self.wdata)),
                    self.iorq.eq(self.c),
                    self.wr.eq(self.c),
                ]
                self.endCycle(m, self.cycle)

            with m.State("IOWR_EXT"):
                m.d.comb += [
                    self.mcycle.eq(MCycle.IOWR),
                    self.tcycle.eq(4),
                    self.A.eq(Mux(self.LATCHING, self.latched_addr, self.addr)),
                    self.Dout.eq(Mux(self.LATCHING, self.latched_wdata, self.wdata)),
                ]
                self.endCycle(m, self.cycle)

            with m.State("INTERNAL"):
                m.d.comb += [
                    self.mcycle.eq(MCycle.INTERNAL),
                    self.tcycle.eq(self.tcycles + 1),
                ]
                self.endCycle(m, self.cycle)

            with m.State("BUSRELEASE"):
                m.d.comb += [
                    self.mcycle.eq(MCycle.BUSRELEASE),
                    self.hiz.eq(1),
                    self.busack.eq(1),
                    self.rdata.eq(self.latched_rdata),
                ]
                m.d.pos += self.tcycles.eq(0)
                with m.If(~self.busrequested):
                    m.next = "BUSTAKE"

            with m.State("BUSTAKE"):
                m.d.comb += [
                    self.mcycle.eq(MCycle.BUSRELEASE),
                    self.hiz.eq(1),
                    self.busack.eq(self.c),
                    self.rdata.eq(self.latched_rdata),
                ]
                self.endCycle(m, self.cycle)

        if platform == "formal":
            self.formal(m)
        return m

    def endCycle(self, m, next):
        m.d.pos += self.tcycles.eq(self.tcycles + 1)
        with m.If(self.extend & (self.mcycle !=
                  MCycle.BUSRELEASE) & (self.mcycle != MCycle.NONE)):
            with m.Switch(self.mcycle):
                with m.Case(MCycle.M1):
                    m.next = "M1_EXT"
                with m.Case(MCycle.MEMRD):
                    m.next = "MEMRD_EXT"
                with m.Case(MCycle.MEMWR):
                    m.next = "MEMWR_EXT"
                with m.Case(MCycle.IORD):
                    m.next = "IORD_EXT"
                with m.Case(MCycle.IOWR):
                    m.next = "IOWR_EXT"
                with m.Case(MCycle.INTERNAL):
                    m.next = "INTERNAL"
                with m.Default():
                    m.next = "RESET"
        with m.Elif(self.busrequested):
            m.d.comb += [
                self.mcycle_done.eq(~self.c),
                self.cycle_to_start.eq(MCycle.BUSRELEASE),
            ]
            m.next = "BUSRELEASE"
        with m.Else():
            m.d.comb += [
                self.mcycle_done.eq(~self.c),
                self.cycle_to_start.eq(next),
            ]
            with m.Switch(next):
                with m.Case(MCycle.M1):
                    m.next = "M1_1"
                with m.Case(MCycle.MEMRD):
                    m.next = "MEMRD_1"
                with m.Case(MCycle.MEMWR):
                    m.next = "MEMWR_1"
                with m.Case(MCycle.IORD):
                    m.next = "IORD_1"
                with m.Case(MCycle.IOWR):
                    m.next = "IOWR_1"
                with m.Case(MCycle.INTERNAL):
                    m.next = "INTERNAL"
                with m.Case(MCycle.BUSRELEASE):
                    m.next = "BUSRELEASE"
                with m.Case(MCycle.NONE):
                    m.next = "RESET"
                with m.Default():
                    m.next = "RESET"

    def formal(self, m: Module):
        # Assume we never ask for an invalid or BUSRELEASE cycle. This is so that comparing
        # requested cycle to actual cycle is simpler.
        m.d.comb += Assume(self.cycle < MCycle.BUSRELEASE)
        m.d.comb += Assume(self.cycle != MCycle.BUSRELEASE)

        # If mcycle_done(N-1^) == 1, then mcycle(N) == cycle_to_start(N-1^),
        # unless bus was requested.
        with m.If(
                Past(self.mcycle_done, domain="pos") &
                ~Past(self.busrequested, domain="pos")):
            m.d.comb += Assert(
                self.mcycle == Past(self.cycle_to_start, domain="pos"))

        # If extend(N^-) == 1 and mcycle(N^-) != NONE then mcycle_done(N^-) == 0.
        # Note that extending a NONE cycle or a BUSRELEASE cycle doesn't do anything.
        # Should it?
        with m.If(
                Past(self.extend, domain="pos") &
            (Past(self.mcycle, domain="pos") != MCycle.NONE) &
            (Past(self.mcycle, domain="pos") != MCycle.BUSRELEASE)):
            m.d.comb += Assert(~Past(self.mcycle_done, domain="pos"))

        # m1 and rfsh can never be active at the same time
        m.d.comb += Assert(~(self.m1 & self.rfsh))

        # rd and wr can never be active at the same time
        m.d.comb += Assert(~(self.rd & self.wr))

        # iorq and mreq can never be active at the same time
        m.d.comb += Assert(~(self.iorq & self.mreq))

        # hiz and ddir can never be active at the same time
        m.d.comb += Assert(~(self.hiz & self.ddir))

        # hiz and (rd or wr) can never be active at the same time
        m.d.comb += Assert(~(self.hiz & (self.rd | self.wr)))

        # If rd then ddir == 0.
        with m.If(self.rd):
            m.d.comb += Assert(~self.ddir)

        # If wr then ddir == 1.
        with m.If(self.wr):
            m.d.comb += Assert(self.ddir)

        # When m1 is high, A must be addr.
        with m.If(self.m1):
            m.d.comb += Assert(self.A == self.latched_addr)

        # When rfsh is high, A must be refresh_addr and rd and wr must be low
        with m.If(self.rfsh):
            m.d.comb += Assert(
                (self.A == self.latched_refresh_addr) & ~self.rd & ~self.wr)

        # When m1 is high or rfsh is high, the cycle must be M1.
        with m.If(self.m1 | self.rfsh):
            m.d.comb += Assert(self.mcycle == MCycle.M1)

        # If busack(N^) == 1 then busrequested(N-1^) == 1
        with m.If(self.busack):
            m.d.pos += Assert(Past(self.busrequested, domain="pos"))

        # If busack(N^) == 0 and busack(N-1^) == 1 then busrequested(N-1^) == 0
        with m.If(~self.busack & Past(self.busack, domain="pos")):
            m.d.pos += Assert(~Past(self.busrequested, domain="pos"))

        # If busack is high then hiz must also be high.
        with m.If(self.busack):
            m.d.comb += Assert(self.hiz)

        # During M1:
        with m.If(self.mcycle == MCycle.M1):
            # iorq must be low, hiz must be low
            m.d.comb += Assert(~self.iorq)
            m.d.comb += Assert(~self.hiz)

            # When rd is high, mreq and m1 must be high, rfsh must be low, and
            # A must be addr.
            with m.If(self.rd):
                m.d.comb += [
                    Assert(self.mreq),
                    Assert(self.m1),
                    Assert(~self.rfsh),
                    Assert(self.A == self.latched_addr),
                ]

            # Ensure that rdata is stable from T3 to the end of the cycle.
            # That is, rdata(N) == rdata(N-1) if tcycle(N) > 3.
            with m.If(self.tcycle > 3):
                m.d.comb += Assert(
                    self.rdata == Past(self.rdata, domain="pos"))

            # Ensure that if we reach T3, then the last T2 wasn't waitstated.
            # That is, if tcycle(N) == 3 then waitstated(N-1) == 0.
            with m.If(self.tcycle == 3):
                m.d.comb += Assert(~Past(self.waitstated, domain="pos"))

            # Ensure that rdata after T2 is equal to whatever was on the bus at
            # the end of the last T2. That is, if tcycle(N) == 3 then
            # rdata(N) = Din(N-1).
            with m.If(self.tcycle == 3):
                m.d.comb += Assert(self.rdata == Past(self.Din, domain="pos"))

        # During MEMRD:
        with m.If(self.mcycle == MCycle.MEMRD):
            # iorq, hiz, wr, rfsh must all be low
            m.d.comb += Assert(~self.iorq)
            m.d.comb += Assert(~self.hiz)
            m.d.comb += Assert(~self.wr)
            m.d.comb += Assert(~self.rfsh)

            # mreq and rd are the same
            m.d.comb += Assert(self.mreq == self.rd)

            # Ensure that latched_addr during T1 is addr(T1-1^).
            with m.If(self.tcycle == 1):
                m.d.comb += Assert(
                    self.latched_addr == Past(self.addr, domain="pos"))

            # Ensure that latched_addr is stable from T2 through the end.
            with m.If(self.tcycle > 1):
                m.d.comb += Assert(
                    self.latched_addr == Past(self.latched_addr, domain="pos"))

            # Ensure that A is equal to latched_addr.
            m.d.comb += Assert(self.A == self.latched_addr)

            # Ensure that rdata in the bottom half of T3 is equal to whatever
            # was on the bus on the negative clock edge of T3.
            with m.If((self.tcycle == 3) & (~self.c)):
                m.d.comb += Assert(self.rdata == Past(self.Din, domain="neg"))

            # Ensure that rdata is stable from T3 to the end of the cycle.
            # That is, rdata(N) == rdata(N-1) if tcycle(N) > 3.
            with m.If(self.tcycle > 3):
                m.d.comb += Assert(
                    self.rdata == Past(self.rdata, domain="pos"))

            # Ensure that if we reach T3, then the last T2 wasn't waitstated.
            # That is, if tcycle(N) == 3 then waitstated(N-1) == 0.
            with m.If(self.tcycle == 3):
                m.d.comb += Assert(~Past(self.waitstated, domain="pos"))

        # During MEMWR:
        with m.If(self.mcycle == MCycle.MEMWR):
            # iorq, hiz, rd, rfsh must all be low
            m.d.comb += Assert(~self.iorq)
            m.d.comb += Assert(~self.hiz)
            m.d.comb += Assert(~self.rd)
            m.d.comb += Assert(~self.rfsh)

            # When wr is high, mreq is high
            with m.If(self.wr):
                m.d.comb += Assert(self.mreq)

            # Ensure that latched_addr during T1 is addr(T1-1^).
            with m.If(self.tcycle == 1):
                m.d.comb += Assert(
                    self.latched_addr == Past(self.addr, domain="pos"))

            # Ensure that latched_addr is stable from T2 through the end.
            with m.If(self.tcycle > 1):
                m.d.comb += Assert(
                    self.latched_addr == Past(self.latched_addr, domain="pos"))

            # Ensure that A is equal to latched_addr.
            m.d.comb += Assert(self.A == self.latched_addr)

            # Ensure that Dout in the bottom half of T1 is equal to
            # wdata(T1-1^).
            with m.If((self.tcycle == 1) & (~self.c)):
                m.d.comb += Assert(Past(self.wdata, domain="pos") == self.Dout)

            # Ensure that latched_wdata in the bottom half of T1 is equal to
            # wdata(T1-1^).
            with m.If((self.tcycle == 1) & (~self.c)):
                m.d.comb += Assert(
                    Past(self.wdata, domain="pos") == self.latched_wdata)

            # Ensure that latched_wdata is stable from T2 to the end of the cycle.
            # That is, latched_wdata(N) == latched_wdata(N-1) if tcycle(N) > 1.
            with m.If(self.tcycle > 1):
                m.d.comb += Assert(self.latched_wdata == Past(
                    self.latched_wdata, domain="pos"))

            # Ensure that Dout is latched_wdata to the end of the cycle.
            # That is, Dout(N) == latched_wdata(N) if tcycle(N) > 1.
            with m.If(self.tcycle > 1):
                m.d.comb += Assert(self.Dout == self.latched_wdata)

            # Ensure that if we reach T3, then the last T2 wasn't waitstated.
            # That is, if tcycle(N) == 3 then waitstated(N-1) == 0.
            with m.If(self.tcycle == 3):
                m.d.comb += Assert(~Past(self.waitstated, domain="pos"))

        # During IORD:
        with m.If(self.mcycle == MCycle.IORD):
            # mreq, hiz, wr, rfsh must all be low
            m.d.comb += Assert(~self.mreq)
            m.d.comb += Assert(~self.hiz)
            m.d.comb += Assert(~self.wr)
            m.d.comb += Assert(~self.rfsh)

            # iorq and rd are the same
            m.d.comb += Assert(self.iorq == self.rd)

            # Ensure that latched_addr during T1 is addr(T1-1^).
            with m.If(self.tcycle == 1):
                m.d.comb += Assert(
                    self.latched_addr == Past(self.addr, domain="pos"))

            # Ensure that latched_addr is stable from T2 through the end.
            with m.If(self.tcycle > 1):
                m.d.comb += Assert(
                    self.latched_addr == Past(self.latched_addr, domain="pos"))

            # Ensure that A is equal to latched_addr.
            m.d.comb += Assert(self.A == self.latched_addr)

            # Ensure that rdata in the bottom half of T3 is equal to whatever
            # was on the bus on the negative clock edge of T3.
            with m.If((self.tcycle == 3) & (~self.c)):
                m.d.comb += Assert(self.rdata == Past(self.Din, domain="neg"))

            # Ensure that rdata is stable from T3 to the end of the cycle.
            # That is, rdata(N) == rdata(N-1) if tcycle(N) > 3.
            with m.If(self.tcycle > 3):
                m.d.comb += Assert(
                    self.rdata == Past(self.rdata, domain="pos"))

            # Ensure that if we reach T3, then the last T2 wasn't waitstated.
            # That is, if tcycle(N) == 3 then waitstated(N-1) == 0.
            with m.If(self.tcycle == 3):
                m.d.comb += Assert(~Past(self.waitstated, domain="pos"))

        # During IOWR:
        with m.If(self.mcycle == MCycle.IOWR):
            # mreq, hiz, rd, rfsh must all be low
            m.d.comb += Assert(~self.mreq)
            m.d.comb += Assert(~self.hiz)
            m.d.comb += Assert(~self.rd)
            m.d.comb += Assert(~self.rfsh)

            # When wr is high, iorq is high
            with m.If(self.wr):
                m.d.comb += Assert(self.iorq)

            # Ensure that latched_addr during T1 is addr(T1-1^).
            with m.If(self.tcycle == 1):
                m.d.comb += Assert(
                    self.latched_addr == Past(self.addr, domain="pos"))

            # Ensure that latched_addr is stable from T2 through the end.
            with m.If(self.tcycle > 1):
                m.d.comb += Assert(
                    self.latched_addr == Past(self.latched_addr, domain="pos"))

            # Ensure that A is equal to latched_addr.
            m.d.comb += Assert(self.A == self.latched_addr)

            # Ensure that Dout in the bottom half of T1 is equal to
            # wdata(T1-1^).
            with m.If((self.tcycle == 1) & (~self.c)):
                m.d.comb += Assert(Past(self.wdata, domain="pos") == self.Dout)

            # Ensure that latched_wdata in the bottom half of T1 is equal to
            # wdata(T1-1^).
            with m.If((self.tcycle == 1) & (~self.c)):
                m.d.comb += Assert(
                    Past(self.wdata, domain="pos") == self.latched_wdata)

            # Ensure that latched_wdata is stable from T2 to the end of the cycle.
            # That is, latched_wdata(N) == latched_wdata(N-1) if tcycle(N) > 1.
            with m.If(self.tcycle > 1):
                m.d.comb += Assert(self.latched_wdata == Past(
                    self.latched_wdata, domain="pos"))

            # Ensure that Dout is latched_wdata to the end of the cycle.
            # That is, Dout(N) == latched_wdata(N) if tcycle(N) > 1.
            with m.If(self.tcycle > 1):
                m.d.comb += Assert(self.Dout == self.latched_wdata)

            # Ensure that if we reach T3, then the last T2 wasn't waitstated.
            # That is, if tcycle(N) == 3 then waitstated(N-1) == 0.
            with m.If(self.tcycle == 3):
                m.d.comb += Assert(~Past(self.waitstated, domain="pos"))


# Formal properties:
#
# Terminology:
#
# ^: A positive edge
# v: A negative edge
# ^+: Just after a positive edge
# ^-: Just before a positive edge
#
# N: the full clock cycle, numbered N, from ^+ up to and including the next ^. That is,
#    the positive edge at the end of cycle N belongs to cycle N, not cycle N+1. The
#    positive edge at the beginning of cycle N belongs to cycle N-1, not cycle N.
#
# N^: the end of clock cycle N: the positive clock edge at the very end of clock cycle N.
# N^+: the beginning of clock cycle N: just after the positive clock edge that starts off
#      clock cycle N.
#
# signal(N): the signal during clock cycle N. It is also asserted to be stable during
#            both halves of the clock cycle.
# signal(N^): the signal at the positive clock edge ending clock cycle N.
#
# In general, signal(N^) == signal(N^-). That is, the signal latched at the clock edge
# is equal to the state of the signal just before that edge.
#
# Example:
#
# If mcycle_done(N^) == 1, then mcycle(N+1) == cycle(N^).
#
# Alternatively, from the viewpoint of clock cycle N:
#
# If mcycle_done(N-1^) == 1, then mcycle(N) == cycle(N-1^).
#
# In nMigen, signal(N-1^) is Past(signal, domain="clk_name").
# In nMigen, signal(N-n^) is Past(signal, clocks=n, domain="clk_name").
#
# Equivalent in Verilog, without using $past:
#
# logic past_mcycle_done;
# logic past_cycle;
# always @(posedge clk) begin
#   past_mcycle_done <= mcycle_done;
#   past_cycle <= cycle;
# end
# always @(*) begin
#   if (past_mcycle_done) assert(mcycle == past_cycle);
# end
#
# Equivalent in nMigen:
#
# with m.If(Past(self.mcycle_done, domain="pos")):
#   m.d.comb += Assert(self.mcycle == Past(self.cycle, domain="pos"))

# For formal verification:
#   python3 m1.py generate -t il > m1.il
#   sby -f m1.sby

if __name__ == "__main__":
    clk = Signal()
    rst = Signal()

    pos = ClockDomain()
    pos.clk = clk
    pos.rst = rst

    neg = ClockDomain(clk_edge="neg")
    neg.clk = clk
    neg.rst = rst

    m1 = MCycler()

    m = Module()
    m.domains.pos = pos
    m.domains.neg = neg
    m.submodules.m1 = m1

    main(m, ports=[clk, rst] + m1.ports(), platform="formal")
