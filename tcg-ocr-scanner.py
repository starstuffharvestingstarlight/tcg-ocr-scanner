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

def init():
  global pygame, beeper, speller, DEV_NULL, camera, poll, card_db, options

  parser = argparse.ArgumentParser(description='Scan MTG cards using OCR (tesseract).')

  parser.add_argument(
    '--nobeep', 
    help='disable beep when scan happens', 
    action='store_false'
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

  options = parser.parse_args()

  if options.nobeep:
    # sound from http://www.freesound.org/people/zerolagtime/sounds/144418/
    pygame.init()
    beeper = pygame.mixer.Sound("media/beep.wav")
 
  speller = hunspell.HunSpell('%s.dic' % options.dictionary, '%s.aff' % options.dictionary)

  DEV_NULL = open(os.devnull, 'w')

  cv.NamedWindow("CaptureFeedback")
  # cv.NamedWindow("debug")
  cv.StartWindowThread()
  camera = cv.CreateCameraCapture(options.webcam)

  try:
    card_db = pickle.load(open("./dict/cards.pickle", "rb"))
  except Exception:
    print "No card database found. Try running 'make dict' with a cards.xml file in ./dict/"
    exit()

  poll = {}

def cleanup():
  global pygame
  pygame.quit()

def beep():
  global beeper
  beeper.play()
  time.sleep(beeper.get_length())

def string_to_clipboard(string):
  print "Clipboarded: %s" % string
  xerox.copy(string)

def file_to_string(fname):
  f = file(fname)
  text = f.read().strip()
  f.close()
  return text

def image_to_string(img):
  global DEV_NULL
  cv.SaveImage("media/tmp.png", img)
  subprocess.call(
    ["tesseract", "media/tmp.png", "media/tmp", "-l", "eng", "-psm", "7", "tesseract.config"],
    stdout=DEV_NULL,
    stderr=subprocess.STDOUT
  )
  return file_to_string("media/tmp.txt")

def tick(ts, message):
  global options
  if options.verbosity == 2:
    print "elapsed [%s]: %.2fs" % (message, round(time.time() - ts, 2))
    return time.time()
  return None

if __name__ == "__main__":
  init()

  img = cv.QueryFrame(camera)

  if img is None:
    print "Can't load images from webcam, please check settings"
    exit()
  
  (max_w, max_h) = cv.GetSize(img)

  # settings
  # rectangle position
  (w, h) = (350, 30)
  (x, y) = (max_w/2 - w/2, 0)

  # minimum card name length
  min_card_name = options.min_length

  # suggestion threshold
  min_suggestions = options.min_suggestions

  #font = cv.InitFont(cv.CV_FONT_HERSHEY_SIMPLEX, 0.7, 0.7)
  font = cv.InitFont(cv.CV_FONT_HERSHEY_PLAIN, 1.3, 1.3)

  (message, last_detected, last_detected_ts) = ("", "", time.time())

  debug_ts = time.time()

  while True:
    img = cv.QueryFrame(camera)
    debug_ts = tick(debug_ts, "Camera")

    cv2.rectangle(numpy.asarray(img[:,:]), (x,y+1), (x+w,y+1+h), (0, 0, 0))
    cv2.rectangle(numpy.asarray(img[:,:]), (x,y), (x+w,y+h), (50, 50, 250))

    cv.PutText(img, message, (0,y+1+2*h), font, (255, 255, 255))
    cv.PutText(img, message, (0,y+2*h), font, (0, 0, 0))

    debug_ts = tick(debug_ts, "Draw img")

    crop_img = img[y:y+h, x:x+w]
    debug_ts = tick(debug_ts, "Crop")

    size = cv.GetSize(crop_img)
    bw = cv.CreateImage(size, 8, 1)
    cv.CvtColor(crop_img, bw, cv.CV_RGB2GRAY)
    
    debug_ts = tick(debug_ts, "Make BW")

    cv.ShowImage("CaptureFeedback", img)

    debug_ts = tick(debug_ts, "Show image")
    # cv.ShowImage("debug", bw)

    card = image_to_string(bw)
    debug_ts = tick(debug_ts, "Image to string")

    if (len(card) > min_card_name):
      suggestions = speller.suggest(card.replace(" ", "")) 
      debug_ts = tick(debug_ts, "Speller")
      if (len(suggestions) > 0):
        # print "I think it is %s" % suggestions[0]
        if (suggestions[0] in poll):
          poll[suggestions[0]] += 1
        else: 
          poll[suggestions[0]] = 1

        if (poll[suggestions[0]] > 10): 
          try:
            last_detected = card_db[suggestions[0]][1]
          except Exception:
            print "Couldn't find data for card '%s', skipping" % suggestions[0]
            continue

          message = "Detected: %s (%.2f secs)" % (last_detected , round(time.time() - last_detected_ts, 2))
          last_detected_ts = time.time()
          if options.verbosity >= 1:
            print message
          if options.clipboard:
            string_to_clipboard(last_detected)
          if options.nobeep:
            beep()
          poll = {}

    c = cv.WaitKey(10)


  cleanup()
