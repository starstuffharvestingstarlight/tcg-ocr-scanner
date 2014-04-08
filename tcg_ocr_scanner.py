#!/usr/bin/python

import numpy
import cv2
import cv2.cv as cv
import sys
import os
import subprocess
import hunspell
import time
from PIL import Image, ImageDraw
# sudo pip install xerox
# sudo apt-get install xclip
import argparse
import signal
import Queue as queue
# import queue
import threading

from handlers import *
from database import *

# @see https://stackoverflow.com/questions/5849800/tic-toc-functions-analog-in-python
class Timer(object):
	def __init__(self, name=None, verbosity=0):
		self.name = name
		self.verbosity = verbosity

	def __enter__(self):
		self.tstart = time.time()

	def __exit__(self, type, value, traceback):
		if self.verbosity > 1:
			print '%s, %e' % (self.name if self.name else 'timer', time.time() - self.tstart)

# tesseract
class Tesseract(object):
	def __init__(self):
		self.DEV_NULL = open(os.devnull, 'w')

	def image_to_string(self, img):
		with Timer('image_to_string_save', 2):
			cv.SaveImage('media/tmp.png', img)
		with Timer('image_to_string_proc', 2):
			subprocess.call(
				['tesseract', 'media/tmp.png', 'media/tmp', '-l', 'eng', '-psm', '7', 'tesseract.config'],
				stdout=self.DEV_NULL,
				stderr=subprocess.STDOUT
			)
		with Timer('image_to_string_cat', 2):
			txt = self.file_to_string('media/tmp.txt')
		return txt

	def file_to_string(self, file_name):
		f = file(file_name)
		text = f.read().strip()
		f.close()
		return text

	def __del__(self):
		try:
			os.remove('media/tmp.png')
			os.remove('media/tmp.txt')
		except Exception:
			pass

# image providers
class ImageProvider(threading.Thread):
	def __init__(self, queue):
		super(ImageProvider, self).__init__()
		self.image_queue = queue
		self.daemon = True

class WebcamImageProvider(ImageProvider):
	def __init__(self, queue, webcam):
		super(WebcamImageProvider, self).__init__(queue)
		self.camera = cv.CreateCameraCapture(webcam)
		img = cv.QueryFrame(self.camera)
		if img is None:
			raise queue.Empty
		self.running = True

	def run(self):
		while self.running:
			img = cv.QueryFrame(self.camera)
			self.image_queue.put(img)
			c = cv.WaitKey(30)

	def stop(self):
		self.running = False

# this needs to do both frame detection and processor chain fetching from the db
class Frame(object):
	def __init__(self, img):
		(self.max_w, self.max_h) = cv.GetSize(img)
		# rectangle position TODO: use frame detection
		(self.w, self.h) = (350, 30)
		(self.x, self.y) = (self.max_w/2 - self.w/2, 0)
		self.rect = (self.x, self.y, self.w, self.h)
		# TODO: replace with frame specific blocks from db
		self.processors = ['CropProcessor', 'GreyscaleProcessor']

class DetectorThread(threading.Thread):
	def __init__(self, 
		card_db, image_queue, handlers, tesseract, speller,
		min_suggestions=0, max_wait=2, verbosity=0, min_card_name=3, max_guesses=5, switch_time=2
	):
		super(DetectorThread, self).__init__()
		self.daemon = True
		self.running = True
		self.card_db = card_db
		self.image_queue = image_queue
		self.handlers = handlers
		self.tesseract = tesseract
		self.speller = speller

		# options
		self.min_suggestions = min_suggestions
		self.max_wait = max_wait
		self.verbosity = verbosity
		self.max_guesses = max_guesses
		self.min_card_name = min_card_name
		self.switch_time = switch_time

	def doCropProcessor(self, img):
		(x, y, w, h) = self.frame.rect
		return img[y:y+h, x:x+w]

	def doGreyscaleProcessor(self, img):
		(x, y, w, h) = self.frame.rect
		bw = cv.CreateImage((w, h), 8, 1)
		cv.CvtColor(img, bw, cv.CV_RGB2GRAY)
		return bw

	def doInvertProcessor(self, img):
		# FIXME this is neat for frames with white text
		return img

	def run(self):
		(last_detected_ts, elapsed_s) = (time.time(), 0)
		poll = {}

		try:
			img = self.image_queue.get(block = True, timeout = 60)
		except queue.Empty:
			print 'Could not load images from webcam, please check settings'
			return
		self.frame = Frame(img) # TODO move to main loop, detect frame
		
		self.handlers.send('detector_started')
		while self.running:
			elapsed_s = time.time() - last_detected_ts

			if elapsed_s > self.max_wait:
				self.handlers.send('detector_gave_up', poll)
				poll = {}
				continue

			try:
				with Timer('consume_image', self.verbosity):
					img = self.image_queue.get(block = True, timeout = self.max_wait)
				self.handlers.send('image_captured', (img, self.frame.rect))

			except queue.Empty:
				poll = {}
				self.handlers.send('detector_gave_up', poll)
				continue

			if elapsed_s < self.switch_time:
				continue

			with Timer('process_image', self.verbosity):
				img_arr = numpy.asarray(img[:,:])

				for processor in self.frame.processors:
					with Timer('processor_%s' % processor):
						img = getattr(self, 'do%s' % processor)(img)
				self.handlers.send('image_processed', img)

			with Timer('image_to_string', self.verbosity):
				card = self.tesseract.image_to_string(img)

			if len(card) < self.min_card_name:
				continue

			with Timer('spell_check', self.verbosity):
				suggestions = self.speller.suggest(card.replace(' ', '')) 

			if not suggestions or len(suggestions) > self.max_guesses:
				continue

			best_slug = suggestions[0]

			if best_slug in poll:
				poll[best_slug] += 1
			else: 
				poll[best_slug] = 1

			self.handlers.send('card_guesses', poll)

			if poll[best_slug] <= self.min_suggestions: 
				continue

			if self.card_db.exists(best_slug):
				card_data = self.card_db.get(best_slug)
				card_data.detected_in = time.time() - self.switch_time - last_detected_ts
				card_data.poll_results = poll
				self.handlers.send('card_detected', card_data)

				last_detected_ts = time.time()

			else:
				self.handlers.send('card_not_found', best_slug)

			poll = {}

	def stop(self):
		self.running = False
		self.handlers.send('detector_stopped')


class DetectorDaemon(object):
	def __init__(self, options, handlers = []):
		self.speller = hunspell.HunSpell('%s.dic' % options.dictionary, '%s.aff' % options.dictionary)
		self.tesseract = Tesseract()
		self.handlers = EventHandlers(handlers)
		self.image_queue = queue.Queue()
		self.verbosity = options.verbosity # FIXME not sold on this
		self.card_db = CardDb(options) # FIXME needs some handler rewiring here for db logs

		self.provider = WebcamImageProvider(self.image_queue, options.webcam)
		self.detector = DetectorThread(
			self.card_db, self.image_queue, self.handlers, self.tesseract, self.speller,
			options.min_suggestions, options.give_up_after, options.verbosity, options.min_length
		);

		self.running = True

	def run(self):
		[t.start() for t in [self.provider, self.detector]]
		while self.running:
			time.sleep(1)

	def stop(self):
		[t.stop() for t in [self.provider, self.detector]]
		[t.join() for t in [self.provider, self.detector]]
		self.running = False

	def __del__(self):
		del self.tesseract
		del self.card_db
