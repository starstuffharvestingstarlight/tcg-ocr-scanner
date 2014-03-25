import cv2
import cv2.cv as cv
import pygame
import numpy
import xerox
import csv
import time

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
		self.beeper = pygame.mixer.Sound('media/beep.wav')
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
			print 'Detected: %s (%.2f secs)' % (card.name, card.detected_in)
		elif self.verbosity >= 2:
			print 'OK, %s, %.2f, %d' % (card.name, card.detected_in, len(card.poll_results))
		self.count += 1
	def detector_started(self):
		self.count = 0
		print 'Detector started'
	def detector_gave_up(self, args):
		if self.verbosity == 1:
			print 'Detection taking too long, giving up'
		elif self.verbosity >= 2:
			print 'FAIL,,,'
	def detector_stopped(self):
		print 'Detector stopped. Detected %s cards' % self.count

class ClipboardHandler(EventHandler):
	def card_detected(self, card):
		xerox.copy(card.name)

class OutputFileHandler(EventHandler):
	def __init__(self, out_file, out_format):
		self.out_file = out_file
		self.out_format = out_format
		getattr(self, '_init_%s' % out_format)()
	
	def __del__(self):
		getattr(self, '_del_%s' % self.out_format)()
		self.out_file.close()
		del self.out_file

	# deckbox_org_csv
	def _init_deckbox_org_csv(self):
		self.writer = csv.writer(self.out_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
		self.writer.writerow(['Count','Tradelist Count','Name','Foil','Textless','Promo','Signed','Edition','Condition','Language'])

	def _write_deckbox_org_csv(self, card):
		self.writer.writerow([1,0,card.name,'','','','','','Near Mint','English'])

	def _del_deckbox_org_csv(self):
		return 
	
	# debug stats
	def _init_debug_csv(self):
		self.writer = csv.writer(self.out_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
		self.writer.writerow(['Count','Tradelist Count','Name','Foil','Textless','Promo','Signed','Edition','Condition','Language'])

	def _write_debug_csv(self, card):
		self.writer = csv.writer(self.out_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
		self.writer.writerow(['Count','Tradelist Count','Name','Foil','Textless','Promo','Signed','Edition','Condition','Language'])

	def _del_debug_csv(self):
		return
	
	# event handler
	def card_detected(self, card):
		getattr(self, '_write_%s' % self.out_format)(card)


# image handlers
class FeedbackWindowImageHandler(EventHandler):
	def __init__(self):
		cv.StartWindowThread()
		cv.NamedWindow('Capture Feedback')
	def image_captured(self, args):
		(img, rect) = args
		(x, y, w, h) = rect

		cv2.rectangle(numpy.asarray(img[:,:]), (x,y+1), (x+w,y+1+h), (0, 0, 0))
		cv2.rectangle(numpy.asarray(img[:,:]), (x,y), (x+w,y+h), (50, 50, 250))
		
		#cv.PutText(img, message, (0,y+1+2*h), font, (255, 255, 255))
		#cv.PutText(img, message, (0,y+2*h), font, (0, 0, 0))
		#cv.ShowImage('Capture Feedback', cv2.fromarray(img[:,:]))
		cv.ShowImage('Capture Feedback', img)

