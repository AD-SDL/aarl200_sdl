from hashlib import sha224
import sys, os
import string, math, re, random
import json, time
from glob import glob
from datetime import datetime
import numpy as np
import pandas as pd
import tkinter as tk
from tkinter import filedialog
import pandas as pd

class AS_log():
    
    def __init__(self):
        root = tk.Tk()
        root.withdraw()
        self.ID = 0
        self.excerpt = None 
        self.digest = None
        self.dir = ""
        self.name = ""
        self.substrates = {}
        self.sequence=["Input : Substrate","Input : Position","Input : Well Row","Input : Well Column"]

    def select_log(self): # Open a file dialog to select a file
        return filedialog.askopenfilename(
            title="Select a log File", 
            filetypes=[("log files", "*.log")]  # Filter to only show .csv files
        )

    def to_csv(self, df, name):
        f = os.path.join(self.dir, "%s.csv" % name)
        df.to_csv(f, index=False)

# ----------- # added 7-20-2025 - operations analysis to find execution times ------------------------------------

    def do_operations_analysis(self, f):
        try:
            df = pd.read_csv(f, sep='\t')
            self.operations_analysis(f, df)
        except Exception as e:
            print(">> AS log reading error occurred: %s\n" % e)
            return 0

    def operations_analysis(self, name, df): 
        classifier = "Script Class"
        df = df[df[classifier] != df[classifier].shift()]
        df = df[df["Script Function"] == "Execute"]
        df = df.drop(columns=["Script Function"])
        df["Active Script"] = df["Active Script"].str.replace(r"^ASMain,?", "", regex=True)
        df["Error"] = df["Error"].replace("FALSE", np.nan)
        df["Time"] = pd.to_datetime(df["Time"], format="%m/%d/%Y %H:%M:%S.%f")
        df["delta (min)"] = df["Time"].diff().dt.total_seconds() / 60  # time operationd
        df["delta (min)"] = df["delta (min)"].shift(-1) # shift up by one row
        df = df[(df["delta (min)"].isna()) | (df["delta (min)"] >= 0.05)]  # remove short operations
        print(df)
        out = name.replace("ASMain","ASOperations")
        self.to_csv(df, out)
# --------------------------------------------------------------------------------------------------------------------

    def read_log(self, f): # read AS log
        if f:
            try:
                df = pd.read_csv(f, sep='\t')
            except Exception as e:
                print(">> AS log reading error occurred: %s\n" % e)
                return 0
        else:
            print(">> No AS log file found\n")
            return 0
 

        self.dir, f = os.path.split(f)
        self.name, _ = os.path.splitext(f)

        self.operations_analysis(self.name, df) # added 7-20-2025 

        try: 
            self.ID = int(os.path.basename(self.dir))
        except ValueError:
            self.ID = 0
        print(">> folder ID=%d\n" % self.ID)
        
        s = os.path.join(self.dir, "substrates_%d.json" % self.ID)
        if os.path.exists(s): 
            with open(s, 'r') as q:
                self.substrates = json.load(q)
    
        keys=["Substrate","Position","Well Row","Well Column","Volume Dispensed","Weight"]

        df = df[df['Well Position'].notna()]
        df = df.fillna("")

        df = df[df["Parameter Name"].str.contains("put : ", na=False)]
        df = df[~df["Parameter Value"].str.contains("Wash|Clean|Drain", na=False)]

        #self.to_csv(df, "simplified")


        rs=[]

        try: # changed 7-22-2025
            for _, row in df.iterrows():
                t= row["Parameter Value"]
                s= row["Parameter Name"]
                s_ = s.split(':')[1].strip()
                if s_ in keys:
                    if self.iszero(s_, t, "Volume") or self.iszero(s_, t, "Weight"):
                        continue
                    r={"index" : row["Index"],
                        "timestamp" : row["Time"].split('.')[0],
                        "well" : int(row["Well Position"].strip("[]")),
                        "name" : s,
                        "value" : t,
                        }
                    rs.append(r)

            self.excerpt = pd.DataFrame(rs).fillna("")

            if self.parse_excerpt():
                self.name = self.name.replace("ASMain","ASExcerpt")
                self.to_csv(self.excerpt, self.name)

                print(self.excerpt)
                self.excerpt_name = self.name
                return 1

        except Exception as e:
            print("ERROR: cannot make AS digest or parse - %s" % e)

        return 0

    def iszero(self, s, t, key):
        return key in s and t=="0"

    def search_sequence(self, i): # search for the well addressing sequence
        well = ""
        j=0
        for s in self.sequence:
            if s != self.excerpt.iloc[i+j]["name"]:
                self.excerpt.loc[i,"name"] = "Delete"
                return
            else:
                well+=self.excerpt.iloc[i+j]["value"]+", "
            j+=1
        self.excerpt.loc[i,"value"] = well[:-2]

    def parse_excerpt(self):
        for i, row in self.excerpt.iterrows():
            if "Input" in row["name"]:
                self.search_sequence(i)

        if "name" in self.excerpt.columns: # changed 7-21-2025
            self.excerpt = self.excerpt[~self.excerpt["name"].str.contains("Delete|Position|Row|Column", na=False)]
            self.excerpt  = self.excerpt.reset_index(drop=True)
        else:
           return 0

        return 1

    def digest_volumes(self): #make a digest of volumes
        last=""
        flag=0
        kind = 0
        rs = []
        k=-1
        template={"to stamp": "", "from well" : "", "to well" : "", "to vol": ""}
        f = self.name.replace("ASExcerpt","ASDigest_vols")
        f = os.path.join(self.dir,"%s.csv" % f)
        self.digest_vol_name = f
        for i, row in self.excerpt.iterrows():
            s=row["name"]
            t=row["value"]

            if "Output : Volume" in s: 
                flag = 0
            else:
                if flag==0 and t !=last:
                    rs.append(template.copy())
                    last = ""
                    kind=0
                    flag=1
                    k+=1
                    
                if not rs[k]["from well"]:
                    if kind==0: 
                        rs[k]["from well"]=last=t

                else:
                    if rs[k]["from well"] != t:
                       rs[k]["to well"] = last = t 
                       kind = 1
                       
            if "Output : Volume" in s: 
                rs[k]["to vol"]+=t+","
                rs[k]["to stamp"]=row["timestamp"]
                
        qs = []
        k=1
        last_from = ""

        # self.pre_digest = pd.DataFrame(rs).fillna("")

        for r in rs:
            q={}
            q["index"]=k
            v=r["to vol"].rstrip(',').split(",")
            q["datetime"] = r["to stamp"]
            q["volume"]= np.nan
            q["chaser"]= np.nan

            if r["to well"]:
                last_from = r["from well"]
                q["plate from"], q["well from"] = self.plate_well(r["from well"])
                q["plate to"], q["well to"] = self.plate_well(r["to well"])
                try: 
                    q["volume"]=int(v[0])
                except: pass
                try: 
                    q["chaser"]=int(v[1])
                except: pass
            else:
                if r["from well"] == last_from:
                    continue
                q["plate from"] = "outside" 
                q["well from"] = ""
                q["plate to"], q["well to"] = self.plate_well(r["from well"])
                try: # changed 7-23-2025 to deal with randomly aborted runs
                    vols = [int(x) for x in v]
                    q["volume"] = sum(vols)
                except:
                    q["volume"] = np.nan

            qs.append(q)
            k+=1

        self.digest = pd.DataFrame(qs).fillna("")

        self.digest.to_csv(f, index=False)
        print(self.digest)
        
    def digest_weights(self): # make a digest of weights
        last=""
        rs = []
        flag=0
        k=-1
        template={"to stamp": "", "from well" : "", "to weight": ""}
        f = self.name.replace("ASExcerpt","ASDigest_wts")
        f = os.path.join(self.dir,"%s.csv" % f)

        for i, row in self.excerpt.iterrows():
            s=row["name"]
            t=row["value"]

            if "Input" in s:
                if "Balance" not in t:
                    if t !=last:
                        flag=0
                        rs.append(template.copy())
                        last = ""
                        k+=1
                else:
                    flag+=1
                    
                if not rs[k]["from well"]:
                    rs[k]["from well"]=last=t
                       
            if "Output : Weight" in s and flag==1: 
                rs[k]["to weight"]+=t+", "
                rs[k]["to stamp"]=row["timestamp"]

        qs = []
        k=1
        for r in rs:
            q={}
            wts = r["to weight"][:-2]
            if wts:
                data = list(map(float, wts.split(', ')))
                avg = np.mean(data)
                std= np.std(data)
                q["index"]=k
                q["plate from"], q["well from"] = self.plate_well(r["from well"])
                q["weights"]=wts
                q["AVG"]=round(avg,2)
                q["STD"]=round(std,2)
                q["RSD, %"] = round(100*std/avg,3)
                q["datetime"] = r["to stamp"]
            qs.append(q)
            k+=1

        self.digest = pd.DataFrame(qs).fillna("")

        self.digest.to_csv(f, index=False)
        print(self.digest)

    def plate_well(self, address):  # plate from the substrate
        a = address.split(', ')
        b0=a[0].strip()
        b1=a[1].strip()
        if "Balance" in b0:
            well = ""
        else:
            well = "%s%d" % (chr(int(a[2])+64), int(a[3]))
        if self.substrates:
            for s in self.substrates:
                r = self.substrates[s]
                if r["kind"]==b0 and r["position"]==b1:
                    return s, well
        return "%s, %s" % (b0, b1), well
    
    def process_log(self, f): # process AS log
        if f:
            if self.read_log(f):
                self.process_excerpt()

    def process_excerpt(self): # process AS log excerpt
        if self.excerpt['name'].str.contains('Weight').any():  # makes a digest of weights
            print("\n>> Writes a digest of weights")
            self.digest_weights()
        if self.excerpt['name'].str.contains('Volume').any():  # makes a disgest of volumes
            print("\n>> Writes a digest of volumes")
            self.digest_volumes()

    def consolidate_logs(self, d): # used master log to consolidate logs
        f = os.path.join(d, "AS_sequence_log.csv")
        if os.path.exists(f):
            df = pd.read_csv(f)
            union = []
            for i,row in df.iterrows():
                f = row["AS_log"].replace("ASMain","ASExcerpt")
                f = os.path.join(d, f)
                if os.path.exists(f): 
                    c = pd.read_csv(f)
                    c["container"] = row["container"]
                    c["ID"] = row["ID"]
                    c["category"] = row["category"]
                    union.append[c]
            self.excerpt = pd.concat(union, axis=0, ignore_index=True)
            del(union)
            self.name = "ASExcerpt_union"
            f = os.path.join(d, "%s.csv" % self.name)
            self.excerpt.to_csv(f)
            self.process_excerpt(self.name)

if __name__ == "__main__":
    asl = AS_log()
    f=asl.select_log()
    asl.process_log(f)
    # asl.do_operations_analysis(f)





