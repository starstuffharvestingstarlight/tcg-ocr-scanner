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

# handlers
class CardHandler(object):
  def __init__(self, options = None):
    return None
    
  def handle(self, card):
    raise NotImplementedError("Please implement the card handler")

class BeepHandler(CardHandler):
  def __init__(self):
    # sound from http://www.freesound.org/people/zerolagtime/sounds/144418/
    self.pygame = pygame.init()
    print self.pygame
    self.beeper = pygame.mixer.Sound("media/beep.wav")
  def handle(self, card):
    self.beeper.play()
    time.sleep(self.beeper.get_length())
  def __del__(self):
    print 'beeper cleanup'
    self.pygame.quit()

class StdoutHandler(CardHandler):
  def handle(self, card):
    print "Detected: %s (%.2f secs)" % (card.name, card.detected_in)

class ClipboardHandler(CardHandler):
  def handle(self, card):
    xerox.copy(card.name)

class CsvHandler(CardHandler):
  def __init__(self, options):
    print "init file"
  def handle(self, card):
    print "write file for %s" % card.name

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

# detector
class Detector(object):
  def __init__(self, options, handlers = []):
    self.speller = hunspell.HunSpell('%s.dic' % options.dictionary, '%s.aff' % options.dictionary)
    self.tesseract = Tesseract()

    cv.NamedWindow("CaptureFeedback")
    # cv.NamedWindow("debug")
    cv.StartWindowThread()
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

    self.handlers = handlers

    self.running = True

  def run(self):
    #font = cv.InitFont(cv.CV_FONT_HERSHEY_SIMPLEX, 0.7, 0.7)
    font = cv.InitFont(cv.CV_FONT_HERSHEY_PLAIN, 1.3, 1.3)

    (message, last_detected, last_detected_ts, elapsed_s) = ("", "", time.time(), 0)

    debug_ts = time.time()

    (x, y, h, w) = (self.x, self.y, self.h, self.w)

    poll = {}
    while self.running:
      img = cv.QueryFrame(self.camera)
      # self.debug_ts = tick(self.debug_ts, "Camera")

      cv2.rectangle(numpy.asarray(img[:,:]), (x,y+1), (x+w,y+1+h), (0, 0, 0))
      cv2.rectangle(numpy.asarray(img[:,:]), (x,y), (x+w,y+h), (50, 50, 250))

      cv.PutText(img, message, (0,y+1+2*h), font, (255, 255, 255))
      cv.PutText(img, message, (0,y+2*h), font, (0, 0, 0))

      #debug_ts = tick(debug_ts, "Draw img")

      crop_img = img[y:y+h, x:x+w]
      #debug_ts = tick(debug_ts, "Crop")

      size = cv.GetSize(crop_img)
      bw = cv.CreateImage(size, 8, 1)
      cv.CvtColor(crop_img, bw, cv.CV_RGB2GRAY)
    
      #debug_ts = tick(debug_ts, "Make BW")

      cv.ShowImage("CaptureFeedback", img)

      #debug_ts = tick(debug_ts, "Show image")
      # cv.ShowImage("debug", bw)

      elapsed_s = time.time() - last_detected_ts

      if elapsed_s < self.max_wait:
        card = self.tesseract.image_to_string(bw)
        #debug_ts = tick(debug_ts, "Image to string")

        if len(card) > self.min_card_name:
          suggestions = self.speller.suggest(card.replace(" ", "")) 
          #debug_ts = tick(debug_ts, "Speller")
          if len(suggestions) > 0:
            
            # print "I think it is %s" % suggestions[0]
            if suggestions[0] in poll:
              poll[suggestions[0]] += 1
            else: 
              poll[suggestions[0]] = 1

            if poll[suggestions[0]] > self.min_suggestions: 
              if self.card_db.exists(suggestions[0]):
                card_data = self.card_db.get(suggestions[0])
                card_data.detected_in = time.time() - last_detected_ts

                last_detected_ts = time.time()
    
                for handler in self.handlers:
                  handler.handle(card_data)

              else:
                print "Couldn't find data for card '%s', skipping" % suggestions[0]
    
              poll = {}
      else:
        poll = {}
        last_detected_ts = time.time()
        print "gave up detecting, restarting guesses"

      c = cv.WaitKey(10)

  def stop(self):
    self.running = False

class TcgOcrScannerCli(object):
  def __init__(self):
    parser = argparse.ArgumentParser(description='Scan MTG cards using OCR (tesseract).')

    parser.add_argument(
      '-b',
      '--beep', 
      help='beep when scan happens', 
      action='store_true'
    )
    parser.add_argument(
      '--clipboard', 
      help='save card name to clipboard', 
      action='store_true'
    )
    parser.add_argument(
      '--batchfile', 
      help='save data to batch file', 
      nargs='+', 
      type=argparse.FileType('w') 
    )
    parser.add_argument(
      '-v', 
      '--verbosity', 
      help='verbosity level (0: quiet, 1: feedback, 2: debug)', 
      default=0,
      metavar='int',
      type=int,
      choices=xrange(3)
    )
    parser.add_argument(
      '-d', 
      '--dictionary',
      help='dictionary to use (e.g., dict/INN for dict/INN.dic + dict/INN.aff)', 
      default='./dict/mtg'
    )
    parser.add_argument(
      '--min-suggestions', 
      help='minimum number of suggestions polled (e.g., 5 means it is considered a correct guess after 5 equal guesses)', 
      default=8,
      metavar='int',
      type=int,
      choices=xrange(100)
    )
    parser.add_argument(
      '--min-length', 
      help='minimum length for a detected card name', 
      default=3,
      metavar='int',
      type=int,
      choices=xrange(100)
    )
    parser.add_argument(
      '--webcam', 
      help='webcam number (usually, the biggest number is the one you plugged in)', 
      default=1,
      metavar='int',
      type=int,
      choices=xrange(10)
    )
    parser.add_argument(
      '--give-up-after',
      help='maximum number of seconds to try to guess the card',
      default=80,
      metavar='int',
      type=int,
      choices=xrange(360)
    )

    self.options = parser.parse_args()
  
    signal.signal(signal.SIGINT, self.handle_sigint)

    handlers = []
    if self.options.beep:
      handlers.append(BeepHandler())
    if self.options.verbosity >= 1:
      handlers.append(StdoutHandler())
    if self.options.clipboard:
      handlers.append(ClipboardHandler())

    self.detector = Detector(self.options, handlers)

  def handle_sigint(self, signal, frame):
    self.detector.stop()

  def run(self):
    self.detector.run()

  def cleanup(self):
    for handler in handlers:
      del handler

if __name__ == "__main__":
  app = TcgOcrScannerCli()
  app.run()

