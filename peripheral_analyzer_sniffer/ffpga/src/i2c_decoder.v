module i2c_decoder (
    input  wire        clk,
    input  wire        rst_n,

    input  wire        sda,
    input  wire        scl,

    output reg         pkt_valid,
    output reg  [7:0]  pkt_addr,
    output reg  [7:0]  pkt_data,
    output reg         pkt_rw,
    output reg         pkt_ack,
    output reg         pkt_is_addr,
    output reg         pkt_start,
    output reg         pkt_stop
);

    // ── Two-stage synchronisers ───────────────────────────────────────────────
    reg [1:0] sda_sync;
    reg [1:0] scl_sync;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sda_sync <= 2'b11;
            scl_sync <= 2'b11;
        end else begin
            sda_sync <= {sda_sync[0], sda};
            scl_sync <= {scl_sync[0], scl};
        end
    end

    wire sda_i = sda_sync[1];
    wire scl_i = scl_sync[1];

    reg sda_prev;
    reg scl_prev;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sda_prev <= 1'b1;
            scl_prev <= 1'b1;
        end else begin
            sda_prev <= sda_i;
            scl_prev <= scl_i;
        end
    end

    wire scl_rise  =  scl_i & ~scl_prev;

    // START: SDA falls while SCL is high
    wire i2c_start = ~sda_i &  sda_prev & scl_i;
    wire i2c_stop  =  sda_i & ~sda_prev & scl_i;

    reg [3:0] bit_cnt;
    reg [7:0] byte_reg;
    reg       is_first_byte;
    reg       bus_active;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            bit_cnt       <= 4'd0;
            byte_reg      <= 8'd0;
            is_first_byte <= 1'b0;
            bus_active    <= 1'b0;

            pkt_valid     <= 1'b0;
            pkt_addr      <= 8'd0;
            pkt_data      <= 8'd0;
            pkt_rw        <= 1'b0;
            pkt_ack       <= 1'b0;
            pkt_is_addr   <= 1'b0;
            pkt_start     <= 1'b0;
            pkt_stop      <= 1'b0;
        end else begin

            // Default: de-assert single-cycle pulses
            pkt_valid <= 1'b0;
            pkt_start <= 1'b0;
            pkt_stop  <= 1'b0;

            // START condition
            if (i2c_start && !bus_active) begin
                bus_active    <= 1'b1;
                bit_cnt       <= 4'd0;
                byte_reg      <= 8'd0;
                is_first_byte <= 1'b1;
                pkt_start     <= 1'b1;
            end

            // STOP condition
            else if (i2c_stop && bus_active) begin
                bus_active    <= 1'b0;
                bit_cnt       <= 4'd0;
                byte_reg      <= 8'd0;
                is_first_byte <= 1'b0;
                pkt_stop      <= 1'b1;
            end

            // SCL rising edge — shift in data bits or latch ACK
            else if (scl_rise && bus_active) begin
                if (bit_cnt <= 4'd7) begin
                    byte_reg <= {byte_reg[6:0], sda_i};
                    bit_cnt  <= bit_cnt + 4'd1;
                end else begin
                    pkt_ack   <= ~sda_i;   // ACK = SDA pulled low
                    pkt_valid <= 1'b1;

                    if (is_first_byte) begin
                        // Address frame: byte_reg = [A6..A0, R/W]
                        pkt_addr      <= byte_reg;
                        pkt_rw        <= byte_reg[0];
                        pkt_is_addr   <= 1'b1;
                        is_first_byte <= 1'b0;
                    end else begin
                        // Data frame
                        pkt_data    <= byte_reg;
                        pkt_is_addr <= 1'b0;
                    end

                    byte_reg <= 8'd0;
                    bit_cnt  <= 4'd0;
                end
            end

        end
    end

endmodule