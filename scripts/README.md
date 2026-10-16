The script `collect_vocab.py` is automatically ran every time a csv file is uploaded to annoations. The script collects all values from the fields we are trying to standardize and fills out `vocab/<field>/raw.csv with:
- All unique values in that field across all annotations.
- The number of times the value was recorded.
- Who recoded the value.
- When the value was recorded. 
