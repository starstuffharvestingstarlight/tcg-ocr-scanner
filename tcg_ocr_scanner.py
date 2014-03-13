#!/usr/bin/python

import numpy
import cv2
import cv2.cv as cv
import pygame
import sys
import os
import subprocess
import hunspell
import time
import pickle
from PIL import Image, ImageDraw
# sudo pip install xerox
# sudo apt-get install xclip
import xerox
import argparse
import signal
import csv

# @see https://stackoverflow.com/questions/5849800/tic-toc-functions-analog-in-python
class Timer(object):
  def __init__(self, name=None):
    self.name = name

  def __enter__(self):
    self.tstart = time.time()

  def __exit__(self, type, value, traceback):
    if self.name:
      print '[%s]' % self.name,
    print 'Elapsed: %s' % (time.time() - self.tstart)

# basic card
class Card(object):
  (slug, name, detected_in) = ("", "", 1000)
  def __init__(self, properties = {}):
    for p in properties:
      setattr(self, p, properties[p])

# card collection
class CardDb(object):
  def __init__(self, options):
    try:
      self.card_db = pickle.load(open("./dict/cards.pickle", "rb"))
    except Exception:
      print "No card database found. Try running 'make dict' with a cards.xml file in ./dict/"
      exit()
  def exists(self, slug):
    return slug in self.card_db
  def get(self, slug):
    data = self.card_db[slug]
    return Card({"slug":data[0], "name":data[1], "expansion": data[2], "multiverse_id": data[3]})

# generic event handler
class EventHandler(object):
  def image_captured(self, args=None):
    return
  def image_processed(self, args=None):
    return
  def card_guesses(self, args=None):
    return
  def card_detected(self, args=None):
    return
  def card_not_found(self, args=None):
    return
  def detector_gave_up(self, args=None):
    return
  def detector_stopped(self, args=None):
    return
  def detector_started(self, args=None):
    return
  def __str__(self):
    return self.__class__.__name__

class EventHandlers(object):
  def __init__(self, handlers):
    self.handlers = handlers
  def send(self, method, args=None):
    for handler in self.handlers:
      if hasattr(handler, method):
        if args is None:
          getattr(handler, method)()
        else:
          getattr(handler, method)(args)

# card handlers
class BeepHandler(EventHandler):
  def __init__(self):
    # sound from http://www.freesound.org/people/zerolagtime/sounds/144418/
    pygame.init()
    self.beeper = pygame.mixer.Sound("media/beep.wav")
  def card_detected(self, card):
    self.beeper.play()
    time.sleep(self.beeper.get_length())
  def __del__(self):
    try:
      self.pygame.quit()
    except Exception:
      pass

class StdoutHandler(EventHandler):
  def __init__(self, verbosity):
    self.verbosity = verbosity
  def card_detected(self, card):
    if self.verbosity == 1:
      print "Detected: %s (%.2f secs)" % (card.name, card.detected_in)
    elif self.verbosity >= 2:
      print "OK, %s, %.2f, %d" % (card.name, card.detected_in, len(card.poll_results))
    self.count += 1
  def detector_started(self):
    self.count = 0
    print "Detector started"
  def detector_gave_up(self, args):
    if self.verbosity == 1:
      print "Detection taking too long, giving up"
    elif self.verbosity >= 2:
      print "FAIL,,,"
  def detector_stopped(self):
    print "Detector stopped. Detected %s cards" % self.count

class ClipboardHandler(EventHandler):
  def card_detected(self, card):
    xerox.copy(card.name)

class OutputFileHandler(EventHandler):
  def __init__(self, out_file, out_format):
    self.out_file = out_file
    self.out_format = out_format
    getattr(self, "_init_%s" % out_format)()
  
  def __del__(self):
    getattr(self, "_del_%s" % self.out_format)()
    self.out_file.close()
    del self.out_file

  # deckbox_org_csv
  def _init_deckbox_org_csv(self):
    self.writer = csv.writer(self.out_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    self.writer.writerow(["Count","Tradelist Count","Name","Foil","Textless","Promo","Signed","Edition","Condition","Language"])

  def _write_deckbox_org_csv(self, card):
    self.writer.writerow([1,0,card.name,"","","","","","","English"])

  def _del_deckbox_org_csv(self):
    return 
  
  # debug stats
  def _init_debug_csv(self):
    self.writer = csv.writer(self.out_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    self.writer.writerow(["Count","Tradelist Count","Name","Foil","Textless","Promo","Signed","Edition","Condition","Language"])

  def _write_debug_csv(self, card):
    self.writer = csv.writer(self.out_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    self.writer.writerow(["Count","Tradelist Count","Name","Foil","Textless","Promo","Signed","Edition","Condition","Language"])

  def _del_debug_csv(self):
    return
  
  # event handler
  def card_detected(self, card):
    getattr(self, "_write_%s" % self.out_format)(card)


# image handlers
class FeedbackWindowImageHandler(EventHandler):
  def __init__(self):
    cv.StartWindowThread()
    cv.NamedWindow("Capture Feedback")
  def image_captured(self, args):
    (img, rect) = args
    (x, y, w, h) = rect

    cv2.rectangle(numpy.asarray(img[:,:]), (x,y+1), (x+w,y+1+h), (0, 0, 0))
    cv2.rectangle(numpy.asarray(img[:,:]), (x,y), (x+w,y+h), (50, 50, 250))
    
    #cv.PutText(img, message, (0,y+1+2*h), font, (255, 255, 255))
    #cv.PutText(img, message, (0,y+2*h), font, (0, 0, 0))
    #cv.ShowImage("Capture Feedback", cv2.fromarray(img[:,:]))
    cv.ShowImage("Capture Feedback", img)

# tesseract
class Tesseract(object):
  def __init__(self):
    self.DEV_NULL = open(os.devnull, 'w')

  def image_to_string(self, img):
    cv.SaveImage("media/tmp.png", img)
    subprocess.call(
      ["tesseract", "media/tmp.png", "media/tmp", "-l", "eng", "-psm", "7", "tesseract.config"],
      stdout=self.DEV_NULL,
      stderr=subprocess.STDOUT
    )
    return self.file_to_string("media/tmp.txt")

  def file_to_string(self, file_name):
    f = file(file_name)
    text = f.read().strip()
    f.close()
    return text

  def __del__(self):
    try:
      os.remove("media/tmp.png")
      os.remove("media/tmp.txt")
    except Exception:
      pass

# detector
class Detector(object):
  def __init__(self, options, handlers = []):
    self.speller = hunspell.HunSpell('%s.dic' % options.dictionary, '%s.aff' % options.dictionary)
    self.tesseract = Tesseract()
    self.handlers = EventHandlers(handlers)

    # cv.NamedWindow("debug")
    self.camera = cv.CreateCameraCapture(options.webcam)

    self.card_db = CardDb(options)

    self.poll = {}

    img = cv.QueryFrame(self.camera)

    if img is None:
      print "Can't load images from webcam, please check settings"
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

    self.handlers.send("detector_started")

    while self.running:
      img = cv.QueryFrame(self.camera)
      img_arr = numpy.asarray(img[:,:])

      self.handlers.send("image_captured", (img, (x, y, w, h)))

      elapsed_s = time.time() - last_detected_ts

      if not switch_pause:
        crop_img = img[y:y+h, x:x+w]

        bw = cv.CreateImage((w, h), 8, 1)
        cv.CvtColor(crop_img, bw, cv.CV_RGB2GRAY)
      
        self.handlers.send("image_processed", bw)

        if elapsed_s < self.max_wait:
          card = self.tesseract.image_to_string(bw)

          if len(card) > self.min_card_name:
            suggestions = self.speller.suggest(card.replace(" ", "")) 
            if len(suggestions) > 0 and len(suggestions) < self.max_guesses:
              best_slug = suggestions[0]

              if best_slug in poll:
                poll[best_slug] += 1
              else: 
                poll[best_slug] = 1

              self.handlers.send("card_guesses", poll)

              if poll[best_slug] > self.min_suggestions: 
                if self.card_db.exists(best_slug):
                  card_data = self.card_db.get(best_slug)
                  card_data.detected_in = time.time() - self.switch_time - last_detected_ts
                  card_data.poll_results = poll

                  last_detected_ts = time.time()

                  self.handlers.send("card_detected", card_data)

                else:
                  self.handlers.send("card_not_found", best_slug)
      
                (poll, switch_pause) = ({}, True)
        else:
          poll = {}
          last_detected_ts = time.time()

          self.handlers.send("detector_gave_up", poll)
      else:
        if elapsed_s > self.switch_time:
          switch_pause = False

      c = cv.WaitKey(10)

  def stop(self):
    self.running = False
    self.handlers.send("detector_stopped")

  def __del__(self):
    del self.tesseract
    del self.card_db
