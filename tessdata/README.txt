This directory is intended to store Tesseract language data files.

Expected files (depending on your OCR language choices):
- eng.traineddata
- por.traineddata
- fra.traineddata
- deu.traineddata
- spa.traineddata

If you see an error like:
  "Please make sure the TESSDATA_PREFIX environment variable is set"
or:
  "Failed loading language 'fra'"
it usually means the required *.traineddata file is missing or
TESSDATA_PREFIX points to the wrong directory.
