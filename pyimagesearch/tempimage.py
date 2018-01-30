# import the necessary packages
import uuid
import os

class TempImage:
	def __init__(self, basePath="./", ext=".jpg"):
		# construct the file path
		fn = "{rand}{ext}".format(rand=str(uuid.uuid4()), ext=ext)
		self.filename = fn
		self.path = "{base_path}/{fn}".format(base_path=basePath, fn=fn)

	def cleanup(self):
		# remove the file
		os.remove(self.path)
