(* top *)
module top (
    (* iopad_external_pin, clkbuf_inhibit *) input  clk,
    (* iopad_external_pin *)                 output clk_en,
    (* iopad_external_pin *)                 input  rst_n,
    
  
    (* iopad_external_pin *)                 input  uart_rx,
    (* iopad_external_pin *)                 input  i2c_sda,
    (* iopad_external_pin *)                 input  i2c_scl,
    (* iopad_external_pin *)                 input  pwm_in,
    (* iopad_external_pin *)                 input  spi_mon_cs_n, 
    (* iopad_external_pin *)                 input  spi_mon_sclk, 
    (* iopad_external_pin *)                 input  spi_mon_mosi, 
    (* iopad_external_pin *)                 input  spi_mon_miso, 
    
   
    (* iopad_external_pin *)                 input  spi_ss_n,
    (* iopad_external_pin *)                 input  spi_sck,
    (* iopad_external_pin *)                 input  spi_mosi,
    (* iopad_external_pin *)                 output spi_miso,
    (* iopad_external_pin *)                 output spi_miso_en,
    
   
    (* iopad_external_pin *)                 output reg led,
    (* iopad_external_pin *)                 output led_en
);

    assign clk_en = 1'b1;
    assign led_en = 1'b1;

   
    reg pwm_meta, pwm_sync, pwm_d;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            pwm_meta <= 1'b0; pwm_sync <= 1'b0; pwm_d    <= 1'b0;
        end else begin
            pwm_meta <= pwm_in; pwm_sync <= pwm_meta; pwm_d    <= pwm_sync;
        end
    end
    wire pwm_rise =  pwm_sync & ~pwm_d;
    wire pwm_fall = ~pwm_sync &  pwm_d;

    // ── UART 
    wire [7:0] rx_byte;
    wire       rx_data_ready, framing_err;
    uart_rx_core #(.CLKS_PER_BIT(5208)) u_uart (
        .clk(clk), .rst_n(rst_n), .uart_rx(uart_rx),
        .rx_byte(rx_byte), .rx_data_ready(rx_data_ready), .framing_err(framing_err)
    );

    // ── I2C 
    wire        pkt_valid, pkt_rw, pkt_ack, pkt_is_addr, pkt_start, pkt_stop;
    wire [7:0]  pkt_addr, pkt_data;
    i2c_decoder u_i2c (
        .clk(clk), .rst_n(rst_n),
        .sda(i2c_sda), .scl(i2c_scl),
        .pkt_valid(pkt_valid), .pkt_addr(pkt_addr), .pkt_data(pkt_data),
        .pkt_rw(pkt_rw), .pkt_ack(pkt_ack), .pkt_is_addr(pkt_is_addr),
        .pkt_start(pkt_start), .pkt_stop(pkt_stop)
    );

    // ── SPI 
    wire        spi_pkt_valid, spi_pkt_start, spi_pkt_stop;
    wire [7:0]  spi_pkt_mosi, spi_pkt_miso;
    spi_decoder u_spi_decoder (
        .clk(clk), .rst_n(rst_n),
        .spi_mon_cs_n(spi_mon_cs_n), .spi_mon_sclk(spi_mon_sclk),
        .spi_mon_mosi(spi_mon_mosi), .spi_mon_miso(spi_mon_miso),
        .pkt_valid(spi_pkt_valid), .pkt_start(spi_pkt_start), .pkt_stop(spi_pkt_stop),
        .pkt_mosi(spi_pkt_mosi), .pkt_miso(spi_pkt_miso)
    );

    // ── SPI BRAM 
    wire        bram_we;
    wire [6:0]  bram_wr_addr;
    wire [15:0] bram_wr_data;
    reg  [6:0]  bram_rd_addr;
    wire [15:0] bram_rd_data;
    reg         arm_capture;
    wire        capture_done;
    wire [6:0]  capture_length;
    reg  [6:0]  saved_cap_len;

    spi_capture_bram u_bram (
        .clk(clk), .we(bram_we),
        .wr_addr(bram_wr_addr), .wr_data(bram_wr_data),
        .rd_addr(bram_rd_addr), .rd_data(bram_rd_data)
    );

    capture_controller u_capture_ctrl (
        .clk(clk), .rst_n(rst_n), .arm(arm_capture),
        .spi_valid(spi_pkt_valid), 
        .spi_stop(spi_pkt_stop),
        .spi_mosi(spi_pkt_mosi), .spi_miso(spi_pkt_miso),
        .wr_addr(bram_wr_addr), .wr_data(bram_wr_data), .we(bram_we),
        .capture_done(capture_done),
        .capture_length(capture_length)
    );

  // Host
    wire [7:0] host_rx_data;
    wire       host_rx_valid, tx_data_hold;
    reg        tx_hold_d;
    wire       tx_hold_rise;
    
    reg        readout_mode;   
    reg        read_len_mode;  
    reg        bram_byte_sel;  

    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) tx_hold_d <= 1'b0;
        else       tx_hold_d <= tx_data_hold;
    end
    assign tx_hold_rise = tx_data_hold & ~tx_hold_d;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            arm_capture   <= 1'b0;
            readout_mode  <= 1'b0;
            read_len_mode <= 1'b0;
            bram_rd_addr  <= 7'd0;
            bram_byte_sel <= 1'b0;
            saved_cap_len <= 7'd0;
        end else begin
            arm_capture <= 1'b0; 
            
            if (capture_done) saved_cap_len <= capture_length;
            
            if (host_rx_valid) begin
                if (host_rx_data == 8'hC1) begin 
                    arm_capture <= 1'b1; readout_mode <= 1'b0; read_len_mode <= 1'b0; 
                end
                else if (host_rx_data == 8'hC2) begin 
                    readout_mode <= 1'b1; read_len_mode <= 1'b0; bram_rd_addr <= 7'd0; bram_byte_sel <= 1'b0; 
                end
                else if (host_rx_data == 8'hC3) begin 
                    readout_mode <= 1'b0; read_len_mode <= 1'b0; 
                end
                else if (host_rx_data == 8'hC4) begin 
                    read_len_mode <= 1'b1; readout_mode <= 1'b0; 
                end
            end
            
            if (readout_mode == 1'b1 && tx_hold_rise) begin
                bram_byte_sel <= ~bram_byte_sel;
                if (bram_byte_sel == 1'b1) bram_rd_addr <= bram_rd_addr + 7'd1;
            end
        end
    end

   
    reg       fifo_wr_en;
    reg [7:0] fifo_wr_data;
    reg [2:0] tx_state;
    reg [7:0] saved_data;
    reg       saved_ack;
    reg       start_pending, stop_pending;
    reg       capture_done_d;

    localparam [2:0]
        S_IDLE   = 3'd0,
        S_UART_D = 3'd1,   
        S_I2C_V  = 3'd2,
        S_I2C_A  = 3'd3;

    wire capture_done_rise = capture_done & ~capture_done_d;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            fifo_wr_en     <= 1'b0;
            fifo_wr_data   <= 8'h00;
            tx_state       <= S_IDLE;
            saved_data     <= 8'h00;
            saved_ack      <= 1'b0;
            start_pending  <= 1'b0;
            stop_pending   <= 1'b0;
            capture_done_d <= 1'b0;
        end else begin
            fifo_wr_en     <= 1'b0;
            capture_done_d <= capture_done;

            if (pkt_start) start_pending <= 1'b1;
            if (pkt_stop)  stop_pending  <= 1'b1;

            if(tx_state == S_IDLE) begin
                if(capture_done_rise) begin
                    if(!fifo_full) begin
                        fifo_wr_en   <= 1'b1;
                        fifo_wr_data <= 8'hC0; 
                    end
                end
                else if(start_pending) begin
                    start_pending <= 1'b0;
                    if(!fifo_full) begin fifo_wr_en <= 1'b1; fifo_wr_data <= 8'h01; tx_state <= S_IDLE; end
                end
                else if(pkt_valid) begin
                    saved_ack <= pkt_ack;
                    if(pkt_is_addr) begin
                        saved_data <= pkt_addr;
                        if(!fifo_full) begin fifo_wr_en <= 1'b1; fifo_wr_data <= 8'h03; tx_state <= S_I2C_V; end
                    end else begin
                        saved_data <= pkt_data;
                        if(!fifo_full) begin fifo_wr_en <= 1'b1; fifo_wr_data <= 8'h04; tx_state <= S_I2C_V; end
                    end
                end
                else if(stop_pending) begin
                    stop_pending <= 1'b0;
                    if(!fifo_full) begin fifo_wr_en <= 1'b1; fifo_wr_data <= 8'h02; tx_state <= S_IDLE; end
                end
                else if(rx_data_ready) begin
                    saved_data <= rx_byte;
                    if(!fifo_full) begin fifo_wr_en <= 1'b1; fifo_wr_data <= 8'hF1; tx_state <= S_UART_D; end
                end
            end

            case (tx_state)
                S_UART_D: begin
                    if(!fifo_full) begin fifo_wr_en <= 1'b1; fifo_wr_data <= saved_data; tx_state <= S_IDLE; end
                end
                S_I2C_V: begin
                    if(!fifo_full) begin fifo_wr_en <= 1'b1; fifo_wr_data <= saved_data; tx_state <= S_I2C_A; end
                end
                S_I2C_A: begin
                    if(!fifo_full) begin fifo_wr_en <= 1'b1; fifo_wr_data <= saved_ack ? 8'h05 : 8'h06; tx_state <= S_IDLE; end
                end
            endcase
        end
    end

    // ── FIFO ─────────────────────────────────────────────────────────────────
    wire [7:0] fifo_data;
    wire fifo_empty, fifo_full, fifo_almost_empty, fifo_almost_full, fifo_overflow, fifo_underflow;
    reg  fifo_rd_en;

    uart_fifo #(.DATA_WIDTH(8), .DEPTH(16)) u_fifo (
        .clk(clk), .rst_n(rst_n), .wr_en(fifo_wr_en), .wr_data(fifo_wr_data),
        .rd_en(fifo_rd_en), .rd_data(fifo_data), .empty(fifo_empty), .full(fifo_full),
        .almost_empty(fifo_almost_empty), .almost_full(fifo_almost_full),
        .overflow(fifo_overflow), .underflow(fifo_underflow)
    );

  
    reg [7:0] tx_data;
    reg       pending_read;

    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            tx_data      <= 8'h00;
            fifo_rd_en   <= 1'b0;
            pending_read <= 1'b0;
        end else begin
            fifo_rd_en <= 1'b0;

            if(pending_read) begin
                fifo_rd_en   <= 1'b1;
                pending_read <= 1'b0;
            end

            if(tx_hold_rise) begin
                if (read_len_mode == 1'b1) begin
                    tx_data <= {1'b0, saved_cap_len};
                end else if (readout_mode == 1'b0) begin
                    if(!fifo_empty) begin
                        tx_data      <= fifo_data;
                        pending_read <= 1'b1;
                    end else begin
                        tx_data <= 8'h00;
                    end
                end else begin
                    tx_data <= bram_byte_sel ? bram_rd_data[7:0] : bram_rd_data[15:8];
                end
            end
        end
    end

  
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) led <= 1'b0;
        else if(rx_data_ready || pkt_valid || spi_pkt_valid || capture_done)
            led <= ~led;
    end

    // ── SPI Target 
    spi_target #(.CPOL(1'b0), .CPHA(1'b0), .WIDTH(8), .LSB(1'b0)) u_spi (
        .i_clk(clk), .i_rst_n(rst_n), .i_enable(1'b1),
        .i_ss_n(spi_ss_n), .i_sck(spi_sck), .i_mosi(spi_mosi),
        .o_miso(spi_miso), .o_miso_oe(spi_miso_en),
        .o_rx_data(host_rx_data), .o_rx_data_valid(host_rx_valid),
        .i_tx_data(tx_data), .o_tx_data_hold(tx_data_hold)
    );

endmodule