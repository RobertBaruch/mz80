from nmigen import *
from nmigen.hdl.rec import *

from enum import Enum, unique


class SequencerControls(Record):
    def __init__(self, name=None):
        super().__init__(
            Layout([
                ("dataBusSource", DataBusSource, DIR_FANOUT),
                ("dataBusDest", DataBusDestination, DIR_FANOUT),
                ("readRegister8", Register8, DIR_FANOUT),
                ("readRegister16", Register16, DIR_FANOUT),
                ("writeRegister8", Register8, DIR_FANOUT),
                # The source of 16-bit register writes is the IncDec output.
                ("writeRegister16", Register16, DIR_FANOUT),
                ("addrIncDecSetting", IncDecSetting, DIR_FANOUT),
                ("useIX", 1, DIR_FANOUT),
                ("useIY", 1, DIR_FANOUT),
                # registerSet chooses whether we use the W set or the W2 set.
                ("registerSet", 1, DIR_FANOUT),
                ("aluFunc", ALUFunc, DIR_FANOUT),
                ("addrALUInput", Register16, DIR_FANOUT),
                ("addrALUInputByte", 1, DIR_FANOUT),
            ]),
            name=name)


@unique
class ALUFunc(Enum):
    NONE = 0
    ADD = 1


@unique
class MCycle(Enum):
    NONE = 0
    M1 = 1
    MEMRD = 2
    MEMWR = 3
    IORD = 4
    IOWR = 5
    INTERNAL = 6
    BUSRELEASE = 7


@unique
class Register8(Enum):
    NONE = 0
    I = 1
    R = 2
    W = 3
    Z = 4
    B = 5
    C = 6
    D = 7
    E = 8
    H = 9
    L = 10
    A = 11
    F = 12
    TMP = 13
    OFFSET = 14
    ADDR_ALU = 15
    MCYCLER_RDATA = 16

    @classmethod
    def r(cls, value):
        return Array([
            Register8.B, Register8.C, Register8.D, Register8.E, Register8.H,
            Register8.L, Register8.NONE, Register8.A
        ])[value]


@unique
class Register16(Enum):
    NONE = 0
    WZ = 1
    BC = 2
    DE = 3
    HL = 4
    SP = 5
    PC = 6
    ADDR_ALU = 7


@unique
class DataBusDestination(Enum):
    NONE = 0
    I = 1
    R = 2
    W = 3
    Z = 4
    B = 5
    C = 6
    D = 7
    E = 8
    H = 9
    L = 10
    A = 11
    F = 12
    OFFSET = 13
    TMP = 14
    INSTR = 15
    DATABUFF = 16

    @classmethod
    def r(cls, value):
        return Array([
            DataBusDestination.B, DataBusDestination.C, DataBusDestination.D,
            DataBusDestination.E, DataBusDestination.H, DataBusDestination.L,
            DataBusDestination.NONE, DataBusDestination.A
        ])[value]


@unique
class DataBusSource(Enum):
    NONE = 0
    I = 1
    R = 2
    W = 3
    Z = 4
    B = 5
    C = 6
    D = 7
    E = 8
    H = 9
    L = 10
    A = 11
    F = 12
    ALU = 13
    DATABUFF = 14
    TMP = 15

    @classmethod
    def r(cls, value):
        return Array([
            DataBusSource.B, DataBusSource.C, DataBusSource.D, DataBusSource.E,
            DataBusSource.H, DataBusSource.L, DataBusSource.NONE,
            DataBusSource.A
        ])[value]


@unique
class AddrBusSource(Enum):
    NONE = 0
    WZ = 1
    BC = 2
    DE = 3
    HL = 4
    SP = 5
    PC = 6
    ADDR_ALU = 7


@unique
class AddrIncDecDestination(Enum):
    NONE = 0
    WZ = 1
    BC = 2
    DE = 3
    HL = 4
    SP = 5
    PC = 6


@unique
class AddrALUSource(Enum):
    NONE = 0
    WZ = 1
    BC = 2
    DE = 3
    HL = 4
    SP = 5
    PC = 6


@unique
class IncDecSetting(Enum):
    ZERO = 0
    INC = 1
    DEC = 2
