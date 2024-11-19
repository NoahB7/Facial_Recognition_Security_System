import RPi.GPIO as GPIO
import face_recognition
from PIL import Image
import cherrypy
import time
import random
import threading
import os
import tweepy
import pygame
import pygame.camera
from pygame.locals import *
from datetime import datetime


pygame.init()
pygame.camera.init()
cam = pygame.camera.Camera("/dev/video0", (640,480))
api = tweepy.API()
BtnPin = 16
TRIG   = 11
ECHO   = 12
BuzzerPin = 13
ds18b20 = ''
running = False
alert = ''

class Page:
    @cherrypy.expose
    def index(self):
        global running
        if running:
            running = False
            self.destroy()
        return """<!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <title>Security System</title>
                    <link href="/static/css/styles1.css" rel="stylesheet">
                </head>
                <body class = "bod">
<div class = "spacer">
</div>
                <div>
                <h1 class ="title"> Security System &trade; </h1>
                </div>
                <form method="get" action="/remoteStart">
                    <button class = "btn">Turn On</button>
                </form>
                <div class="temp">
                <p>Current Tempature: </p>
                <p>Not currently on</p>
                </div>
                <div class ="alert"><h1> ALERTS: <h1>
                """ + alert +"""
                </div>
                </body>
                </html>"""


    @cherrypy.expose
    def remoteStart(self):
        print(alert)
        global running
        if not running:
            self.setup()
            running = True
            t = threading.Thread(target=self.sensors)
            t.daemon
            t.start()
        temp = self.read()
        return """<!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <title>Security System</title>
                    <script type = "text/javascript">
                        function autoRefreshPage()
                        {
                            window.location = window.location.href
                        }
                        setInterval('autoRefreshPage()', 1000);
                    </script>
                    <link href="/static/css/styles1.css" rel="stylesheet">
                </head>
               
                <body class = "bod">
<div class = "spacer">
</div>
                <div>
                <h1 class ="title"> Security System &trade; </h1>
                </div>
                <form method="get" action="/index">
                    <button class = "btn">Turn Off</button>
                </form>
                <div class="temp"><p> Current Tempature: </p>
                <p>""" + str(temp) + """</p> </div>
<div class = "alert"> <h1> ALERTS: <h1>""" + alert +"""
                </div>
                </body>
                </html>"""



    def sensors(self):
        self.button()
       
    def setup(self):
        GPIO.setmode(GPIO.BOARD)
        #ultrasonic ranging module setup
        GPIO.setup(TRIG, GPIO.OUT)
        GPIO.output(TRIG, GPIO.HIGH)
        GPIO.setup(ECHO, GPIO.IN)
        #buzzer setup
        GPIO.setup(BuzzerPin, GPIO.OUT)
        GPIO.output(BuzzerPin, GPIO.HIGH)
        #button setup
        GPIO.setup(BtnPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)    # Set BtnPin's mode is input, and pull up to high level(3.3V)
        GPIO.add_event_detect(BtnPin, GPIO.BOTH, callback=self.detect, bouncetime=200)
        #tempature setup
        global ds18b20
        for i in os.listdir('/sys/bus/w1/devices'):
                if i != 'w1_bus_master1':
                        ds18b20 = '28-01201f862d36'
                       
    def distance(self):
        GPIO.output(TRIG, 0)
        time.sleep(0.000002)

        GPIO.output(TRIG, 1)
        time.sleep(0.00001)
        GPIO.output(TRIG, 0)

        while GPIO.input(ECHO) == 0:
                a = 0
        time1 = time.time()
        while GPIO.input(ECHO) == 1:
                a = 1
        time2 = time.time()
        during = time2 - time1
        return during * 340 / 2 * 100

    def button(self):
        global api
        global running
        global cam
        while running:
            if GPIO.input(BtnPin)==0:
                break
            dis = self.distance()
            if(dis < 20):
                cam.start()
                t = time.time()
                t = datetime.fromtimestamp(t)
                global alert
                img = cam.get_image()
                pygame.image.save(img, 'image_2.jpg')
                results = [False]
                cam.stop()
                try:  
                    known_image = face_recognition.load_image_file('image_1.jpg')
                    unknown_image = face_recognition.load_image_file('image_2.jpg')

                    known_encoding = face_recognition.face_encodings(known_image)[0]
                    unknown_encoding = face_recognition.face_encodings(unknown_image)[0]

                    results = face_recognition.compare_faces([known_encoding], unknown_encoding)
                    if not results[0]:
                        alert += ('<p>Motion detected : ({dist} cm) ['.format(dist = int(dis)))
                        alert += str(t)
                        alert += ']</p>'
                        thread = threading.Thread(target=self.threadedbeep)
                        thread.daemon
                        thread.start()
                        media = api.media_upload('image_2.jpg')
                        tweet = "Intruder detected!" + str(t)
                        api.update_status(status = tweet, media_ids = [media.media_id])
                except:
                    alert += ('<p>Motion detected : ({dist} cm) ['.format(dist = int(dis)))
                    alert += str(t)
                    alert += ']</p>'
                    thread = threading.Thread(target=self.threadedbeep)
                    thread.daemon
                    thread.start()
                    media = api.media_upload('image_2.jpg')
                    tweet = "Movement detected!" + str(t)
                    api.update_status(status = tweet, media_ids = [media.media_id])
                   
            print (int(dis),'cm')
            print ('')
            time.sleep(0.5)


    def on(self):
        GPIO.output(BuzzerPin, GPIO.LOW)

    def off(self):
        GPIO.output(BuzzerPin, GPIO.HIGH)
       
    def threadedbeep(self):
        for i in range(3):
            self.on()
            time.sleep(0.5)
            self.off()
            time.sleep(0.5)

    def beep(self,x):
        self.on()
        time.sleep(x)
        self.off()
        time.sleep(x)

    def read(self):
#       global ds18b20
        location = '/sys/bus/w1/devices/' + ds18b20 + '/w1_slave'
        tfile = open(location)
        text = tfile.read()
        tfile.close()
        secondline = text.split("\n")[1]
        temperaturedata = secondline.split(" ")[9]
        temperature = float(temperaturedata[2:])
        temperature = temperature / 1000
        return temperature
   
    def destroy(self):
        GPIO.output(TRIG, GPIO.HIGH)
        GPIO.output(BuzzerPin, GPIO.HIGH)
        GPIO.cleanup()                     # Release resource
   
    def detect(self,chn):
        pass



if __name__ == '__main__':
    conf = {
        '/': {
            'tools.staticdir.root': os.getcwd()
            },
        '/static': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': 'public'
            }
        }
    APP_KEY = 'msSEqlAM2E46GYKRVdDT5TybY'
    APP_SECRET = 'u7UWElEZPyzLRf40oza623cLmiW2O0xmah3vltLMqydTGz2aXN'
    OAUTH_KEY = '1456346752924094465-UlqKscWKOjYANwsJFVFaCb02hBM8M2'
    OAUTH_SECRET = 'CVwC5KnVyvG7iUHj0U1yHkzLcSgKhF1euQJgNvn6X8bTV'

    auth = tweepy.OAuthHandler(APP_KEY, APP_SECRET)
    auth.set_access_token(OAUTH_KEY, OAUTH_SECRET)
    api = tweepy.API(auth)
   
   
    cherrypy.quickstart(Page(), '/', conf)

