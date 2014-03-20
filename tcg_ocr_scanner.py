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
      if self.name:
        print '[%s]' % self.name,
      print 'Elapsed: %s' % (time.time() - self.tstart)

# tesseract
class Tesseract(object):
  def __init__(self):
    self.DEV_NULL = open(os.devnull, 'w')

  def image_to_string(self, img):
    cv.SaveImage('media/tmp.png', img)
    subprocess.call(
      ['tesseract', 'media/tmp.png', 'media/tmp', '-l', 'eng', '-psm', '7', 'tesseract.config'],
      stdout=self.DEV_NULL,
      stderr=subprocess.STDOUT
    )
    return self.file_to_string('media/tmp.txt')

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
      raise Empty
    
  def run(self):
    while True:
      img = cv.QueryFrame(self.camera)
      self.image_queue.put(img)
      c = cv.WaitKey(30)

# detector
class Detector(object):
  def __init__(self, options, handlers = []):
    self.speller = hunspell.HunSpell('%s.dic' % options.dictionary, '%s.aff' % options.dictionary)
    self.tesseract = Tesseract()
    self.handlers = EventHandlers(handlers)
    self.image_queue = queue.Queue()
    self.provider = WebcamImageProvider(self.image_queue, options.webcam)

    # cv.NamedWindow('debug')
    self.card_db = CardDb(options)

    self.poll = {}

    self.provider.start()

    try:
      img = self.image_queue.get(block = True, timeout = 60)
    except queue.Empty:
      print 'Could not load images from webcam, please check settings'
      exit()
    
    (self.max_w, self.max_h) = cv.GetSize(img)

    # settings
    # rectangle position
    (self.w, self.h) = (350, 30)
    (self.x, self.y) = (self.max_w/2 - self.w/2, 0)

    # minimum card name length
    self.min_card_name = options.min_length

    # suggestion threshold
    self.min_suggestions = options.min_suggestions

    # max time before giving up
    self.max_wait = options.give_up_after
    
    # max number of guesses
    self.max_guesses = 5
  
    # time to wait after scan succeeds (s)
    self.switch_time = 2

    self.running = True

  def run(self):
    #font = cv.InitFont(cv.CV_FONT_HERSHEY_SIMPLEX, 0.7, 0.7)
    font = cv.InitFont(cv.CV_FONT_HERSHEY_PLAIN, 1.3, 1.3)

    (last_detected_ts, elapsed_s) = (time.time() - self.switch_time, 0)

    (x, y, h, w) = (self.x, self.y, self.h, self.w)

    (poll, switch_pause) = ({}, False)

    self.handlers.send('detector_started')

    while self.running:
      with Timer('capture image', 0):
        try:
          img = self.image_queue.get(block = True, timeout = self.max_wait)
        except Empty:
          poll = {}
          last_detected_ts = time.time()
          self.handlers.send('detector_gave_up', poll)
          continue

        # img = cv.QueryFrame(self.camera)
        img_arr = numpy.asarray(img[:,:])

        self.handlers.send('image_captured', (img, (x, y, w, h)))

      elapsed_s = time.time() - last_detected_ts

      if not switch_pause:
        with Timer('process_image', 0):
          crop_img = img[y:y+h, x:x+w]

          bw = cv.CreateImage((w, h), 8, 1)
          cv.CvtColor(crop_img, bw, cv.CV_RGB2GRAY)
      
        self.handlers.send('image_processed', bw)

        if elapsed_s < self.max_wait:
          with Timer('image_to_string', 0):
            card = self.tesseract.image_to_string(bw)


          if len(card) > self.min_card_name:
            suggestions = self.speller.suggest(card.replace(' ', '')) 
            if len(suggestions) > 0 and len(suggestions) < self.max_guesses:
              best_slug = suggestions[0]

              if best_slug in poll:
                poll[best_slug] += 1
              else: 
                poll[best_slug] = 1

              self.handlers.send('card_guesses', poll)

              if poll[best_slug] > self.min_suggestions: 
                if self.card_db.exists(best_slug):
                  card_data = self.card_db.get(best_slug)
                  card_data.detected_in = time.time() - self.switch_time - last_detected_ts
                  card_data.poll_results = poll

                  last_detected_ts = time.time()

                  self.handlers.send('card_detected', card_data)

                else:
                  self.handlers.send('card_not_found', best_slug)
      
                (poll, switch_pause) = ({}, True)
        else:
          poll = {}
          last_detected_ts = time.time()

          self.handlers.send('detector_gave_up', poll)
      else:
        if elapsed_s > self.switch_time:
          switch_pause = False

  def stop(self):
    self.running = False
    self.handlers.send('detector_stopped')

  def __del__(self):
    del self.tesseract
    del self.card_db
