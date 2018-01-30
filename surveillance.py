# This program was modified from a blog post on the really cool website pyimagesearch.com.
# It was originally written for raspberry pi, but I got it running on an old Sony laptop
# and Logitech USB webcam with very minimal modifications. You can find the blog post here:
#
# https://www.pyimagesearch.com/2015/06/01/home-surveillance-and-motion-detection-with-the-raspberry-pi-python-and-opencv/
#
# My modifications were to send an e-mail with an image attached if motion is detected,
# to only examine a specific (cropped) portion of the image for motion (to reduce false
# positives), and to save a video file of the "motion incident".

# To run the program: 
# > python surveillance.py -c conf.json
#
# To run the program in "aiming" mode (to see the cropped image size and/or position the camera):
# > python surveillance.py -c conf.json --aim True




# Import the necessary packages
from pyimagesearch.tempimage import TempImage
import argparse
import warnings
import datetime
import imutils
import json
import time
import cv2
import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.MIMEBase import MIMEBase
from email import encoders

def send_email(frame):
	# Write the image to temporary file
	t = TempImage()
	cv2.imwrite(t.path, frame)

	# E-mail the image and cleanup the tempory image
	msg = MIMEMultipart()
	msg['From'] = conf["from_addr"]
	msg['To'] = conf["to_addr"]
	msg['Subject'] = "Front Door Visitor"

	body = " "

	msg.attach(MIMEText(body, 'plain'))

	attachment = open(t.path, "rb")

	part = MIMEBase('application', 'octet-stream')
	part.set_payload((attachment).read())
	encoders.encode_base64(part)
	part.add_header('Content-Disposition', "attachment; filename= %s" % t.filename)

	msg.attach(part)

	server = smtplib.SMTP('smtp.gmail.com', 587)
	server.starttls()
	server.login(conf["from_addr"], conf["email_pwd"])
	text = msg.as_string()
	server.sendmail(conf["from_addr"], conf["to_addr"], text)
	server.quit()

	print "[E-MAIL SENT] {}".format(ts)

	t.cleanup()

	return

# Construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-c", "--conf", required=True, help="path to the JSON configuration file")
ap.add_argument("--aim", required=False, help="True to display cropped frame image")
args = vars(ap.parse_args())

# Filter warnings, load the configuration
warnings.filterwarnings("ignore")
conf = json.load(open(args["conf"]))

# Open video capture stream. On my laptop, video device 0 is the built-in
# webcam, while device 1 is a USB-connected webcam
vs = cv2.VideoCapture(1)

# Allow the camera to warmup, then initialize key values
print "[INFO] warming up..."
time.sleep(conf["camera_warmup_time"])
avg = None
lastUploaded = datetime.datetime.now()
motionCounter = 0
no_motionCounter = 0
recording = False

# If image will be cropped, set crop coordinates
if conf["crop"]:
	X1 = conf["crop_pt1"][0]
	Y1 = conf["crop_pt1"][1]
	X2 = conf["crop_pt2"][0]
	Y2 = conf["crop_pt2"][1]

# Main program loop. Capture frame from the camera in each loop
while True:
	# Grab the image and initialize the
	# timestamp and motion/no motion text
	__, frame = vs.read()
	timestamp = datetime.datetime.now()
	text = "No motion detected"

	# If crop is True, then crop the frame. Otherwise the region of interest is the entire frame.
	# Convert the region of interest to grayscale, and blur it. Cropping the frame allows looking
	# for motion in a specific portion of the image
	if conf["crop"]:
		roi = frame[Y1:Y2, X1:X2] # Crops the frame using numpy slices
	else:
		roi = frame

	gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
	gray = cv2.GaussianBlur(gray, (21, 21), 0)

	# If the average frame is None, initialize it
	if avg is None:
		print "[INFO] starting background model..."
		avg = gray.copy().astype("float")
		continue

	# Accumulate the weighted average between the current frame and
	# previous frames, then compute the difference between the current
	# frame and running average
	cv2.accumulateWeighted(gray, avg, 0.5)
	frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(avg))

	# Threshold the delta image, dilate the thresholded image to fill
	# in holes, then find contours on thresholded image
	thresh = cv2.threshold(frameDelta, conf["delta_thresh"], 255, cv2.THRESH_BINARY)[1]
	thresh = cv2.dilate(thresh, None, iterations=2)
	(cnts, _) = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

	# Loop over the contours
	for c in cnts:
		# If the contour is too small, ignore it
		if cv2.contourArea(c) < conf["min_area"]:
			continue

		# Compute the bounding box for the contour
		(x, y, w, h) = cv2.boundingRect(c)

		# If the region of interest has been cropped, then we need to add the
		# lower left coordinates of the cropping box in order to draw the
		# bounding box in the proper position on the full image
		if conf["crop"]:
			x += X1
			y += Y1

		# Draw the bounding box for the contiour on the frame, and update
		# the text.
		cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
		text = "Motion Detected"

	# Draw the text and timestamp on the frame
	ts = timestamp.strftime("%A %d %B %Y %I:%M:%S%p")
	cv2.putText(frame, "Status: {}".format(text), (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
	cv2.putText(frame, ts, (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)

	# Check to see if motion is detected
	if text == "Motion Detected":

		# The no_motionCounter keeps the video rolling even if the motion "pauses"
                # for a configurable number of frames. Since motion is detected here, the
                # counter gets reset

		no_motionCounter = 0

		# Check to see if enough time has passed between motion "incidents", to prevent multiple image
		# emails and video recording sessions for the same incident
		if (timestamp - lastUploaded).seconds >= conf["min_upload_seconds"]:
			# Increment the motion counter
			motionCounter += 1

			# Check to see if the number of frames with consistent motion is high enough.
			# Prevents image email and/or recording for very brief motion incidents, like a
			# bird flying past the camera.
			if motionCounter >= conf["min_motion_frames"]:
				# If this is a new motion incident, and the video isn't already started,
				# start recording
				if not recording:
					# Save first frame to email later. If you try to e-mail it now, video frames
					# will get dropped while the email operation is completing.
					first_frame = frame

       					fname = timestamp.strftime("%A-%d-%B-%Y-%I-%M-%S%p")
					ftype = cv2.cv.CV_FOURCC(*'XVID')
					vidout = cv2.VideoWriter('{}.avi'.format(fname), ftype, conf["fps"], (conf["resolution"][0], conf["resolution"][1]))
					recording = True

				# Update the timestamp of last motion incident
				lastUploaded = timestamp

	# If no motion is detected
	else:
		motionCounter = 0

		# Keep no_motionCounter from growing too large while waiting for a new motion incident
		if no_motionCounter < 1000:
			no_motionCounter += 1
		else:
			no_motionCounter = conf["min_no_motion_frames"] + 1

		# Stops video if recording and no motion detected for a minimum number of frames
		if recording and no_motionCounter >= conf["min_no_motion_frames"]:
			if conf["send_email"]:
				send_email(first_frame)
			print "[VIDEO SAVED] {}".format(ts)
			vidout.release()
			recording = False

	if recording:
		vidout.write(frame)

	# Check to see if the frames should be displayed to screen
	if conf["show_video"]:
		if args["aim"]: # Display the region of interest so it can be aimed, especially when cropped
			cv2.imshow("Region of Interest", roi)
		else:
			cv2.imshow("Security Feed", frame)
		cv2.waitKey(1) # Display image for 1 millisecond. Image is not displayed without waitKey.

vs.release()
cv2.destroyAllWindows()
