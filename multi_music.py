#!/usr/bin/python3

import os
import time
import random
import threading
import subprocess
import re
import RPi.GPIO as GPIO
from RPLCD import CharLCD
from subprocess import Popen, PIPE
from gpiozero import LED, Button

# Methods for scrolling text on LCD screen
def write_to_lcd(lcd, display_string, row, num_cols):
    threadLock.acquire()
    lcd.cursor_pos = (row, 0)
    lcd.write_string(display_string[:num_cols])
    threadLock.release()
    #lcd.write_string('\r\n')

def loop_string(string, lcd, row, num_cols, delay=0.5):
    # DELAY= CONTROLS THE SPEED OF SCROLL
    padding = ' ' * 2
    s = string + padding
    for i in range(len(s) - num_cols + 1):
        write_to_lcd(lcd, s[i:i+num_cols], row, num_cols)
        time.sleep(delay)

class displayThread (threading.Thread):
    def __init__(self, threadID, name, lcd):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.lcd = lcd
        self.display_top = ''
        self.display_bot = ''

    def run(self):
        print("Starting Display Thread... " + self.name)
        while exitFlag < 1:
            threadLock.acquire()
            self.display_top = current_artist
            self.display_bot = current_song
            threadLock.release()
            print(self.display_top + " - " + self.display_bot)
            write_to_lcd(self.lcd, "{:<16}".format(self.display_top), 0, 16)
            if len(self.display_bot) > 16:
                print("scrolling text: " + self.display_bot)
                # Only scroll first 30 characters of song
                loop_string(self.display_bot[:30], self.lcd, 1, 16)
            else:
                print("Text short:     " + self.display_bot)
                write_to_lcd(self.lcd, "{:<16}".format(self.display_bot), 1, 16)
                time.sleep(0.5)
            
        print(self.name + ": Time to Exit!")

class musicThread (threading.Thread):
    def __init__(self, threadID, name):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name

    def run(self):
        print("Starting Music Thread... " + self.name)
        while exitFlag < 1:
            #print(self.name + ": Playlist len: " + str(len(playlist)))
            #print(self.name + ":  Play Status: " + str(play_status))
            if len(playlist) > 0 and play_status > 0:
                #song_file = "/media/pi/Backup Plus/Music/Tyler Childers/White House Road (OurVinyl Sessions).mp3"
                #artist = 'Tyler Childers'
                #song = 'White House Road (OurVinyl Sessions)'
                #song = 'White House'
                threadLock.acquire()
                playlist_item = playlist[current_song_number]
                item_key = playlist_item[0]
                song_file = playlist_item[1]
                artist, song = item_key.split('|')
                global current_artist
                current_artist = artist
                global current_song
                current_song = song
                threadLock.release()
                print(str(current_song_number) + " playing: " + song)
                my_process = Popen(['omxplayer', song_file], stdout=PIPE, stdin=PIPE)
                threadLock.acquire()
                global music_process
                music_process = my_process
                threadLock.release()
                #os.system('omxplayer ' + song_file)
                print(self.name + ": Song Playing....")
                my_process.wait()
                print(self.name + ": Finished Playing " + song)
                threadLock.acquire()
                global current_song_number
                current_song_number += 1
                if current_song_number == len(playlist) or current_song_number < 0:
                    current_song_number = 0
                threadLock.release()
            else:
                print(self.name + ": Ready to play...")
                time.sleep(0.5)


def send_control(user_input):
    print("sending control to music process: " + user_input)
    threadLock.acquire()
    try:
        global music_process
        poll = music_process.poll()
        if poll is None:
            music_process.stdin.write(user_input.encode())
            music_process.stdin.flush()
        else:
            print("Process already terminated...moving on!")
    except:
        print("ERROR: trying to get music process (may not exist)")
        pass
    threadLock.release()
    #result = music_process.communicate(input=user_input.encode())
    #print(result.decode('utf-8'))

# Shutdown the system
def shutdown():
    print("SHUTDOWN! SHUTDOWN!")
    send_control("q")
    threadLock.acquire()
    global exitFlag
    exitFlag = 1
    threadLock.release()
    time.sleep(0.5)
    print("SHUTDOWN IN PROGRES...")
    # Let threads all end and shutdown system at the end

# Get playlist ready
def load_playlist(playlist_number):
    print("Loading Playlist #" + str(playlist_number))
    threadLock.acquire()
    # set to display on LCD
    global current_artist
    current_artist = "Load Playlist " + str(playlist_number)
    global current_song
    current_song = '                '
    # stop current playing
    global play_status
    play_status = 0
    threadLock.release()
    send_control("q")
    threadLock.acquire()
    # empty current playlist
    global playlist
    playlist = []

    # Playlists available to load
    playlists = ['/jinks&friends.m3u', '/rock.m3u', '/pop_hip_hop.m3u']
    
    # Get playlist ready
    # Playlist path
    playlist_path = '/home/pi/.kodi/userdata/playlists/music'
    playlist_file = open(playlist_path + playlists[playlist_number - 1], 'rb')
    playlist_count = 0
    my_regex = "\(.*\)"

    for line in playlist_file:
        #print(line)
        if not line.startswith(b'#'):
            playlist_count += 1
            current_song = '# songs: ' + str(playlist_count)
            song_path = line.decode('utf-8').replace('\r', '').replace('\n', '')
            artist_song = song_path.replace('/media/pi/Backup Plus/Music/', '')
            #print(artist_song)
            artist_song = artist_song
            artist_song_split = artist_song.split('/')
            artist = artist_song_split[0]
            song = artist_song_split[-1]
            # Clean song (.mp3 & anything in brackets)
            song = song.replace('.mp3', '')
            song = re.sub(my_regex, "", song)
            song_key = artist + "|" + song
            #print(song_key)
            playlist.append((song_key, song_path))
    random.shuffle(playlist)
    # set flag to continue playing
    play_status = 1
    threadLock.release()
    print("Playlist #" + str(playlist_number) + " Loaded!")
    # only adding a delay for human time to read LCD
    time.sleep(1.5)

    
class controlThread (threading.Thread):
    def __init__(self, threadID, name):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.playing = False

        # Playlist Buttons
        self.playlist_1_btn = Button(14)
        self.playlist_2_btn = Button(15)
        self.playlist_3_btn = Button(18)

        # Control Buttons
        self.prev_button = Button(25)
        self.pause_play_button = Button(8)
        self.next_button = Button(7)
        self.shutdown_button = Button(3, hold_time=3)
        self.shutdown_button.when_held = shutdown

        # LEDs
        self.ready_led = LED(12)
        self.ready_led.blink()
        self.list_1_led = LED(16)
        self.list_2_led = LED(20)
        self.list_3_led = LED(21)

    def run(self):
        print("Starting Control Thread... " + self.name)
        self.ready_led.on()
        while exitFlag < 1:
            if self.playlist_1_btn.is_pressed:
                self.playing = False
                self.ready_led.blink()
                self.list_1_led.blink()
                self.list_2_led.off()
                self.list_3_led.off()
                print("Playlist #1")
                load_playlist(1)
                self.list_1_led.on()
                self.playing = True
                self.ready_led.on()
            elif self.playlist_2_btn.is_pressed:
                self.playing = False
                self.ready_led.blink()
                self.list_2_led.blink()
                self.list_1_led.off()
                self.list_3_led.off()
                print("Playlist #2")
                load_playlist(2)
                self.list_2_led.on()
                self.playing = True
                self.ready_led.on()
            elif self.playlist_3_btn.is_pressed:
                self.playing = False
                self.ready_led.blink()
                self.list_3_led.blink()
                self.list_1_led.off()
                self.list_2_led.off()
                print("Playlist #3")
                load_playlist(3)
                self.list_3_led.on()
                self.playing = True
                self.ready_led.on()
            elif self.prev_button.is_pressed:
                print('Previous Song')
                send_control("q")
                # Back current_song_number 2 songs, MusicThread will
                # increment up 1
                threadLock.acquire()
                global current_song_number
                print(str(current_song_number))
                current_song_number -= 2
                print(str(current_song_number))
                threadLock.release()
                # pause for human to release button ;)
                time.sleep(0.5)
                if not self.playing:
                    # was paused need to resume
                    self.playing = True
                    self.ready_led.on()
            elif self.pause_play_button.is_pressed:
                if self.playing:
                    # currently playing now pause
                    self.ready_led.blink()
                    self.playing = False
                else:
                    # currently paused, now play
                    self.ready_led.on()
                    self.playing = True
                print('Pause')
                send_control("p")
                # pause for human to release button ;)
                time.sleep(0.5)
            elif self.next_button.is_pressed:
                print('Next Song')
                send_control("q")
                # Shouldn't need to increment current_song_number
                # MusicThread should do that on it's own
                # pause for human to release button ;)
                time.sleep(0.5)
                if not self.playing:
                    # was paused need to resume
                    self.playing = True
                    self.ready_led.on()
            else:
                print(self.name + ": Waiting for input...")
                time.sleep(0.5)
                
        threadLock.acquire()
        global exitFlag
        exitFlag = 1
        threadLock.release()
        print(self.name + ": Exiting control Thread")
        self.ready_led.off()
        self.list_1_led.off()
        self.list_2_led.off()
        self.list_3_led.off()

threadLock = threading.Lock()
threads = []

music_process = None

# Exit when finished
exitFlag = 0

current_artist = ''
current_song = ''
current_song_number = 0
current_playlist = 0
playlist = []
play_status = 0

# Get LCD ready
GPIO.cleanup()
lcd = CharLCD(cols=16, rows=2, pin_rs=37, pin_e=35, pins_data=[33, 31, 29, 23], numbering_mode=GPIO.BOARD)
lcd.clear()
lcd.write_string(u'Getting Ready...')


# Create new threads
music_thread = musicThread(1, "Player")
display_thread = displayThread(2, "Display", lcd)
control_thread = controlThread(4, "Controls")

# Start new Threads
music_thread.start()
display_thread.start()
control_thread.start()

# Add threads to list to manage
threads.append(music_thread)
threads.append(display_thread)
threads.append(control_thread)

# Wait for all thread to complete
for t in threads:
    t.join()

# clear LCD
lcd.clear()
# wait for LCD to clear
time.sleep(0.5)
# clean up all GPIO pins
GPIO.cleanup()
# wait for GPIO to finish cleanup
time.sleep(1)
print("Exiting Main Thread")
print("SHUTDOWN COMPLETE!")
print("Shutting down the pi system...")
# send command to shutdown pi
subprocess.call(['sudo', 'shutdown', '-h', 'now'], shell=False)
