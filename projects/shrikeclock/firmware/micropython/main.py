from machine import Pin
import time

# ---- PIN MAPPING (apne hisab se badal le) ----
# Shrike-Fi (ESP32-S3) safe pins — avoids GPIO 8,9,10,11,12,13 (FPGA bus),
# GPIO21 (onboard LED), GPIO0/3/45/46 (strapping), GPIO19/20 (USB)
SEG_PINS = {
    'a': 1, 'b': 2, 'c': 4, 'd': 5,
    'e': 6, 'f': 7, 'g': 14, 'dp': 15
}
DIGIT_PINS = [16, 17, 18, 33, 34, 35]  # digit1..digit6 — confirmed working

# Common anode: segment pin LOW = ON, digit pin HIGH = digit selected
SEGMENT_MAP = {
    '0': 'abcdef',
    '1': 'bc',
    '2': 'abged',
    '3': 'abgcd',
    '4': 'fgbc',
    '5': 'afgcd',
    '6': 'afgedc',
    '7': 'abc',
    '8': 'abcdefg',
    '9': 'abcdfg',
    ' ': '',
    '-': 'g',
}

segs = {}
for name, pin_num in SEG_PINS.items():
    p = Pin(pin_num, Pin.OUT)
    p.value(1)  # OFF (common anode: HIGH = off)
    segs[name] = p

digits = []
for pin_num in DIGIT_PINS:
    p = Pin(pin_num, Pin.OUT)
    p.value(0)  # OFF (common anode: LOW = not selected)
    digits.append(p)


def set_segments(char, dot=False):
    on_segs = SEGMENT_MAP.get(char, '')
    for name, pin in segs.items():
        if name == 'dp':
            pin.value(0 if dot else 1)
        else:
            pin.value(0 if name in on_segs else 1)


def all_off():
    for pin in segs.values():
        pin.value(1)
    for pin in digits:
        pin.value(0)


def display_number(number, duration_ms=2000):
    """Multiplex-display a number (max 6 digits) for duration_ms using time-slicing.
    Call this in a loop, or use display_once() inside your own loop for non-blocking use."""
    s = str(number)
    if len(s) > 6:
        s = s[-6:]
    s = (' ' * (6 - len(s))) + s   # manual rjust (MicroPython has no str.rjust)

    start = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), start) < duration_ms:
        for i, ch in enumerate(s):
            for d in digits:
                d.value(0)
            set_segments(ch)
            digits[i].value(1)
            time.sleep_ms(3)   # per-digit ON time
            digits[i].value(0)


import network
import ntptime

# ---- WiFi & Timezone config  ----
WIFI_SSID = "ssid"
WIFI_PASSWORD = "pass"
TZ_OFFSET_HOURS = 5.5   # India = UTC+5:30
RESYNC_EVERY_MS = 3600000  


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        timeout = time.ticks_ms()
        while not wlan.isconnected():
            if time.ticks_diff(time.ticks_ms(), timeout) > 25000:
                raise RuntimeError("WiFi connect failed - check SSID/password")
            time.sleep_ms(200)
    print("WiFi connected:", wlan.ifconfig())


def sync_ntp():
    ntptime.host = "pool.ntp.org"
    ntptime.settime()   # sets RTC to UTC
    print("NTP time synced")


def get_local_time_str():
    # RTC has UTC; add TZ offset
    offset_sec = int(TZ_OFFSET_HOURS * 3600)
    t = time.localtime(time.time() + offset_sec)
    hh, mm, ss = t[3], t[4], t[5]
    return "{:02d}{:02d}{:02d}".format(hh, mm, ss)


def get_local_date_str():
    offset_sec = int(TZ_OFFSET_HOURS * 3600)
    t = time.localtime(time.time() + offset_sec)
    dd, mo, yy = t[2], t[1], t[0] % 100
    return "{:02d}{:02d}{:02d}".format(dd, mo, yy)


def show_frame(s, dots=()):
    
    for i, ch in enumerate(s):
        for d in digits:
            d.value(0)
        set_segments(ch, dot=(i in dots))
        digits[i].value(1)
        time.sleep_ms(3)
        digits[i].value(0)


def boot_animation():
    
    order = ['a', 'b', 'c', 'd', 'e', 'f', 'g']
    for _ in range(2):  
        for seg_name in order:
            for d in digits:
                d.value(0)
            for name, pin in segs.items():
                pin.value(0 if name == seg_name else 1)
            for d in digits:
                d.value(1)
            time.sleep_ms(60)
            for d in digits:
                d.value(0)
    all_off()
    time.sleep_ms(200)


# ---- NTP Clock ----
if __name__ == '__main__':
    boot_animation()
    connect_wifi()
    sync_ntp()
    last_resync = time.ticks_ms()
    blink_state = True
    last_blink = time.ticks_ms()

    # Time/Date toggle settings
    SHOW_TIME_MS = 8000   
    SHOW_DATE_MS = 2500   
    mode = 'time'
    mode_start = time.ticks_ms()

    try:
        while True:
            now = time.ticks_ms()

            if time.ticks_diff(now, last_blink) >= 500:
                blink_state = not blink_state
                last_blink = now

            if mode == 'time':
                if time.ticks_diff(now, mode_start) >= SHOW_TIME_MS:
                    mode = 'date'
                    mode_start = now
                s = get_local_time_str()
                dots = (1, 3) if blink_state else ()  # blinking colon
            else:
                if time.ticks_diff(now, mode_start) >= SHOW_DATE_MS:
                    mode = 'time'
                    mode_start = now
                s = get_local_date_str()
                dots = (1, 3)  

            show_frame(s, dots=dots)

            if time.ticks_diff(now, last_resync) >= RESYNC_EVERY_MS:
                try:
                    sync_ntp()
                except Exception as e:
                    print("Resync failed:", e)
                last_resync = time.ticks_ms()
    except KeyboardInterrupt:
        all_off()
