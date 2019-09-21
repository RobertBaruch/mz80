/* Generated by Yosys 0.9+36 (git sha1 4aa505d1, clang 6.0.0-1ubuntu2 -fPIC -Os) */

(* \nmigen.hierarchy  = "top.edgelord" *)
(* generator = "nMigen" *)
module edgelord(rst, clk, clk_state);
  (* src = "edgelord.py:28" *)
  wire \$1 ;
  (* src = "edgelord.py:46" *)
  wire \$11 ;
  (* src = "edgelord.py:56" *)
  wire [8:0] \$13 ;
  (* src = "edgelord.py:56" *)
  wire \$14 ;
  (* src = "edgelord.py:56" *)
  wire [8:0] \$16 ;
  (* src = "edgelord.py:58" *)
  wire \$18 ;
  (* src = "edgelord.py:28" *)
  wire \$2 ;
  (* src = "edgelord.py:58" *)
  wire \$20 ;
  (* src = "edgelord.py:59" *)
  wire \$23 ;
  (* src = "edgelord.py:60" *)
  wire \$25 ;
  (* src = "edgelord.py:28" *)
  wire \$5 ;
  (* src = "edgelord.py:45" *)
  wire \$7 ;
  (* src = "edgelord.py:45" *)
  wire \$8 ;
  (* src = "edgelord.py:60" *)
  reg \$assert$check ;
  (* src = "edgelord.py:60" *)
  reg \$assert$en ;
  (* src = "edgelord.py:58" *)
  wire \$assume$check ;
  (* src = "edgelord.py:58" *)
  wire \$assume$en ;
  (* src = "edgelord.py:64" *)
  input clk;
  (* src = "edgelord.py:16" *)
  output clk_state;
  (* init = 8'h00 *)
  (* src = "edgelord.py:54" *)
  reg [7:0] cycle = 8'h00;
  (* src = "edgelord.py:54" *)
  reg [7:0] \cycle$next ;
  (* init = 1'h0 *)
  (* src = "edgelord.py:20" *)
  reg neg = 1'h0;
  (* src = "edgelord.py:20" *)
  reg \neg$next ;
  (* init = 1'h0 *)
  (* src = "edgelord.py:19" *)
  reg pos = 1'h0;
  (* src = "edgelord.py:19" *)
  reg \pos$next ;
  (* src = "edgelord.py:65" *)
  input rst;
  assign \$7  = ~ (* src = "edgelord.py:45" *) \$8 ;
  assign \$11  = neg ^ (* src = "edgelord.py:46" *) clk_state;
  assign \$14  = cycle != (* src = "edgelord.py:56" *) 8'hff;
  assign \$16  = cycle + (* src = "edgelord.py:56" *) \$14 ;
  assign \$18  = cycle < (* src = "edgelord.py:58" *) 2'h2;
  assign \$20  = rst == (* src = "edgelord.py:58" *) \$18 ;
  always @* if (\$assume$en ) assume(\$assume$check );
  assign \$23  = rst == (* src = "edgelord.py:59" *) 1'h0;
  assign \$25  = cycle == (* src = "edgelord.py:60" *) 1'h0;
  always @* if (\$assert$en ) assert(\$assert$check );
  assign \$2  = pos ^ (* src = "edgelord.py:28" *) neg;
  assign \$1  = ~ (* src = "edgelord.py:28" *) \$2 ;
  assign \$5  = rst | (* src = "edgelord.py:28" *) \$1 ;
  assign \$8  = pos ^ (* src = "edgelord.py:45" *) clk_state;
  always @(posedge clk)
      cycle <= \cycle$next ;
  always @(negedge clk)
      neg <= \neg$next ;
  always @(posedge clk)
      pos <= \pos$next ;
  always @* begin
    (* src = "edgelord.py:41" *)
    casez (rst)
      /* src = "edgelord.py:41" */
      1'h1:
          \pos$next  = 1'h0;
      /* src = "edgelord.py:44" */
      default:
          \pos$next  = \$7 ;
    endcase
    (* src = "/home/robertbaruch/.local/lib/python3.6/site-packages/nmigen/hdl/xfrm.py:518" *)
    casez (rst)
      1'h1:
          \pos$next  = 1'h0;
    endcase
  end
  always @* begin
    (* src = "edgelord.py:41" *)
    casez (rst)
      /* src = "edgelord.py:41" */
      1'h1:
          \neg$next  = 1'h0;
      /* src = "edgelord.py:44" */
      default:
          \neg$next  = \$11 ;
    endcase
    (* src = "/home/robertbaruch/.local/lib/python3.6/site-packages/nmigen/hdl/xfrm.py:518" *)
    casez (rst)
      1'h1:
          \neg$next  = 1'h0;
    endcase
  end
  always @* begin
    \cycle$next  = \$13 [7:0];
    (* src = "/home/robertbaruch/.local/lib/python3.6/site-packages/nmigen/hdl/xfrm.py:518" *)
    casez (rst)
      1'h1:
          \cycle$next  = 8'h00;
    endcase
  end
  always @* begin
    \$assert$en  = 1'h0;
    \$assert$check  = 1'h0;
    (* src = "edgelord.py:59" *)
    casez (\$23 )
      /* src = "edgelord.py:59" */
      1'h1:
        begin
          \$assert$check  = \$25 ;
          \$assert$en  = 1'h1;
        end
    endcase
  end
  assign \$13  = \$16 ;
  assign \$assume$en  = 1'h1;
  assign \$assume$check  = \$20 ;
  assign clk_state = \$5 ;
endmodule

(* \nmigen.hierarchy  = "top" *)
(* top =  1  *)
(* generator = "nMigen" *)
module top(rst, clk_state, clk);
  (* src = "edgelord.py:64" *)
  input clk;
  (* src = "edgelord.py:16" *)
  output clk_state;
  (* src = "edgelord.py:65" *)
  input rst;
  edgelord edgelord (
    .clk(clk),
    .clk_state(clk_state),
    .rst(rst)
  );
endmodule
