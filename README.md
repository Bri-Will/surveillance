# surveillance
Simple Python program for using a webcam to do motion-detection-based surveillance

This program was modified from a blog post on the really cool website pyimagesearch.com.
It was originally written for raspberry pi, but I got it running on an old Sony laptop
and Logitech USB webcam with very minimal modifications. You can find the blog post here:

https://www.pyimagesearch.com/2015/06/01/home-surveillance-and-motion-detection-with-the-raspberry-pi-python-and-opencv/

My modifications were to send an e-mail with an image attached if motion is detected,
to only examine a specific (cropped) portion of the image for motion (to reduce false
positives), and to save a video file of the "motion incident".

To run the program: 
> python surveillance.py -c conf.json

To run the program in "aiming" mode (to see the cropped image size and/or position the camera):
> python surveillance.py -c conf.json --aim True
