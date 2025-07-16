
import json
from pathlib import Path
import pandas as pd
import re
from datetime import datetime
from data_processing.AMEWS_analysis import AMEWS_analysis
import os
import periodictable
import math
initial_molarity = 2
tube_racks = []
reagent_volume = 2000
feed_volume = 21e3
def calculate_concentration(element: str, volume: float, num_ions: int):
    element = getattr(periodictable, element)
    starting_ppm = initial_molarity * 1000 * element.mass
    fraction = volume / ((num_ions * reagent_volume) + (feed_volume))
    final_ppm = fraction * starting_ppm
    return final_ppm
def run_analysis(path: Path, num_tube_racks: int, num_cells: int):
    cell_plates = math.ceil(num_cells / 4)
    input_wells = ["A1", "A2", "B1", "B2"]
    output_wells = ["C1", "C2", "D1", "D2"] 
    barcodes = ["76", "70", "68"]
    tube_racks = []
   
    with open(path / "protocols" / "tube_rack_1_stamped.json") as f:
        fill_protocol = json.load(f)

    with open(path / "results"/ ("tube_rack_1_results_converted.csv")) as f:
        test = pd.read_csv(f)
        element_columns = []
        for column in test.columns:
            if re.match("axial_.*", column) is not None or re.match("radial_.*", column) is not None:
                element_columns.append(column)


    cell_fill_times = []

    curr_well = "init"

    for step in fill_protocol["actions"]:
        if re.search( "cell_plate_.", step["target_plate"]) is not None and step["action_type"] == 'dispense' and step["source_chemical"] != "solvent" and step["source_chemical"] != "standard":
            timestamp = datetime.strptime(step["dispense_timestamp"], "%m/%d/%Y %H:%M:%S.%f") 
            if step["target_well"] != curr_well:
                curr_well = step["target_well"]
                cell_fill_times.append(timestamp)
            else: 
                cell_fill_times[-1] = timestamp


    with open(path / "input_volumes.json", "r") as f:
        input_volumes = json.load(f)
    print(input_volumes)

    for i in range(num_tube_racks):
        tube_rack_path = path / ("tube_rack_%s_info.json" % (i+1))
        with open(tube_rack_path, "r") as f:
            tube_rack = json.load(f)
        tube_racks.append(tube_rack)

        
    ICP_readings = []
    for i in range(num_tube_racks):
        results = path / "results"/ ("tube_rack_%s_results_converted.csv" % (i+1))
        with open(results) as f:
            ICP_readings.append(pd.read_csv(f))

    j = 1
    cells = {}
    cell_ids = []
    total_cells = 0
    for i in range(cell_plates):
        cell_ids.append({})
        for index, well in enumerate(input_wells):
            total_cells += 1
            if total_cells > num_cells:
                break
            
            cell_ids[-1][well] = j
            name = "plate" + str(i+1) + "-" + well + "-" + str(j)
            base_columns = ["th", 
                            "sample",	
                            "barcode", 	
                            "category",  
                            "feed", 
                            "volume", 	
                            "chaser", 
                            "kind", 
                            "method",
                            "analyzed"
            ]
            base_columns += element_columns
            
            for key in input_volumes[j-1].keys():
                base_columns.append(key + ", ppm")
            cells[name] = pd.DataFrame(columns=base_columns)
            j += 1


    for ICP_reading in ICP_readings:
        for index, row in ICP_reading.iterrows():
            tube = None
            tube_rack_index = re.match("rack.", row["Sample"])
            if tube_rack_index is not None:
                tube_rack_index = tube_rack_index.group()[-1]
                tube_rack = tube_racks[int(tube_rack_index)-1]
                
            tube_well = re.search("well.*$", row["Sample"])
            if tube_well is not None:
                tube_well = tube_well.group()[4:]
                tube = tube_rack[tube_well]
            if tube is not None:
                if tube["type"] == "Calibrate":
                    cell_well = tube["sampled_well"]
                else:
                    cell_well = input_wells[output_wells.index(tube["sampled_well"])]

                cell_plate = tube["sampled_plate"][-1]
                id = cell_ids[int(cell_plate)-1][cell_well]
                name = "plate" + str(cell_plate) + "-" + cell_well + "-" + str(id)
                cell = cells[name]
                new_row = {}
                sample_time = datetime.strptime(tube["sampled_at"], "%m/%d/%Y %H:%M:%S.%f") 
                fill_time = cell_fill_times[id-1]
                new_row["th"] = (sample_time - fill_time).total_seconds() / 3600
                new_row["sample"] = row["Sample"]
                new_row["barcode"] = barcodes[int(tube_rack_index)-1]
                if tube["type"] == "Blank":
                    category = "blank"+tube_rack_index
                elif tube["type"] == "Calibrate":
                    category = "calibrate"+tube_rack_index
                else:
                    category = "rack"+tube_rack_index
                new_row["category"] = category
                new_row["feed"] = 0
                new_row["volume"] = tube["sample_volume"]
                new_row["chaser"] = tube["total_volume"] - tube["sample_volume"]
                if tube["type"] == "Blank":
                    kind = "blank"
                elif tube["type"] == "Calibrate":
                    kind = "calibration"
                else:
                    kind = "analyte"
                new_row["kind"] = kind
                new_row["method"] = row["method"]
                new_row["analyzed"] = row["Date"] + row["Time"]
                for element in element_columns:
                    new_row[element] = row[element]
                for key in input_volumes[id-1].keys():
                    concentration = calculate_concentration(key, input_volumes[id-1][key], len(input_volumes[id-1]))
                    new_row[key + ", ppm"] = concentration
                for key, value in new_row.items():
                    new_row[key] = [value]
                pandas_row = pd.DataFrame(new_row)
                cell = pd.concat([cell, pandas_row], ignore_index=True)
                cells[name] = cell
    for key in cells.keys():
        results_folder = path / "cell_results"
        results_folder.mkdir(parents=True, exist_ok=True)
        with open(path / ("cell_results/"+key+".csv"),"w") as f:
            cells[key].to_csv(f, index=False)
    analyzer = AMEWS_analysis(exp=path / "cell_results")
    analyzer.std = "Y"
    analyzer.ref_mode = 1
    analyzer.analyze_all_records()
    analyzer.do_fit("radial_Li")


            


           
