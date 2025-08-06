
from re import M
import sys, os, re
import string, math
import json, time, shutil, glob
from datetime import datetime
import numpy as np
import pandas as pd
import tkinter as tk
from tkinter import filedialog

user = os.getlogin()
sys.path.append('C:/Users/%s/Dropbox/Instruments cloud/Robotics/Unchained BK/AS Scripts/API Scripts' % user)

from CustomService import *


#######################################################################################################################

class CustomSequence:

    def __init__(self, exp = None):

        self.exp = None
        self.farm = None
        self.log = None
        self.t0 = {}
        self.c0 = {}
        self.user = os.getlogin()
        self.exp_path = r"Z:\RESULTS"
        self.unit = "mM"
        self.verbose = 0

        if exp: 
            self.exp = exp
            print("\n>> Experiment folder = %s" % exp)
            try: 
                self.results = os.path.join(exp, "Results")
                print(">> Results folder = %s" % self.results)
                os.makedirs(self.results, exist_ok=True)
            except: 
                pass
        else:
            self.select_dir()

        try:
            f = os.path.join(self.exp, "cell farm.csv")
            self.farm = pd.read_csv(f)
            print("\n>> Found cell farm %s\n\n%s\n" % (f, self.farm))
        except:
            print("\n>> Cannot find cell farm %s, abort" % f)
            sys.exit(0)


# ====================================== consolidate log files  ===============================================


    def select_dir(self): # select directory by cursor

        root = tk.Tk()
        root.withdraw()  # Hide the root window
        self.exp = filedialog.askdirectory(initialdir=self.exp_path, 
                                           title="Select an experiment")
        print("\n>> Experiment folder = %s\n" % self.exp)

        for f in os.listdir(self.exp):
            if os.path.isfile(os.path.join(self.exp, f)):
                print(f)

        self.results = os.path.join(self.exp, "Results")
        print("\n>> Results folder = %s" % self.results)
        os.makedirs(self.results, exist_ok=True)

    def consolidate_BK_records(self): # consolidate all records
        try:
            if self.exp: 
                self.consolidate_waste_logs()
                self.combine_AS_digests()
                self.add_ICP_records()
        except Exception as e:
           print(">> Cannot consolidate BK records, error = %s" % e)

    def consolidate_PAL_records(self): # consolidate all records
        try:
            if self.exp: 
                self.consolidate_waste_logs()
                self.add_ICP_records(log="sequence_log", digest="extended_time_log")
        except Exception as e:
            print(">> Cannot consolidate PAL records, error = %s" % e)

    def consolidate_waste_logs(self):  # consolidate waste logs and remove individual logs

        files = glob(os.path.join(self.exp, "waste*.csv"))
        dfs = []

        print(">> Found %d waste files to consolidate" % len(files))

        for f in files:
            if "combined" not in f:
                ID = f.replace('.csv', '').split('_')[-1]
                print("+++ processing waste from library %s" % ID)
                try:
                    df = pd.read_csv(f)
                    df.insert(0, "library", int(ID))
                    df = df[~df['container'].str.contains('glass', case=False, na=False)]
                    if len(df): 
                        dfs.append(df)
                    #os.remove(f)
                except: pass

        if len(dfs):
            waste = pd.concat(dfs, ignore_index=True)
            waste = waste.sort_values(by="library", ascending=True)
            waste = waste.drop(columns=['Unnamed: 0'])
            f = os.path.join(self.exp, "waste_ICP_combined.csv")
            waste = waste.dropna(axis=1, how='all')
            waste.to_csv(f, index=False)

    def find_rack_container(self, i):
        for _, r in self.log[i:].iterrows():
            if 'rack' in r['category']:
                return r['container']
        self.log.loc[i, 'container']

    def find_cell(self, mask):
        for _, r in self.farm.iterrows():
            if mask in r['label']:
                return r['cell']
        return None

    def index2name(self, c):
        for _, r in self.farm.iterrows():
            q = r['label'].split('-')
            if q[2]=="IN" and r['cell']==c:
                return "%s-%s-%d" % (q[0].lower(),q[1].upper(),c)
        return None

    def find_counter_well(self, c):
        for _, r in self.farm.iterrows():
            q = r['label'].split('-')
            if q[2]=="OUT" and r['cell']==c:
                if 'address' in r: 
                    return r['address']
                else:
                    return "%s:%s" % (q[0],q[1])
        return None

    def combine_AS_digests(self, log="AS_sequence_log", digest="ASDigest_vols_combined"):

        self.last_digest = None
        self.log = None
        self.t0 = {}
        self.fill = ""

        try: 
            f = os.path.join(self.exp, "%s.csv" % log) # added 7-23-2025
            print("\n>> Searching for sequence log file %s" % f)
            self.log = pd.read_csv(f)
            if 'code' in self.log.columns: # added 7-1-2025
                self.log['code'] = self.log['code'].astype(str).str.replace(r'\..*$', '', regex=True) 
        except Exception as e:
            print("ERROR in reading the AS sequence log: %s" % e)
            return 0

        print("\n\n>> Using %s.csv file to consolidate AS digests\n" % log)
        self.log['AS log'] = self.log['AS log'].fillna("")

        j=-1

        self.log['barcode'] = pd.to_numeric(self.log['barcode'], errors='coerce')
        self.log['barcode'] = self.log['barcode'].fillna(0).astype(int)

        dfs = []
        for i, r in self.log.iterrows():
            ID = r["ID"]
            category = r["category"]
            container = self.find_rack_container(i)
            barcode = r["barcode"]
            f = r["AS log"]
            if f:
                f = f.replace("ASMain","ASDigest_vols")
                f = f.replace(".log",".csv")
                g = os.path.join(self.exp, f)
                df = pd.read_csv(g)
                # print("+++ processing digest %s" % g)
                if "fill" in category:
                    if category != self.fill:
                        self.fill = category

                if len(df):
                    print(">> Processed %s : ID=%d, container=%s, barcode=%d, category=%s" % (f, ID, container, barcode, category))
                    df.insert(0, "library", ID)
                    df.insert(1, "container", container)
                    df.insert(2, "barcode", barcode)
                    df.insert(3, "category", category)
                    if self.fill: 
                        df.insert(4, "feed", self.fill)
                    else:
                        df.insert(4, "feed", "fill1")
                    dfs.append(df)

        c0 = np.nan

        if len(dfs):
            self.last_digest = pd.concat(dfs, ignore_index=True)
            del dfs
            self.last_digest['sample'] = None
            self.last_digest.insert(0, 'sample', self.last_digest.pop('sample'))

            for i, r in self.last_digest.iterrows(): # zero times from the first fill
                c = self.find_cell("%s-%s" % (r['plate from'], r['well from']))
                self.last_digest.loc[i, 'index'] = c
                if "load" in r['category']:
                    c = self.find_cell("%s-%s" % (r['plate to'], r['well to']))
                    self.last_digest.loc[i, 'index'] = c
                elif "fill" in r['category']:
                    c = self.find_cell("%s-%s" % (r['plate to'], r['well to']))
                    if "source" in r["plate from"]: 
                        dt = pd.to_datetime(r["datetime"], errors="coerce") # changed 7-23-2025 to deal with inconsistent dates
                        self.last_digest.loc[i, 'index'] = c
                        if c: 
                            self.t0[c] = dt
                            c0 = c
                    else:
                        self.last_digest.loc[i, 'category'] = r['category'].replace("fill","calibrate") # changed 7-23-2025
                        if c is None: # added 7-27-2025
                            self.last_digest.loc[i, 'sample'] = "%s-BK-%s" % (r['container'], r['well to'])
                            self.last_digest.loc[i, 'index'] = c0
                else: 
                    self.last_digest.loc[i, 'sample'] = "%s-BK-%s" % (r['container'], r['well to'])
                    

            print("\n\n>> Took t0 from cell fill record: %s\n" % self.t0)

            for c, dt in self.t0.items():
                print("--- t0 for cell well %s = %s" % (c, dt))

            self.last_digest["th"] = np.nan
            self.last_digest['well from'] = self.last_digest['well from'].fillna('')

            for i,r in self.last_digest.iterrows():
                    c = r["index"]
                    t= r["datetime"]
                    if pd.notna(c) and c in self.t0 and pd.notna(t): # changed 7-23-2025 to deal with aborted digests
                        dt = pd.to_datetime(t, errors="coerce") # changed 7-23-2025 to deal with inconsistent dates
                        dt -= self.t0[c]
                        self.last_digest.loc[i, 'th'] = dt.total_seconds()/3600

            f = os.path.join(self.exp,"%s.csv" % digest)

            try: 
                self.last_digest.to_csv(f, index=False)
                print("\n>> Combined digest files to %s" % f)
            except Exception as e:
                print("\n>> Cannot combine files, error = %s" % e)
            return 1
        else:
            print("\n>> Did not find digests to consolidate, abort")

        return 0

    def digest_new_row(self): # temple row from self.last_digest
        return {col: np.nan if pd.api.types.is_float_dtype(dtype) or 
              pd.api.types.is_object_dtype(dtype)
              else dtype.type()  # default for int, bool, etc.
              for col, dtype in self.last_digest.dtypes.items()} 


    def add_ICP_records(self, log="AS_sequence_log", digest="ASDigest_vols_combined"):

        os.makedirs(self.exp, exist_ok=True)
        os.makedirs(self.results, exist_ok=True)

        self.std = None

        try: 
            self.last_digest = pd.read_csv(os.path.join(self.exp, "%s.csv" % digest))
            self.log = pd.read_csv(os.path.join(self.exp, "%s.csv" % log))
        except:
            print("\n>> Cannot find combined digest and/or sequence log files, abort")
            return 0

        print("\n\n>> Using %s file to add ICP records to digests\n" % log)

        # added 7-27-2025 removing duplicative calibration records
        self.last_digest = self.last_digest.rename(columns={'index': 'cell'})
        mask = self.last_digest["category"].str.startswith("calibrate")
        dups = self.last_digest[mask].duplicated(subset="sample", keep="last")
        self.last_digest = self.last_digest.drop(self.last_digest[mask][~dups].index)
        #

        flag = 0
        for _, r in self.log.iterrows():
            container = r["container"]
            if "rack" in r["category"]:
                files = glob(os.path.join(self.exp,"run_%s_*_converted.csv" % container))
                if files:
                    print("\n>> Processing container %s: %d file(s))" % (container,len(files)))
                    for f in files:
                        print(">> add record from %s" % os.path.basename(f))
                        df = pd.read_csv(f)
                        df['Date'] += ' ' + df['Time']
                        df.rename(columns={'Date': 'analyzed'}, inplace=True)
                        df.drop(columns=['Time'], inplace=True)
                        if flag==0:
                            flag=1
                            for col in df.columns:
                                if col != 'Sample' and col not in self.last_digest.columns:
                                    self.last_digest[col] = None

                        for _, row in df.iterrows():
                            sample = row['Sample']
                            kind = row['kind']

                            if kind.startswith("calibrate"): # add external standard ICP calibration
                                new = self.digest_new_row()
                                new["container"] = container
                                new["barcode"] = r["barcode"]
                                new["category"] = r["category"]
                                row['kind'] = "standard %s" % sample
                                for col in df.columns:
                                    if col != 'Sample': 
                                        new[col] = row[col]
                                self.last_digest.loc[len(self.last_digest)] = new
                                print("--- added ICP standard (%s) for container %s" % (sample, container))
                            else:
                                c = self.last_digest['sample'] == sample
                                if c.any(): 
                                    q = c.idxmax()  # index of the first occurrence
                                    if "rpt" not in kind: # changed 7-27-2025
                                        for col in df.columns:
                                            if col != 'Sample': 
                                                self.last_digest.loc[q, col] = row[col]
                                    else: # added 7-27-2025
                                        new = self.last_digest.loc[q].copy()
                                        print("+++ %s: %s" % (sample, kind))
                                        for col in df.columns:
                                            if col != 'Sample': 
                                                new[col] = row[col]
                                        self.last_digest = pd.concat(
                                            [self.last_digest, pd.DataFrame([new], columns=self.last_digest.columns)],
                                            ignore_index=True
                                            )
                                else:
                                    print("--- Sample %s does not exist in AS logs" % sample)

        if flag==0: 
            print("\n>> No ICP analysis files to add, will only split data")
        else: 
            print("\n>> added ICP records")

        f = os.path.join(self.exp,"%s_w_ICP.csv" % digest)
        self.last_digest.to_csv(f, index=False)

        self.last_digest = self.last_digest[~self.last_digest['category'].str.contains('fill|load', case=False, na=False)]
        self.last_digest = self.last_digest.drop(columns = ["datetime", "container", "library","time, min",
                                            "plate from", "well from", "plate to", "well to"])

        if any("address" in col for col in self.last_digest.columns):
               self.last_digest = self.last_digest.drop(columns = ["address from", "address to"])

        self.std = self.last_digest[self.last_digest['kind'].str.contains('standard', case=False, na=False)]

        print("\n>> Grouping by cells")
        grouped = self.last_digest.groupby(['cell'])
        feeds = self.last_digest['feed'].dropna().unique()

        print(">> Unique feeds: %s" % feeds)

        self.c0 = {}

        for q in feeds: # for each cell fill, add estimated feed concentrations
            print("+++ adding concentrations from %s" % q)
            f= os.path.join(self.exp, "%s.json" % q)
            with open(f, 'r') as j:
                  self.c0[q] = json.load(j)
                  print("--- loaded %s" % f)

        print(">> Added all feeds\n")

        for (c,), group in grouped:
            if self.std is not None: 
                group = pd.concat([group, self.std], ignore_index=True)
            # print(group)
            ID = self.find_counter_well(c)
            print("+++ Extracting cell %d, counter address %s, %d group records" % (c, ID, len(group)))
            f= os.path.join(self.results, "%s.csv" % self.index2name(c))
            if ID:
                for q in self.c0:
                    if ID in self.c0[q]:
                        u = self.c0[q][ID]
                        if "unit" in u:
                            self.unit = u["unit"]
                        if "constitution" in u:
                            for el, conc in u["constitution"].items():
                                label = "%s, %s" % (el, self.unit)
                                if label not in group.columns:
                                    group[label] = None
                                group.loc[group['feed'] == q, label] = conc

            group['feed'] = pd.factorize(group['feed'])[0]

            if "analyze" in group.columns: 
                group = group.dropna(subset=['kind'])
                group = group.drop(columns=["analyzed", "method"])

            group = group.drop(columns=["cell"])
            group.insert(0, 'th', group.pop('th'))      # time in hours
            group = group.sort_values(by="th", na_position="last") # sort by time

            #group['feed'] = group['feed'].astype('Int64')
            #group['feed'] = group['feed'].replace(-1, pd.NA)
            #group['volume'] = group['volume'].astype('Int64')
            #group['volume'] = group['volume'].replace(0, pd.NA)
            
            group.to_csv(f, index=False)

        return 1

    def check_BK_containers(self):  # check_containers vs ASDigests, added 7-25-2025
        self.log = None

        try: 
            f = os.path.join(self.exp, "AS_sequence_log.csv")
            print("\n>> Searching for sequence log file %s" % f)
            self.log = pd.read_csv(f)
            if 'code' in self.log.columns: # added 7-1-2025
                self.log['code'] = self.log['code'].astype(str).str.replace(r'\..*$', '', regex=True) 
        except Exception as e:
            print("ERROR in reading the AS sequence log: %s" % e)
            return 0

        print("\n\n>> Using AS log file to check containers against AS digests\n")
        self.log['AS log'] = self.log['AS log'].fillna("")

        self.racks = self.log[self.log["category"].str.startswith("rack", na=False)]["category"].unique()

        for rack in self.racks:

            skip = 0
            missing = []
            barcode = self.log.loc[self.log["category"] == rack, "barcode"].iloc[0]

            if pd.isna(barcode) or "XX" in str(barcode):
                continue

            container = self.log.loc[self.log["category"] == rack, "container"].iloc[0]
            
            print("\nChecking %s, barcode = %s, container = %s **************************" % (rack, str(barcode), container))

            f = os.path.join(self.exp,"Active_%s.json" % container)
            try: 
                with open(f, 'r') as j:
                    c = json.load(j)
                    old = c.copy()
                    content = c["creator"]["content"]
                    print(">> Container found, %d wells\n" % len(content))
            except:
                continue

            for ID in content:
                plate, well = ID.split(":")
                flag=0  

                for i, r in self.log.iterrows(): # check all digests for this position
                    if r["barcode"] == barcode:
                        f = r["AS log"]
                        if f:
                            f = f.replace("ASMain","ASDigest_vols")
                            f = f.replace(".log",".csv")
                            f = os.path.join(self.exp, f)
                            try: 
                                df = pd.read_csv(f)
                            except: 
                                continue
                            if ((df["plate to"] == plate) & (df["well to"] == well)).any():
                                flag =1
                                break

                if flag ==0:
                    content[ID]["type"] = "missing"
                    print("AS logs missing %s" % ID)
                    missing.append(well)

            if len(missing):
                print("\n%s missing AS records for %d wells\n" % (rack, len(missing)))

                f = os.path.join(self.exp, "Active_%s_edited.json" % container)
                with open(f, 'w') as j:
                    json.dump(c, j, indent=4)

                f = os.path.join("Z:\CONTAINERS", "Container_%s.json" % container)
                with open(f, 'w') as j:
                    json.dump(c, j, indent=4)


if __name__ == "__main__":
    seq  = CustomSequence()
    # seq.select_dir()
    # seq.check_BK_containers()
    seq.consolidate_BK_records()

