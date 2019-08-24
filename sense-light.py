import RPi.GPIO as GPIO # Import Raspberry Pi GPIO library
import time
from bluepy import btle
import binascii

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


def open_garage_light():    
    '''
    ******* YOU NEED TO SETUP YOUR MAC_ADDRESS   *******
    ******* WHICH IS "FF:FF:FF:FF:FF:FF" NOW!    *******
    ******* CHANGE IT TO YOUR DEVICE MAC ADDRESS *******
    Connect to your LOLAR Bluetooth Low Energy switch and turn it on;
    Try to turn it on within `connect_ble_time_limit` seconds,
    if not successful (due to ble issues) then abort this try
    '''
    mac_address = "ff:ff:ff:ff:ff:ff" # YOUR BLE switch mac address
    connect_ble_time_limit = 60 # YOUR connect limit time in seconds

    time_limit = time.time() + connect_ble_time_limit
    dev = None # BLE device
    while (time.time() < time_limit):

        # while BLE device is occupied, wait
        while (dev is None and time.time() < time_limit): 
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
                # the light is already on
                pass
            elif status[1] == 48: # ascii 0
                # the light is off, turning it on
                switch_control.write(bytes("\x01", encoding='utf8'))

            # Don't forget to disonnect BLE
            dev.disconnect() 
            break

        except btle.BTLEException:
            dev = None
            time.sleep(3)


    if time.time() > time_limit:
        return " [FAILED] Exceeds time limit, abort!"
    else:
        return " [SUCCESS] Human detected, light is on!"

def human_sensed_callback(channel):
    response = open_garage_light()
    with open(log_filename, 'a') as log_file:
        print(now() + " [Alert] Sensed something!", file=log_file)
        print(now() + response, file=log_file)
        print(now() + " [INFO] Will be sleeping for %d %s...\n" %(interval, interval_type), file=log_file)


pin_control = 14 #RPi BCM mode pin
log_filename = 'sense_human_logs.txt'
detect_interval, (interval, interval_type) = gen_interval(10, "MINUTES") # wait 10 minutes for another detection 

# Init
with open(log_filename, 'a') as log_file:
    print(now() + " [INFO] Start sensing human")
    print("\n\n\n" + now() + " [INFO] Pi Human Sensor Starting...", file=log_file)
    print("[INFO] Configuration:", file=log_file)
    print("[INFO] \tPIN: Raspberry Pi BCM MODE %d" % (pin_control), file=log_file)
    print("[INFO] \tDETECT_INTERVAL: %d %s" % (interval, interval_type), file=log_file)
    print(now() + " [INFO] Start sensing human...\n", file=log_file)

# Use pi BCM mode
GPIO.setmode(GPIO.BCM) 

# Set pin 14 to be an input pin and set initial value to be pulled low
GPIO.setup(pin_control, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) 

# Setup event on rising edge
GPIO.add_event_detect(pin_control, GPIO.BOTH, bouncetime=detect_interval, callback=human_sensed_callback) 


while(1):
    time.sleep(10)

# GPIO.cleanup() # Clean up

