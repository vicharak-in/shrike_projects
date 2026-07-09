
module uart_rx_core #(
    parameter CLKS_PER_BIT = 5208  
)(
    input  wire       clk,
    input  wire       rst_n,
    input  wire       uart_rx,
    output reg  [7:0] rx_byte,
    output reg        rx_data_ready,
    output reg        framing_err
);
    reg rx_sync0, rx_sync1;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rx_sync0 <= 1'b1;
            rx_sync1 <= 1'b1;
        end else begin
            rx_sync0 <= uart_rx;
            rx_sync1 <= rx_sync0;
        end
    end
    wire rx_clean = rx_sync1;   

    localparam [1:0]
        IDLE  = 2'd0,
        START = 2'd1,
        DATA  = 2'd2,
        STOP  = 2'd3;

    reg [1:0]  state;
    reg [15:0] clk_count;
    reg [2:0]  bit_index;
    reg [7:0]  shift_reg;

    localparam [15:0] HALF_BIT = CLKS_PER_BIT / 2;  
    localparam [15:0] FULL_BIT = CLKS_PER_BIT - 1;       

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state         <= IDLE;
            clk_count     <= 16'd0;
            bit_index     <= 3'd0;
            shift_reg     <= 8'd0;
            rx_byte       <= 8'd0;
            rx_data_ready <= 1'b0;
            framing_err   <= 1'b0;
        end else begin

            rx_data_ready <= 1'b0;
            framing_err   <= 1'b0;

            case (state)

                IDLE: begin
                    clk_count <= 16'd0;
                    bit_index <= 3'd0;
                    if (rx_clean == 1'b0)       // falling edge → possible start
                        state <= START;
                end

     
                START: begin
                    if (clk_count == HALF_BIT) begin
                        clk_count <= 16'd0;
                        if (rx_clean == 1'b0)   // valid start bit confirmed
                            state <= DATA;
                        else
                            state <= IDLE;       // glitch — abort
                    end else begin
                        clk_count <= clk_count + 1'b1;
                    end
                end

                DATA: begin
                    if (clk_count == FULL_BIT) begin
                        clk_count             <= 16'd0;
                        shift_reg[bit_index]  <= rx_clean;  // LSB first

                        if (bit_index == 3'd7) begin
                            bit_index <= 3'd0;
                            state     <= STOP;
                        end else begin
                            bit_index <= bit_index + 1'b1;
                        end
                    end else begin
                        clk_count <= clk_count + 1'b1;
                    end
                end

        
                STOP: begin
                    if (clk_count == FULL_BIT) begin
                        clk_count <= 16'd0;
                        state     <= IDLE;

                        if (rx_clean == 1'b1) begin
                            rx_byte       <= shift_reg;
                            rx_data_ready <= 1'b1;
                        end else begin
                            framing_err   <= 1'b1;  
                           
                        end
                    end else begin
                        clk_count <= clk_count + 1'b1;
                    end
                end

                // ----------------------------------------------------------
                default: state <= IDLE;
                // ----------------------------------------------------------

            endcase
        end
    end

endmodule