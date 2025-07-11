import pandas as pd 
import math
from datetime import datetime


"""Refrence dictionary mapping metals to integers"""

metals = {
            "Li": 3,  # Lithium
            "Na": 11,  # Sodium
            "K": 19,  # Potassium
            "Rb": 37,  # Rubidium
            "Cs": 55,  # Cesium
            "Be": 4,  # Beryllium
            "Mg": 12,  # Magnesium
            "Ca": 20,  # Calcium
            "Sr": 38,  # Strontium
            "Ba": 56,  # Barium
            "Sc": 21,  # Scandium
            "Ti": 22,  # Titanium
            "V": 23,  # Vanadium
            "Cr": 24,  # Chromium
            "Mn": 25,  # Manganese
            "Fe": 26,  # Iron
            "Co": 27,  # Cobalt
            "Ni": 28,  # Nickel
            "Cu": 29,  # Copper
            "Zn": 30,  # Zinc
            "Y": 39,  # Yttrium
            "Zr": 40,  # Zirconium
            "Nb": 41,  # Niobium
            "Mo": 42,  # Molybdenum
            "Ru": 44,  # Ruthenium
            "Rh": 45,  # Rhodium
            "Pd": 46,  # Palladium
            "Ag": 47,  # Silver
            "Cd": 48,  # Cadmium
            "Hf": 72,  # Hafnium
            "Ta": 73,  # Tantalum
            "W": 74,  # Tungsten
            "Re": 75,  # Rhenium
            "Os": 76,  # Osmium
            "Ir": 77,  # Iridium
            "Pt": 78,  # Platinum
            "Au": 79,  # Gold
            "Hg": 80,  # Mercury
            "La": 57,  # Lanthanum
            "Ce": 58,  # Cerium
            "Pr": 59,  # Praseodymium
            "Nd": 60,  # Neodymium
            "Pm": 61,  # Promethium
            "Sm": 62,  # Samarium
            "Eu": 63,  # Europium
            "Gd": 64,  # Gadolinium
            "Tb": 65,  # Terbium
            "Dy": 66,  # Dysprosium
            "Ho": 67,  # Holmium
            "Er": 68,  # Erbium
            "Tm": 69,  # Thulium
            "Yb": 70,  # Ytterbium
            "Lu": 71,  # Lutetium
        }

def convert_report(name): # convert report to a better readable format
    views = ["radial", "axial"]
    with open(name, 'r') as file:
        df = pd.read_csv(file)
    if 'View' not in df.columns:
        df['View'] = 1
    df.rename(columns={"User Value 1": "kind"},   inplace=True)
    df.rename(columns={"User Value 2": "method"}, inplace=True)

    sample_IDs = df['Sample ID'].unique().tolist()  
    elements = sorted(df['Elem'].unique().tolist(), 
                        key=lambda x: metals[x])
    qs = []

    for ID in sample_IDs:
        subset = df[df['Sample ID'] == ID]
        q = { "Sample": ID, "kind" : "sample", "method" : "", "Date": "", "Time": ""}

        for e in elements:
            q["radial_%s" % e] = math.nan
            q["axial_%s" % e] = math.nan
            for _, row in subset.iterrows():  # logs the last measurement for each sample ID and element
                if row["Elem"] == e:
                    i=int(row["View"])
                    u="%s_%s" % (views[i], e)
                    q[u] = row["Int (Corr)"]
                    q["Date"] = row["Date"].replace("/","-")
                    t = datetime.strptime(row["Time"], "%I:%M:%S %p")
                    q["Time"] =  t.strftime("%H:%M:%S")

                    if "method" in row: 
                        q["method"] = row["method"].strip()
                        
                    if "kind" in row: 
                        q["kind"] = row["kind"].strip()
                        
                    
        if "rinse" not in q["kind"] and "WASH" not in q["method"]:
            qs.append(q)

    if qs: 
        out = pd.DataFrame(qs)
        out = out.dropna(axis=1, how='all')
        name = name.replace(".csv", "_converted.csv")
        with open(name, 'w') as file:
            out.to_csv(file, index=False)
        