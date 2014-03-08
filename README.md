# mtg-ocr-scanner

Magic: The Gatheric card scanner using OCR (using Tesseract and OpenCV)

## Description

## Dependencies

### Required Python packages

- numpy
- hunspell
- xerox

### Required software

- tesseract
- xclip or equivalent for your OS (see xerox)
- GNU make (to build dictionary files)

### Required data

- cards.xml with the cards you'd like to recognise.

## Installing 

## Running

### Command line options

```
$ ./main.py -h
usage: main.py [-h] [--nobeep] [--clipboard]
               [--batchfile BATCHFILE [BATCHFILE ...]] [-v int]
               [-d DICTIONARY] [--min-suggestions int] [--min-length int]

Scan MTG cards using OCR (tesseract).

optional arguments:
  -h, --help            show this help message and exit
  --nobeep              disable beep when scan happens
  --clipboard           save card name to clipboard
  --batchfile BATCHFILE [BATCHFILE ...]
                        save data to batch file
  -v int, --verbosity int
                        verbosity level (0: quiet, 1: feedback, 2: debug)
  -d DICTIONARY, --dictionary DICTIONARY
                        dictionary to use (e.g., dict/INN for dict/INN.dic +
                        dict/INN.aff)
  --min-suggestions int
                        minimum number of suggestions polled (e.g., 5 means it
                        is considered a correct guess after 5 equal guesses)
  --min-length int      minimum length for a detected card name
```

### Example run

```bash
$ ./main.py -v 1
```

### Output

```
Detected: Rapid Hybridization (12.84 secs)
Detected: Rapid Hybridization (10.45 secs)
Detected: Hands of Binding (12.42 secs)
Detected: Simic Charm (14.22 secs)
Detected: Riot Control (15.22 secs)
Detected: Mind Grind (9.07 secs)
Detected: Spark Trooper (6.47 secs)
Detected: Vorel of the Hull Clade (11.54 secs)
Detected: Varolz, the Scar-Striped (14.62 secs)
Detected: Teysa, Envoy of Ghosts (13.34 secs)
Detected: Kessig Wolf Run (12.89 secs)
Detected: Fireshrieker (18.82 secs)
Detected: Megantic Sliver (9.38 secs)
Detected: Elvish Mystic (14.29 secs)
Detected: Bane Alley Blackguard (9.46 secs)
Detected: Doom Blade (12.16 secs)
Detected: Bronzebeak Moa (9.38 secs)
```


