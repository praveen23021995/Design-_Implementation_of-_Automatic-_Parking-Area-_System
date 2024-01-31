from machine import ADC , I2C
import time
from lib.pycoproc_1 import Pycoproc
from lib.LTR329ALS01 import LTR329ALS01
from machine import Pin
from network import WLAN
import socket
from i2c_lcd import I2cLcd 
import _thread
from mqtt import MQTTClient
import json
import machine

import _thread

last_entry_time = None

wlan = WLAN() # get current object, without changing the mode
if machine.reset_cause() != machine.SOFT_RESET:
    wlan.init(mode=WLAN.STA)

if not wlan.isconnected():
    # change the line below to match your network ssid, security and password
    wlan.connect('praveen', auth=(WLAN.WPA2, 'praveen123'), timeout=5000)
    print("connecting",end='')
    while not wlan.isconnected():
        time.sleep(1)
        print(wlan.ifconfig())
    print("connected")

def settimeout(duration): 
     pass

client = MQTTClient("Zain", "192.168.98.134", port=1883)
client.settimeout = settimeout 
client.connect()

# Car entry log list
car_entry_log = []
    
i2c = I2C(0)                         # create on bus 0
i2c = I2C(0, I2C.MASTER)             # create and init as a master
i2c = I2C(0, pins=('P9','P10'))     # create and use non-default PIN assignments (P10=SDA, P11=SCL)
i2c.init(I2C.MASTER, baudrate=20000)


devices = i2c.scan()
if devices:
    print("I2C devices found at addresses:", devices)
else:
    print("No I2C devices found")

lcd = I2cLcd(i2c, 0x27, 2, 16)
adc = ADC()
adc_c = adc.channel(pin='P16', attn=ADC.ATTN_11DB)
adc_c()




def message_handler(topic, msg):
    global car_count, available_slots
    if topic == b"/traffic":
        message = msg.decode()
        if available_slots <= 3 and car_count != 0:
            if message.startswith("Car Count:"):
                try:
                    received_count = int(message.split(":")[1].strip())
                    car_count = max (0, car_count - received_count)  # Update car_count with the received value
                    available_slots += 1
                    lcd.clear()
                    lcd.putstr("Car Count: {}".format(car_count))
                    lcd.move_to(0, 1)
                    lcd.putstr("Free Slots: {}".format(available_slots))
                    current_time = get_current_time()
                    log_data = {
                    "Car Count": car_count,
                    "Free Slots": available_slots,
                    "car exit time": current_time
                    }
                    log_message = json.dumps(log_data)
                    client.publish("/logMaster", log_message)
                    print("Car Count: {}".format(car_count), "Available Slots: {}".format(available_slots))
                except ValueError:
                    print("Invalid message format")
        else:
            print("false alarm from exit")
            client.publish("/logMaster", "false alarm from exit")
    elif topic == b"/keep_alive":
        message = msg.decode()
        try:
            green_light.value(1)
            time.sleep(1)
            green_light.value(0)
            time.sleep(1)
        except ValueError:
            print("Invalid message format")
    else:
        green_light.value(0)
    return

client.set_callback(message_handler)
client.subscribe("/traffic")
client.subscribe("/keep_alive")


threshold = 1000
# Initialize car counter
car_count = 0
available_slots = 3
print(threshold,"threshold")
# Initialize a flag to track car presence (initially no car)
car_present = False
button_pin = Pin('P21', mode=Pin.IN, pull=Pin.PULL_UP)
green_light = Pin('P8', mode=Pin.OUT)
green_led = Pin('P2', mode=Pin.OUT)
yellow_led = Pin('P3', mode=Pin.OUT)
red_led = Pin('P4', mode=Pin.OUT)
payment_button = Pin('P7', mode= Pin.IN )
payment_done = Pin('P6', mode=Pin.OUT)
lcd.clear()
lcd.putstr("Car Count: {}".format(car_count))
# Set cursor to the start of the second line
lcd.move_to(0, 1)
lcd.putstr("Free Slots: {}".format(available_slots))


def publish_traffic_log(car_count, available_slots, formatted_time):
    log_data = {
        "Car Count": car_count,
        "Free Slots": available_slots,
        "car entry time": formatted_time
    }
    log_message = json.dumps(log_data)  # Convert the log data to a JSON string
    print(log_message)
    client.publish("/logMaster", log_message)  # Publish the log message to the /traffic/test_log topic

rtc = machine.RTC()
rtc.ntp_sync("pool.ntp.org")
while not rtc.synced():
    machine.idle()
print("RTC synced with NTP time")
time.timezone(2*60**2)

def get_current_time():
    current_time_tuple = time.localtime()
    # Extract hour, minute, and second from the current time tuple
    hour, minute, second = current_time_tuple[3:6]
    # Format the time as "hour:minute:second"
    formatted_time = "{:02}:{:02}:{:02}".format(hour, minute, second)
    return formatted_time

# Main loop
while True:
    client.check_msg()

    # Read the analog value from the LDR sensor
    ldr_value = adc_c.value()
    


    # Print the LDR value to the console
    print("LDR Value:", ldr_value)

    if button_pin.value() == 0:
        print("payment done")
        current_time = get_current_time()
        client.publish("/logMaster", "Payment Done : {}".format(current_time))
        time.sleep(0.2)  # Debounce the button
    time.sleep(0.01)

    if ldr_value > threshold:
        if not car_present:
            if car_count < 3:
            # A car has entered
                car_count = car_count+1
                car_present = True
                # Get the current entry time
                # entry_time = time.localtime()
                # print(entry_time)
                lcd.clear()
                lcd.putstr("Car Count: {}".format(car_count))
                # Calculate the number of available slots
                available_slots = max(0, 3 - car_count)
                # Set cursor to the start of the second line
                lcd.move_to(0, 1)
                lcd.putstr("Free Slots: {}".format(available_slots))
                # current_time_tuple = time.localtime()
                # hour, minute, second = current_time_tuple[3:6]
                current_time = get_current_time()
                # formatted_time = "{:02}:{:02}:{:02}".format(hour, minute, second)
                publish_traffic_log(car_count, available_slots,current_time)  # Publish traffic/test log data
                # client.publish("/traffic/test", "Car Count: {}".format(car_count))
                time.sleep(1)
            else:

                print("Parking is full. Cannot accept more cars.")
                client.publish("/logMaster", "Parking is full. Cannot accept more cars.")
          
    else:
        if car_present:
            # A car has exited
            car_present = False
     
     # Update LED colors based on available slots
    if available_slots == 0:
        # No available slots, turn on the red LED
        red_led.value(1)
        yellow_led.value(0)
        green_led.value(0)
    elif available_slots <= 2:
        # 1 or 2 slots available, blink the yellow LED
        red_led.value(0)
        yellow_led.value(1)
        green_led.value(0)
    else:
        # 3 slots available, turn on the green LED
        red_led.value(0)
        yellow_led.value(0)
        green_led.value(1)
    
    client.check_msg()
    
    

    # Delay for a short interval before the next reading (e.g., 1 second)
    time.sleep(1)