from nmigen import *
from nmigen.cli import main
from nmigen.asserts import *

from .muxing import *
from .arch import Registers
from .mcycler import *
from .transparent_latch import TransparentLatch
from ..z80fi.z80fi import Z80fiInterface

@unique
class Step(Enum):
    # Copy Register8 to another Register8. Args: src (reg8), dest (reg8)
    COPY_REG8 = 0
    HALT = 1
    # Do a memory read cycle. Args: addr (reg16), dest (reg8)
    MEM_RD = 2
    # Do a memory write cycle. Args: addr (reg16), src (reg8)
    MEM_WR = 3
    # Add using addr ALU, low. Args: addr (reg16), dest (reg8)
    ADDR_ALU_ADD_LO = 4
    # Add using addr ALU, high. Args: addr (reg16), dest (reg8)
    ADDR_ALU_ADD_HI = 5

@unique
class Arg(Enum):
    NONE = 0
    # Translate a register r-encoding to Register8
    REG8_R = 1
    # Register 16
    REG16 = 2
    HL = 3
    PC = 4
    OFFSET = 5

class Microsequencer(Elaboratable):
    def __init__(self):
        self.controls = SequencerControls(name="ctrls")
        self.microPC = Signal(16)
        self.advance = Signal()
        self.pgm = Array([])
        self.op1 = Signal(16)
        self.op2 = Signal(16)

        self.memrd_addr = Signal.enum(Register16)
        self.memrd_dest = Signal.enum(Register8)
        self.memwr_addr = Signal.enum(Register16)
        self.memwr_src = Signal.enum(Register8)

    def elaborate(self, platform):
        m = Module()

        step = self.pgm[microPC]
        arg1 = self.pgm[microPC+1]
        arg2 = self.pgm[microPC+2]
        mcycle = self.pgm[microPC+3]
        next_microPC = self.pgm[microPC+4]

        op1 = Signal(16)
        op2 = Signal(16)

        m.d.comb += self.cycle.eq(mcycle)
        with m.If(self.advance):
            m.d.pos += self.microPC.eq(next_microPC)

        with m.Switch(arg1):
            with m.Case(Arg.REGISTER8_R):
                m.d.comb += op1.eq(Register8.r(self.op1))
            with m.Case(Arg.Register16):
                m.d.comb += op1.eq(self.op1)

        with m.Switch(arg2):
            with m.Case(Arg.REGISTER8_R):
                m.d.comb += op2.eq(Register8.r(self.op2))
            with m.Case(Arg.Register16):
                m.d.comb += op2.eq(self.op2)

        with m.Switch(step):
            with m.Case(Step.COPY_REG8):
                m.d.comb += self.controls.readRegister8.eq(op1)
                m.d.comb += self.controls.writeRegister8.eq(op2)
            with m.Case(Step.HALT):
                pass
            with m.Case(Step.MEM_RD):
                m.d.pos += self.memrd_addr.eq(op1)
                m.d.pos += self.memrd_dest.eq(op2)
            with m.Case(Step.MEM_WR):
                m.d.pos += self.memwr_addr.eq(op1)
                m.d.pos += self.memwr_src.eq(op2)
            with m.Case(Step.ADDR_ALU_ADD_LO):
                m.d.pos += self.addrALUInput.eq(op1)
                m.d.pos += self.addrALUInputByte.eq(0)
                m.d.comb += self.controls.readRegister8.eq(Register8.ADDR_ALU)
                m.d.comb += self.controls.writeRegister8.eq(op2)
            with m.Case(Step.ADDR_ALU_ADD_HI):
                m.d.pos += self.addrALUInput.eq(op1)
                m.d.pos += self.addrALUInputByte.eq(1)
                m.d.comb += self.controls.readRegister8.eq(Register8.ADDR_ALU)
                m.d.comb += self.controls.writeRegister8.eq(op2)

        return m

class CopyReg(Object):
    def __init__(self, src=None, dest=None):
        self.src = src
        self.dest = dest

    def elaborate(self, seq):
        seq.m.d.comb += seq.controls.readRegister8.eq(self.src)
        seq.m.d.comb += seq.controls.writeRegister8.eq(self.dest)

class Halt(Object):
    def __init__(self):
        pass

    def elaborate(self, seq):
        seq.m.next = "HALT"

class MemRd(Object):
    def __init__(self, addr=None, dest=None):
        self.addr = addr
        self.dest = dest

    def elaborate(self, seq):
        seq.m.next = "RDMEM_T1"
        seq.m.d.comb += seq.cycle.eq(MCycle.MEMRD)
        seq.m.d.pos += seq.memrd_addr.eq(self.addr)
        seq.m.d.pos += seq.memrd_dest.eq(self.dest)
        seq.m.d.pos += seq.instr.en.eq(0)

class MemWr(Object):
    def __init__(self, addr=None, src=None):
        self.addr = addr
        self.src = src

    def elaborate(self, seq):
        seq.m.next = "WRMEM_T1"
        seq.m.d.comb += seq.cycle.eq(MCycle.MEMWR)
        seq.m.d.pos += seq.memwr_addr.eq(self.addr)
        seq.m.d.pos += seq.memwr_src.eq(self.src)
        seq.m.d.pos += seq.instr.en.eq(0)

