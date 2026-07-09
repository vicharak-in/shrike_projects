module uart_fifo #(
    parameter DATA_WIDTH         = 8,
    parameter DEPTH              = 16,
    parameter PTR_WIDTH          = $clog2(DEPTH),
    parameter ALMOST_EMPTY_THRESH = 2,
    parameter ALMOST_FULL_THRESH  = DEPTH - 4
)(
    input  wire                  clk,
    input  wire                  rst_n,


    input  wire                  wr_en,
    input  wire [DATA_WIDTH-1:0] wr_data,

    input  wire                  rd_en,
    output wire [DATA_WIDTH-1:0] rd_data,

    // Status flags
    output wire                  empty,
    output wire                  full,
    output wire                  almost_empty,
    output wire                  almost_full,

    // Error strobes (single-cycle)
    output reg                   overflow,
    output reg                   underflow
);


    reg [DATA_WIDTH-1:0] mem [0:DEPTH-1];

    reg [PTR_WIDTH-1:0]  wr_ptr;
    reg [PTR_WIDTH-1:0]  rd_ptr;
    reg [PTR_WIDTH:0]    count;      

    assign empty        = (count == {(PTR_WIDTH+1){1'b0}});
    assign full         = (count == DEPTH[PTR_WIDTH:0]);
    assign almost_empty = (count <= ALMOST_EMPTY_THRESH[PTR_WIDTH:0]);
    assign almost_full  = (count >= ALMOST_FULL_THRESH[PTR_WIDTH:0]);


    assign rd_data = mem[rd_ptr];

  
    integer i;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wr_ptr    <= {PTR_WIDTH{1'b0}};
            rd_ptr    <= {PTR_WIDTH{1'b0}};
            count     <= {(PTR_WIDTH+1){1'b0}};
            overflow  <= 1'b0;
            underflow <= 1'b0;
            for (i = 0; i < DEPTH; i = i + 1)
                mem[i] <= {DATA_WIDTH{1'b0}};
        end else begin
    
            overflow  <= 1'b0;
            underflow <= 1'b0;

            case ({wr_en & ~full, rd_en & ~empty})

                2'b10: begin
                    mem[wr_ptr] <= wr_data;
                    wr_ptr      <= wr_ptr + 1'b1;
                    count       <= count + 1'b1;
                end

                2'b01: begin
                    rd_ptr <= rd_ptr + 1'b1;
                    count  <= count - 1'b1;
                end

                2'b11: begin
                    mem[wr_ptr] <= wr_data;
                    wr_ptr      <= wr_ptr + 1'b1;
                    rd_ptr      <= rd_ptr + 1'b1;
             
                end

                default: begin
                
                    if (wr_en && full)
                        overflow  <= 1'b1;
                    if (rd_en && empty)
                        underflow <= 1'b1;
                end

            endcase
        end
    end

endmodule