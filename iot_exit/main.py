from machine import ADC , I2C
import time
from lib.LTR329ALS01 import LTR329ALS01
from machine import Pin
from network import WLAN
import socket
from i2c_lcd import I2cLcd 
import _thread
from mqtt import MQTTClient
from lib.MPL3115A2 import MPL3115A2,ALTITUDE,PRESSURE
import machine

last_entry_time = None
wlan = WLAN(mode=WLAN.STA) # get current object, without changing the mode


adc = ADC()
adc_c = adc.channel(pin='P16', attn=ADC.ATTN_11DB)
adc_c()

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
  
client = MQTTClient("Transmitter", "192.168.98.134", port=1883)
client.settimeout = settimeout
client.connect()

# adc = ADC()
# adc_c = adc.channel(pin='P16', attn=ADC.ATTN_11DB)
# adc_c()
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


threshold = 2000
# Initialize car counter
car_count = 0
available_slots =3
# Initialize a flag to track car presence (initially no car)
car_present = False
green_led = Pin('P2', mode=Pin.OUT)
counter = 0
# Main loop
while True:
    
    

    ldr_value = adc_c.value()
    # Print the LDR value to the console
    print("LDR Value:", ldr_value)

    if ldr_value > threshold:
        if not car_present:
            # A car has entered
            car_count = 1
            car_present = True
            # Get the current entry time
            entry_time = time.localtime()
            print(entry_time)
            
            available_slots = max(0, 3 - car_count)
            current_time  = get_current_time()
            client.publish("/traffic","Car Count: {}".format(car_count) )
            
            time.sleep(5)
        
    else:
        if car_present:
            # A car has exited
            car_present = False
    
    counter += 1
    print(counter,"counter")
    if counter == 2:
        client.publish("/keep_alive", "connection")
        time.sleep(1)
        counter = 0
    
    # Print the car count and available slots to the console
    print("Car Count:", car_count)

    # Delay for a short interval before the next reading (e.g., 1 second)
    time.sleep(1)