import cv2
import numpy as np
import pytesseract
import time
import win32gui
import argparse

from multiprocessing import Process, Manager
from PIL import ImageGrab
from flask import jsonify, make_response, Flask
from flask_restful import Api, Resource, reqparse

# If you don't have tesseract executable in your PATH, include the following:
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def get_power_and_cadence_imgs(window_title='Connect'):
	hwnd = win32gui.FindWindow(None, window_title)
	win32gui.MoveWindow(hwnd, 0, 0, 640, 480, True) # resize window and place it in the top left corner

	power_img = ImageGrab.grab((290, 335, 350, 360))
	power_img = np.array(power_img) # convert Image to array

	cadence_img = ImageGrab.grab((145, 367, 205, 392))
	cadence_img = np.array(cadence_img) # convert Image to array

	return (power_img, cadence_img)

def img_transform(img):
	gray_image = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
	inverted = cv2.bitwise_not(gray_image)
	return inverted

def img_to_int(img):
	img = img_transform(img)
	config = ("--psm 7") # treat the image as a single text line.
	text = pytesseract.image_to_string(img, config=config)
	return int(text)

def obtain_metrics(metrics):
	while True:
		try:
			power_img, cadence_img = get_power_and_cadence_imgs()

			power = img_to_int(power_img)
			cadence = img_to_int(cadence_img)

			metrics['power'] = power
			metrics['cadence'] = cadence

			if debug:
				print("Metrics: {}".format(metrics))

		except ValueError as e:
			if debug:
				print("Can't recognize numbers. Is the Peloton Connect window visible? Error: {}".format(e))


class Metrics(Resource):
	def get(self):
		return metrics.copy(), 200


ap = argparse.ArgumentParser()
ap.add_argument("-d", "--debug", type=bool, nargs='?', const=True, default=False, help="Enable debug messages")
ap.add_argument("-p", "--port", type=int, default=5000, help="Webserver port")
args = vars(ap.parse_args())
debug = args["debug"]
port = args["port"]

app = Flask(__name__)
api = Api(app)
api.add_resource(Metrics, "/metrics")

if __name__ == '__main__':
	with Manager() as manager:
		metrics = manager.dict()
		metrics['cadence'] = 0
		metrics['power'] = 0

		p = Process(target=obtain_metrics, args=(metrics,))
		p.start()

		app.run(host='0.0.0.0', port=port, debug=debug)
