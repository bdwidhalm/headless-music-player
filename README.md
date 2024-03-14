# headless-music-player

This is a simple script created to run on a raspberry pi to play music without a monitor.  

## Setup
Need to add a cron entry to start the python script after start-up or reboot.  The script runs in the background waiting for a button to be pressed.  


## Hardware
Raspberry Pi
=======
The code runs on a raspberry pi, uses 6 buttons for playback, pause, skip/back and playlist selection.  These need to be wired up to specific pins on the pi (see code).  Another button is set up to turn the pi on and off, LEDs connected to indication playlist selection and status.  Used a 16x2 LCD screen to display the current song and artist.  


## Playlist
Playlists need to be setup ahead of time, currently supports 3 different lists in the p3u format.  


