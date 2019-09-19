import RPi.GPIO as GPIO # Import Raspberry Pi GPIO library
import time
from bluepy import btle
import binascii
import threading


def now(): # type: String like 2000-01-01 14:38:40
    return time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))

def gen_interval(length, interval_type="MILLISECONDS"):
    def gen_interval_in_seconds(secs):
        milliseconds_multi = 1000
        return secs * milliseconds_multi, (length, interval_type)

    def gen_interval_in_minutes(minutes):
        milliseconds_multi = 1000
        seconds_multi = 60
        return minutes * milliseconds_multi * seconds_multi, (length, interval_type)

    if interval_type == "MINUTES":
        return gen_interval_in_minutes(length)
    elif interval_type == "SECONDS":
        return gen_interval_in_seconds(length)
    else:  # In milliseconds
        return length, (length, interval_type)

def log(text):
    with open(log_filename, 'a') as log_file:
        print(now() + " " + text, file=log_file)

def open_garage_light(): 

    '''
    Connect to your LOLAR Bluetooth Low Energy switch and turn it on;
    Try to turn it on within `connect_ble_time_limit` seconds,
    if not successful (due to ble issues) then abort this try
    '''
    connect_ble_time_limit = 60 # in seconds
    time_limit = time.time() + connect_ble_time_limit
    dev = None # BLE device
    while (time.time() < time_limit):
        while (dev is None and time.time() < time_limit): # while BLE device is occupied, wait
            try:
                dev = btle.Peripheral(mac_address)
            except btle.BTLEException:
                time.sleep(0.5)
        # since now BLE switch is connected to RPi
        try:
            light_switch = btle.UUID("FFF0")
            light_service = dev.getServiceByUUID(light_switch)
            switch_control = light_service.getCharacteristics()[0]
            switch_status = light_service.getCharacteristics()[1]
            status = switch_status.read()
            status = binascii.b2a_hex(status)

            if status[1] == 49: # ascii 1
                # print('the light is already on')
                pass
            if status[1] == 48: # ascii 0
                # print('the light is off, turning it on')
                switch_control.write(bytes("\x01", encoding='utf8'))
                time.sleep(1) # give BLE some time to communicate
            dev.disconnect() # Don't forget to disonnect BLE
            break

        except btle.BTLEException:
            dev = None
            time.sleep(0.5)

    success = True
    if time.time() > time_limit:
        return not success
    else:
        return success

def close_garage_light():    
    '''
    Connect to your LOLAR Bluetooth Low Energy switch and turn it off;
    Try to turn it off within `connect_ble_time_limit` seconds,
    if not successful (due to ble issues) then abort this try
    '''
    connect_ble_time_limit = 60 # in seconds
    time_limit = time.time() + connect_ble_time_limit
    dev = None # BLE device
    while (time.time() < time_limit):
        while (dev is None and time.time() < time_limit): # while BLE device is occupied, wait
            try:
                dev = btle.Peripheral(mac_address)
            except btle.BTLEException:
                time.sleep(3)
        # since now BLE switch is connected to RPi
        try:
            light_switch = btle.UUID("FFF0")
            light_service = dev.getServiceByUUID(light_switch)
            switch_control = light_service.getCharacteristics()[0]
            switch_status = light_service.getCharacteristics()[1]
            status = switch_status.read()
            status = binascii.b2a_hex(status)
            if status[1] == 49: # ascii 1
                # print('the light is on, turn it off')
                switch_control.write(bytes("\x01", encoding='utf8'))
                time.sleep(1) # give BLE some time to communicate
            elif status[1] == 48: # ascii 0
                # print('the light is already off')
                pass

            dev.disconnect() # Don't forget to disonnect BLE
            break

        except btle.BTLEException:
            dev = None
            time.sleep(3)
    success = True
    if time.time() > time_limit:
        return not success
    else:
        return success

def double_check_is_human():
    """
    If the signal from sensor is only a short single square wave,
    then after one second, there should not be high voltage any more.
    we double check by detecting high voltage after a short pause,
    because if its human moving around, there should be fairly high
    possibility that RPi could sample another high voltage within 5 seconds
    """
    time.sleep(1)
    log("[INFO] Double checking...")
    t0 = time.time()
    t1 = t0 + 5 # in seconds
    is_human = False
    while time.time() < t1:
        time.sleep(0.2) # sample frequency, could decrease it to be more efficient
        if GPIO.input(pin_control) == 1:
            is_human = True
            return is_human
    if not is_human:
        return False

def human_sensed_callback(channel):
    GPIO.remove_event_detect(pin_control) # don't trigger event until done with the current one
    log("[INFO] Sensed something, stopped listening to sensor.")

    is_human = double_check_is_human() # in case of false positive trigger by sensor
    if is_human:
        log("[SUCCESS] Human confirmed!")
        success = open_garage_light()
        if success:
            log("[SUCCESS] Light is on!")
            log("[INFO] Closing light in %d seconds." % (time_before_close))
            time.sleep(time_before_close)
            closed_success = close_garage_light()
            if closed_success:
                log("[SUCCESS] Light is off!")
            else:
                log("[FAILED] BLE exceeds time limit, abort closing!")
        else:
            log("[FAILED] BLE exceeds time limit, abort opening!")
    else:
        log("[INFO] Not human. Sensor False Positive.")

    GPIO.add_event_detect(pin_control, GPIO.RISING, bouncetime=detect_interval, callback=human_sensed_callback) # Setup event on rising edge
    log("[INFO] Resumed listening to sensor.\n")







# ******* YOU NEED TO SETUP YOUR MAC_ADDRESS   ******* #
# ******* WHICH IS "FF:FF:FF:FF:FF:FF" NOW!    ******* #
# ******* CHANGE IT TO YOUR DEVICE MAC ADDRESS ******* #
# If you don't know what it is, use LightBlue on iOS to findout *
mac_address = "ff:ff:ff:ff:ff:ff"

pin_control = 14 #RPi BCM mode pin
log_filename = 'sense_human_logs.txt'
detect_interval, (interval, interval_type) = gen_interval(300, "MILLISECONDS") # bounce time
time_before_close = 60 * 5 # seconds


with open(log_filename, 'a') as log_file:
    print("\n\n\n" + now() + " [INFO] Pi Human Sensor Starting...", file=log_file)
    print("[INFO] Configuration:", file=log_file)
    print("[INFO] \tPIN: Raspberry Pi BCM MODE %d" % (pin_control), file=log_file)
    print("[INFO] \tDETECT_INTERVAL: %d %s" % (interval, interval_type), file=log_file)


GPIO.setmode(GPIO.BCM) # Use BCM 2019.8.24

GPIO.setup(pin_control, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # Set pin 14 to be an input pin and set initial value to be pulled low (off)

GPIO.add_event_detect(pin_control, GPIO.RISING, bouncetime=detect_interval, callback=human_sensed_callback) # Setup event on rising edge



while(1):
    time.sleep(10)

# GPIO.cleanup() # Clean up




