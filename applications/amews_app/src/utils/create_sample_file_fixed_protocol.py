import os
import random

def write_sampleinfo(
        autosampler: dict,
        batch: str,
        start: int = 0,  # start offset
        items: int = 0,  # number of items in the rack
        description: str = "Sample information file",
        calibrate: bool = False,
        rinse: bool = False,
        method: str = "mina_hts_2",
    ):
        
    

        r = "rack%d.sifx" % items
        n = 5 + items + int(rinse)
        filepath = os.path.join(".", r)

        with open(filepath, "w") as file:
            file.write("[System Description]\n")
            file.write("Description=%s\n" % description)
            file.write("MaxNoOfSamples=%d\n" % n)
            file.write("[Constant Parameters]\n")
            file.write("BatchID=%s\n" % batch)
            file.write("VolumeUnits=Vol,mL,0.001,,\n")
            file.write("WeightUnits=Wt,g,1.00,,\n")
            file.write("[User Defined List]\n")
            file.write("NumberOfUserDefined=2\n")
            file.write("UserDefined1=kind\n")
            file.write("UserDefined2=method\n")
            file.write("UserDefined3=\n")
            file.write("UserDefined4=\n")
            file.write("UserDefined5=\n")
            file.write("[Variable Parameter List]\n")
            file.write("NumberOfParameters=5\n")
            file.write("Parameter1=SampleNo\n")
            file.write("Parameter2=AutosamplerLocation\n")
            file.write("Parameter3=SampleID\n")
            file.write("Parameter4=UserDefField1\n")
            file.write("Parameter5=UserDefField2\n")
            file.write("[Variable Parameter Data]\n")
            file.write("NumberOfDataValues=%d\n" % n)

            j = 0
            m = 1  # item counter
            d = 0  # data counter
            queue = []

            # important: sample wetting, home
            file.write("Data%d=1,0,rinse,%s,%s\n" % (d+1, "rinse", method)),
            d +=1

            if calibrate:
                file.write(
                    "Data%d=2,1,before,%s,%s\n" % (d+1, "calibrate",  method)
                )  # well 1
                m += 1
                d += 1
            for i, label in autosampler:
                if j >= start and j < items:
                    if "missing" not in label.lower():
                        file.write(
                            "Data%d=%d,%d,%s,%s\n"
                            % (d + 1, m + 1, i + 10, label, method)
                        )
                        m += 1
                        d += 1
                j += 1

            if calibrate:
                file.write(
                    "Data%d=%d,1,after,%s,%s,\n"
                    % (d +1, m + 1, "calibrate rpt", method)
                )  # well 1
                m += 1
                d += 1

            if rinse:  # optional extra rinse at the end of a sequence, home
                for i in range(rinse):
                    queue.append("rinse")
                    file.write(
                        "Data%d=%d,0,rinse,%s,%s\n"
                        % (d + 1, m + 1, "rinse", method)
                    )
                    m += 1
                    d += 1

            file.close()
            return filepath