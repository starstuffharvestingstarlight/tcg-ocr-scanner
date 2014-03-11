#!/usr/bin/python
from tcg_ocr_scanner import *

class TcgOcrScannerCli(object):
  def __init__(self):
    parser = argparse.ArgumentParser(description="Scan MTG cards using OCR (tesseract).")

    parser.add_argument(
      "-b",
      "--beep", 
      help="beep when scan happens", 
      action="store_true"
    )
    parser.add_argument(
      "-c",
      "--clipboard", 
      help="save card name to clipboard", 
      action="store_true"
    )
    parser.add_argument(
      "-o",
      "--output-file", 
      help="save data to batch file(s)", 
      nargs="+", 
      type=argparse.FileType("w") 
    )
    parser.add_argument(
      "-of", 
      "--output-format",
      help="output format to use when outputting a file (goes together with -o, multiples matched in order)", 
      default=["deckbox_org_csv"],
      nargs="+", 
      choices=["deckbox_org_csv", "debug_csv"]
    )
    parser.add_argument(
      "-d", 
      "--dictionary",
      help="dictionary to use (e.g., dict/INN for dict/INN.dic + dict/INN.aff)", 
      default="./dict/mtg"
    )
    parser.add_argument(
      "-v", 
      "--verbosity", 
      help="verbosity level (0: quiet, 1: feedback, 2: debug)", 
      default=0,
      metavar="int",
      type=int,
      choices=xrange(3)
    )
    parser.add_argument(
      "-cw",
      "--capture-window",
      help="don't show a capture window", 
      action="store_true"
    )
    parser.add_argument(
      "--min-suggestions", 
      help="minimum number of suggestions polled (e.g., 5 means it is considered a correct guess after 5 equal guesses)", 
      default=8,
      metavar="int",
      type=int,
      choices=xrange(100)
    )
    parser.add_argument(
      "--min-length", 
      help="minimum length for a detected card name", 
      default=3,
      metavar="int",
      type=int,
      choices=xrange(100)
    )
    parser.add_argument(
      "--webcam", 
      help="webcam number (usually, the biggest number is the one you plugged in)", 
      default=1,
      metavar="int",
      type=int,
      choices=xrange(10)
    )
    parser.add_argument(
      "--give-up-after",
      help="maximum number of seconds to try to guess the card",
      default=80,
      metavar="int",
      type=int,
      choices=xrange(360)
    )

    self.options = parser.parse_args()
  
    signal.signal(signal.SIGINT, self.handle_sigint)

    handlers = []
    if self.options.beep:
      handlers.append(BeepHandler())
    if self.options.clipboard:
      handlers.append(ClipboardHandler())
    if self.options.capture_window:
      handlers.append(FeedbackWindowImageHandler())
    if self.options.output_file:
      for i, out_file in enumerate(self.options.output_file):
        if i < len(self.options.output_format):
          out_format = self.options.output_format[i]
        handlers.append(OutputFileHandler(out_file, out_format))
    if self.options.verbosity:
      handlers.append(StdoutHandler(self.options.verbosity))
      print "Registered handlers: %s" % ", ".join(str(v) for v in handlers)

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
