/* Generated by Yosys 0.9+36 (git sha1 4aa505d1, clang 6.0.0-1ubuntu2 -fPIC -Os) */

(* cells_not_processed =  1  *)
(* src = "tmp.sv:1" *)
module z80fi_insn_spec_ld_reg_n(z80fi_insn, spec_valid);
  (* src = "tmp.sv:6" *)
  wire _0_;
  (* src = "tmp.sv:3" *)
  output spec_valid;
  (* src = "tmp.sv:2" *)
  input [7:0] z80fi_insn;
  assign _0_ = z80fi_insn == (* src = "tmp.sv:6" *) 8'b00???110;
  assign spec_valid = _0_;
endmodule
