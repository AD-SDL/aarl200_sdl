import datetime
import json
import math
import shutil
import random
from madsci.common.types.workflow_types import WorkflowDefinition
from madsci.common.types.step_types import StepDefinition
from madsci.client.experiment_application import ExperimentApplication, ExperimentDesign
from madsci.client.node.rest_node_client import RestNodeClient
from pathlib import Path
from utils.log_parsing import read_logs, add_timestamps
from utils.generate_protocol import generate_protocol
from utils.assign_timestamps import assign_timestamps
from utils.create_sample_file import create_sample_file
from utils.AMEWS_types import AMEWS_tube
from utils.big_kahuna_protocol_types import BigKahunaProtocol
from utils.parse_input_csv import parse_input_csv
from data_processing.current_data_processing import run_analysis
from data_processing.icp_processing import convert_report
import pandas as pd
import os
from data_processing.unpack_container import unpack_self_container
from utils.create_sample_file_fixed_protocol import write_sampleinfo
class AMEWSApp(ExperimentApplication):
    """A demonstration and benchmarking experimental application: mixing colors autonomously."""
    url = "http://controlroom1.cse.anl.gov:8002/"
    workflow_directory = Path("../workflows").resolve()
    experiment_design = ExperimentDesign(experiment_name="AMEWS Cell Tests")
    network_output_path = Path("/run/user/1000/gvfs/smb-share:server=sheldon.cse.anl.gov,share=aarl200/RESULTS").resolve()
    network_input_path = Path("/run/user/1000/gvfs/smb-share:server=sheldon.cse.anl.gov,share=aarl200/RESULTS").resolve()
    
    output_path = Path("/home/aarl/Documents/AMEWS_output").resolve()
    
if __name__ == "__main__":
    
    experiment_app = AMEWSApp()
    
    current_time = datetime.datetime.now()
    with experiment_app.manage_experiment(
        run_name=f"AMEWS Experiment Run {current_time}",
        run_description=f"Run for AMEWS experiment, started at ~{current_time}",
    ):
        #folder_name = "tests BK_run24 July-August 2025/BK_run24_20250723_074837 8-cell run"
        folder_name = "BK_run24_20250807_142310"
        experiment_app.output_path = experiment_app.output_path / folder_name
        experiment_app.network_output_path = experiment_app.network_output_path / folder_name
        experiment_app.output_path.mkdir(parents=True, exist_ok=True)
        experiment_app.network_output_path.mkdir(parents=True, exist_ok=True)
        "Input Variables"
        num_cells = 24
        sampling_rounds = 6
        sampling_delay_mins = 180
        
        input_folder = experiment_app.network_input_path / folder_name
        print(os.listdir(input_folder))
        labjack_client = RestNodeClient("http://146.139.45.9:2001")
        measured_racks = []
        with open(input_folder / "Active_6QW03.json", 'r') as f:
             container = json.load(f)
        autosampler, items, code, last_dataset = unpack_self_container(container)
        sample_info_file_path = write_sampleinfo( 
            autosampler = autosampler,
            batch=code,
            items=items,
            description="Sample information file for Mina HTS 2",
            calibrate=True,
            rinse=True,
            method="mina_hts_3",
        )
        raise("crap")
        with open(input_folder / "AS_sequence_log.csv", 'r') as f:
             sequence_log = pd.read_csv(f)
        container_labels = []
        for index, row in sequence_log.iterrows():
             if "rack" in row["category"]:
                container_labels.append(row["container"])
        sampled_racks = []
        for label in container_labels:
            rack = json.load((input_folder / ("Active_"+label + ".json")).open())
            sampled_racks.append(rack)
        total_racks = len(sampled_racks)
        input_locations = ["supply_slot_1", "supply_slot_2", "supply_slot_3", "supply_slot_4", "supply_slot_5"]
        icp_workflow = None
        
        while len(measured_racks) < total_racks:
            icp_workflow = experiment_app.workcell_client.query_workflow(icp_workflow.workflow_id) if icp_workflow else None
            
            
            if icp_workflow is None and len(sampled_racks) > len(measured_racks):
                    labjack_state = labjack_client.get_state()
                    if labjack_state["volumes"]["AIN0"] > 0.95*113.56:
                        print("Not enough space in barrel, will not run icp yet")
                    else:
                        autosampler, items, code, last_dataset = unpack_self_container(sampled_racks[len(measured_racks)])
                        sample_info_file_path = write_sampleinfo(
                            autosampler = autosampler,
                            batch=code,
                            items=items,
                            description="Sample information file for Mina HTS 2",
                            calibrate=True,
                            rinse=True,
                            method="mina_hts_3",
                        )
                        experiment_app.workcell_client.submit_workflow(
                            experiment_app.workflow_directory / "transfer_to_icp.workflow.yaml", parameters={"source_location": input_locations[len(measured_racks)]}
                        )
                        icp_workflow = WorkflowDefinition.from_yaml(experiment_app.workflow_directory / "run_icp.workflow.yaml")
                        if len(measured_racks) == 0:
                            icp_workflow.steps = icp_workflow.steps[0:2]
                        elif len(measured_racks) == len(sampled_racks) - 1:
                            icp_workflow.steps = icp_workflow.steps[1:]
                        else:
                             icp_workflow.steps = [icp_workflow.steps[1]]
                        randcode = random.randint(1000, 9999)
                        icp_workflow = experiment_app.workcell_client.submit_workflow(
                        icp_workflow, parameters={"dataset_name": last_dataset, "sample_info_file": str(sample_info_file_path)}, await_completion=False)

                    
            if icp_workflow and icp_workflow.status.completed:
                    experiment_app.workcell_client.submit_workflow(
                            experiment_app.workflow_directory / "transfer_from_icp.workflow.yaml", parameters={"target_location": input_locations[len(measured_racks)]}
                        )
                    code = sampled_racks[len(measured_racks)]["code"]
                    experiment_app.data_client.save_datapoint_value(
                        icp_workflow.get_datapoint_id_by_label("result_file"), experiment_app.output_path / ("run_"+code+".csv"))
                    measured_racks.append(sampled_racks[len(measured_racks)])
                    try:
                        convert_report(str(experiment_app.output_path / ("run_"+code+".csv")))
                        experiment_app.data_client.save_datapoint_value(
                            icp_workflow.get_datapoint_id_by_label("result_file"), experiment_app.network_output_path / ("run_"+code+".csv"))
                        convert_report(str(experiment_app.network_output_path / ("run_"+code+".csv")))
                        #run_analysis(experiment_app.network_output_path, len(sampled_racks),  num_cells)
                    
                    except Exception as e:
                        print(e)
                        print("unable to write results to network")
                    icp_workflow = None
                    