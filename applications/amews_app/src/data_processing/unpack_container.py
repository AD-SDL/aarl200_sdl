from datetime import datetime
import math
import random
from typing import Any
import re

def nsort(s): # natural sort of wells
    well = s.split(',')[0].split('-')[2]
    return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', well)]


def unpack_self_container(
                          container: Any,
                          vol_min: float = 2300,
                          sort: bool = False): 
    code = container["code"]

    dt = datetime.now() 
    last_ID ="%s_%s" % (code, dt.strftime("%H%M"))
    last_dataset = "run_%s" % last_ID

    rack = container["rack"]
    creator = container["creator"]
    samples = creator["content"]
    who = creator["location"]

    items = rack["items"]
    rows = rack["rows"]
    cols = rack["columns"]
    autosampler = []


    q = []

    for ID in samples:

        # original well designations
        kind = samples[ID]["type"] 
        
        # added 7-25-2025 for recoveries
        if "missing" in kind:
            continue
        #

        well = ID.split(":")[-1] # creator well
        
        

        # ICP rack and autosampler designations
        if who == "BK":
            row =  ord(well[0]) - ord('A') + 1
            col = int(well[1:]) 
            row_ = rows + 1 - row 
            col_ = cols + 1 - col
            index = col_ + (row-1)*cols
            well_ = well

        if who == "PAL1":
            index = int(well) # assumes PAL indexing direction=2 (Y axis)
            row = 1 + math.floor((index-1)/cols)
            col = index - (row-1)* cols
            row_ = 1 + math.floor((index-1)/rows)
            col_ = index - (row_-1)* rows
            well_ = "%s%d" % (chr(64+row), col) # PAL1 labels

        tube = "%s%d" % (chr(64+row_), col_)
        record = "%s-%s-%s,%s" % (code, who, well_, kind)
        
        autosampler.append((index, record)) # changed 7-20-2025
        
        vol = samples[ID]["volume"] # changed 7-20-2025
        if "calibration" in kind and vol >= 2*vol_min:
            kind += " w rpts"
            q.append((index, record+" rpt"))
        #


    # create sample info file
    if sort: 
        autosampler = sorted(
                        autosampler,
                        key=lambda item: nsort(item[1])
                        )

    # repeated shuffled calibration samples, changed 7-20-2025
    n = len(q)
    if n:
        print(">> Adding %d shuffled calibration repeats at the end" % n)
        random.shuffle(q)
        for index, record in q: 
            autosampler.append((index, record))
        items += n
    return autosampler, items, code, last_dataset
# 