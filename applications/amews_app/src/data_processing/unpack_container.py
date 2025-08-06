from typing import Any
import math

def unpack_self_container(container: Any, sort: bool = False):
        # sort autosampler record in the normal autosampler order (right nearmost)

        if not container:
            return 0

        autosampler = {}
        elements = []

        code = container["code"]


        rack = container["rack"]
        
        creator = container["creator"]
        samples = creator["content"]
        who = creator["location"]

        rows = rack["rows"]
        cols = rack["columns"]
        items = rack["items"]

        for ID in samples:
            # original well designations
            kind = samples[ID]["type"]
            well = ID.split(":")[-1]  # creater well

            # elemental composition
            es = list(samples[ID]["constitution"])
            s = ", ".join(es)
            for e in es:
                if e not in elements:
                    elements.append(e)

            # ICP rack and autosampler designations
            if who == "BK":
                row = ord(well[0]) - ord("A") + 1
                col = int(well[1:])
                row_ = rows + 1 - row
                col_ = cols + 1 - col
                index = col_ + (row - 1) * cols
                well_ = well

            if who == "PAL1":
                index = int(well)  # assumes PAL indexing direction=2 (Y axis)
                row = 1 + math.floor((index - 1) / cols)
                col = index - (row - 1) * cols
                row_ = 1 + math.floor((index - 1) / rows)
                col_ = index - (row_ - 1) * rows
                well_ = "%s%d" % (chr(64 + row), col)  # PAL1 labels

           

            autosampler[index] = "%s-%s-%s,%s" % (
                code,
                who,
                well_,
                kind,
            )

            

        # create sample info file
        if sort:
            autosampler = dict(sorted(autosampler.items()))

        return autosampler, items, code