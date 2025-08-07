import datetime
import json
import math
import shutil
from madsci.common.types.workflow_types import WorkflowDefinition
from madsci.common.types.step_types import StepDefinition
from madsci.client.experiment_application import ExperimentApplication, ExperimentDesign
from madsci.client.node.rest_node_client import RestNodeClient
from madsci.common.types.datapoint_types import DataPoint
from pathlib import Path
from utils.generate_protocol import generate_protocol
from utils.assign_timestamps import assign_timestamps
from utils.create_sample_file import create_sample_file
from utils.AMEWS_types import AMEWS_tube
from utils.big_kahuna_protocol_types import BigKahunaProtocol
from utils.parse_input_csv import parse_input_csv
from data_processing.current_data_processing import run_analysis
from data_processing.icp_processing import convert_report
from data_processing.unpack_container import unpack_self_container
from utils.create_sample_file_fixed_protocol import write_sampleinfo

class AMEWSApp(ExperimentApplication):
    """A demonstration and benchmarking experimental application: mixing colors autonomously."""
    url = "http://controlroom1.cse.anl.gov:8002/"
    workflow_directory = Path("../workflows").resolve()
    experiment_design = ExperimentDesign(experiment_name="AMEWS Cell Tests")
    network_output_path = Path("/run/user/1000/gvfs/smb-share:server=sheldon.cse.anl.gov,share=aarl200/RESULTS/").resolve()
    network_input_path = Path("/run/user/1000/gvfs/smb-share:server=sheldon.cse.anl.gov,share=aarl200/INPUTS").resolve()
    output_path = Path("/home/aarl/Documents/AMEWS_output").resolve()
    def get_latest_datapoint_value_by_label(self, label: str):
        """Get the latest datapoint by label."""
        datapoints = self.data_client.query_datapoints(lambda dp: dp.label == label)
        if not datapoints:
            return None
        datapoint =  sorted(datapoints.values(), key=lambda x: x.data_timestamp, reverse=True)[0]
        return datapoint.value
    def find_file_datapoint(self, datapoints: list[DataPoint], protocol_id: int, key_string: str, suffix=".xml"):
        """Find the file associated with a protocol."""
        protocol_id = str(protocol_id)
        for dp in datapoints.values():
            if dp.data_type == "file" and key_string+"_" + protocol_id in dp.path:
                output_path = self.output_path / (key_string + "_" + protocol_id + ".xml")
                self.data_client.save_datapoint_value(dp.datapoint_id, output_path)
                try:
                    self.data_client.save_datapoint_value(dp.datapoint_id, self.network_output_path / (key_string + "_" + protocol_id + ".xml"))
                except Exception as e:
                    print(f"Unable to write to network drive: {e}")
        return str(output_path)
if __name__ == "__main__":
    experiment_app = AMEWSApp()
    current_time = datetime.datetime.now()
    with experiment_app.manage_experiment(
        run_name=f"AMEWS Experiment Run {current_time}",
        run_description=f"Run for AMEWS experiment, started at ~{current_time}",
    ):
        experiment_app.output_path = experiment_app.output_path / experiment_app.experiment.experiment_id
        # experiment_app.output_path.mkdir(parents=True, exist_ok=True)
        # (experiment_app.output_path / "protocols").mkdir(parents=True, exist_ok=True)
        # (experiment_app.output_path / "results").mkdir(parents=True, exist_ok=True)
        # experiment_app.network_output_path.mkdir(parents=True, exist_ok=True)
        # (experiment_app.network_output_path / "protocols").mkdir(parents=True, exist_ok=True)
        # (experiment_app.network_output_path / "results").mkdir(parents=True, exist_ok=True)
        labjack_client = RestNodeClient("http://146.139.45.9:2001")

        
        containers = []
        sampled_racks = []
        measured_racks = []
        bk_workflow = None
        icp_workflow = None
        first_run = True
        input_locations = ["supply_slot_1", "supply_slot_2", "supply_slot_3", "supply_slot_4", "supply_slot_5"]
        setup_parameters = {}
        experiment_label = "Z:/RESULTS/BK_run24_20250806_200622" 
        experiment_folder = experiment_label.replace("Z:/RESULTS/", "")
        experiment_app.network_output_path = experiment_app.network_output_path / experiment_folder
        print(experiment_app.network_output_path)
        datapoints = experiment_app.data_client.query_datapoints({"label": experiment_label})
        sequence_logs = [datapoint.value for datapoint in datapoints.values() if datapoint.data_type == "data_value" and "AS_sequence_log" in datapoint.value]
        sequence_log  = sequence_logs[0]
        
        for log in sequence_logs:
            if len(log["AS_sequence_log"]) >= len(sequence_log["AS_sequence_log"]):
                sequence_log = log
        print(sequence_log)
        num_tube_racks = 0
        containers = []
        rack_ids = []
        for step in sequence_log["AS_sequence_log"]:
            if "load" in step["category"]:
                setup_parameters["load_protocol"] = step["ID"]
                setup_parameters["load_prompts_file"] = experiment_app.find_file_datapoint(datapoints, step["ID"], "prompts")
                setup_parameters["load_chem_file"] = experiment_app.find_file_datapoint(datapoints, step["ID"], "chem")
            if "blank" in step["category"]:
                setup_parameters["blank_protocol"] = step["ID"]
                setup_parameters["blank_prompts_file"] = experiment_app.find_file_datapoint(datapoints, step["ID"], "prompts")
                setup_parameters["blank_chem_file"] = experiment_app.find_file_datapoint(datapoints, step["ID"], "chem")
            if "fill" in step["category"]:
                setup_parameters["fill_protocol"] = step["ID"]
                setup_parameters["fill_prompts_file"] = experiment_app.find_file_datapoint(datapoints, step["ID"], "prompts")
                setup_parameters["fill_chem_file"] = experiment_app.find_file_datapoint(datapoints, step["ID"], "chem")
            if "rack1" in step["category"]:
                setup_parameters["sample_protocol"] = step["ID"]
                setup_parameters["sample_prompts_file"] = experiment_app.find_file_datapoint(datapoints, step["ID"], "prompts")
                setup_parameters["sample_chem_file"] = experiment_app.find_file_datapoint(datapoints, step["ID"], "chem")
            if "rack" in step["category"]:
                num_tube_racks += 1
                containers.append(step["container"])
                rack_ids.append(step["ID"])
        final_racks = []
        for container in containers:
            container_path = experiment_app.find_file_datapoint(datapoints, container, "Active_", suffix=".json")
            with open(container_path, "r") as f:
                rack = json.load(f)
                final_racks.append(rack)
                
        
        while len(measured_racks) < num_tube_racks:
            bk_workflow = experiment_app.workcell_client.query_workflow(bk_workflow.workflow_id) if bk_workflow else None
            icp_workflow = experiment_app.workcell_client.query_workflow(icp_workflow.workflow_id) if icp_workflow else None
            
            if bk_workflow and bk_workflow.status.completed:
                
                experiment_app.workcell_client.submit_workflow(experiment_app.workflow_directory / "open_door.workflow.yaml")
                experiment_app.workcell_client.submit_workflow(
                   experiment_app.workflow_directory / "transfer_from_bk.workflow.yaml", parameters={"target_location": input_locations[len(sampled_racks)]}
                )
                experiment_app.workcell_client.submit_workflow(experiment_app.workflow_directory / "close_door.workflow.yaml")
                if len(bk_workflow.steps) > 1:
                    datapoint_id = bk_workflow.get_datapoint_id_by_label("sample_log")
                    datapoint = experiment_app.data_client.get_datapoint(datapoint_id)
                else:
                    datapoint_id = bk_workflow.get_datapoint_id_by_label("log_file")
                    datapoint = experiment_app.data_client.get_datapoint(datapoint_id)

                experiment_app.data_client.save_datapoint_value(
                    datapoint_id, 
                    experiment_app.output_path / datapoint.path.name
                )
                try:
                    
                    experiment_app.data_client.save_datapoint_value(
                    datapoint_id, 
                    experiment_app.networl_output_path / datapoint.path.name
                    )
                except Exception as e:
                    print(f"Unable to write protocol to network drive: {e}")
                sampled_racks.append(final_racks[len(sampled_racks)])
               
                bk_workflow = None


            if bk_workflow is None and len(sampled_racks) < num_tube_racks:
                
                
               
                experiment_app.workcell_client.submit_workflow(experiment_app.workflow_directory / "open_door.workflow.yaml")
                experiment_app.workcell_client.submit_workflow(
                    experiment_app.workflow_directory / "transfer_to_bk.workflow.yaml", parameters={"source_location": input_locations[len(sampled_racks)]}
                )
                experiment_app.workcell_client.submit_workflow(experiment_app.workflow_directory / "close_door.workflow.yaml")
                if first_run:
                    first_run = False
                    bk_workflow = experiment_app.workcell_client.submit_workflow(
                        experiment_app.workflow_directory / "run_bk_setup.workflow.yaml", parameters=setup_parameters,
                        await_completion = False
                    )
                else:
                    library_id = rack_ids[len(sampled_racks)]
                    chem_file = experiment_app.find_file_datapoint(datapoints, library_id, "chem")
                    prompts_file = experiment_app.find_file_datapoint(datapoints, library_id, "prompts")
                    bk_workflow = experiment_app.workcell_client.submit_workflow(
                        experiment_app.workflow_directory / "run_bk_fp.workflow.yaml", parameters={"library_id": library_id, "chem_file": chem_file, "prompts_file": prompts_file, "dataset_name": f"tube_rack_{len(sampled_racks) + 1}_stamped" }, await_completion=False
                    )
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
                        icp_workflow = experiment_app.workcell_client.submit_workflow(
                        experiment_app.workflow_directory / "run_icp.workflow.yaml", parameters={"dataset_name": last_dataset, "sample_info_file": str(sample_info_file_path)}, await_completion=False)

                    
            if icp_workflow and icp_workflow.status.completed:
                    experiment_app.workcell_client.submit_workflow(
                            experiment_app.workflow_directory / "transfer_from_icp.workflow.yaml", parameters={"target_location": input_locations[len(measured_racks)]}
                        )
                    measured_racks.append(sampled_racks[len(measured_racks)])
                    experiment_app.data_client.save_datapoint_value(
                            icp_workflow.get_datapoint_id_by_label("result_file"), experiment_app.network_output_path / ("run_"+code+".csv"))
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
                    