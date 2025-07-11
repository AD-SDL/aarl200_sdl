import datetime
import json
import math
import shutil
from madsci.common.types.workflow_types import WorkflowDefinition
from madsci.common.types.step_types import StepDefinition
from madsci.client.experiment_application import ExperimentApplication, ExperimentDesign
from pathlib import Path
from utils.generate_protocol import generate_protocol
from utils.assign_timestamps import assign_timestamps
from utils.create_sample_file import create_sample_file
from utils.AMEWS_types import AMEWS_tube
from utils.big_kahuna_protocol_types import BigKahunaProtocol
from utils.parse_input_csv import parse_input_csv
from data_processing.icp_processing import convert_report

class AMEWSApp(ExperimentApplication):
    """A demonstration and benchmarking experimental application: mixing colors autonomously."""
    url = "http://controlroom1.cse.anl.gov:8002/"
    workflow_directory = Path("../workflows").resolve()
    experiment_design = ExperimentDesign(experiment_name="AMEWS Cell Tests")
    network_output_path = Path("/run/user/1000/gvfs/smb-share:server=sheldon.cse.anl.gov,share=aarl200/RESULTS/AMEWS_Output").resolve()
    network_input_path = Path("/run/user/1000/gvfs/smb-share:server=sheldon.cse.anl.gov,share=aarl200/INPUTS").resolve()
    output_path = Path("/home/aarl/Documents/AMEWS_output").resolve()
    

if __name__ == "__main__":
    experiment_app = AMEWSApp()
    current_time = datetime.datetime.now()
    with experiment_app.manage_experiment(
        run_name=f"AMEWS Experiment Run {current_time}",
        run_description=f"Run for AMEWS experiment, started at ~{current_time}",
    ):
        experiment_app.output_path = experiment_app.output_path / experiment_app.experiment.experiment_id
        experiment_app.network_output_path = experiment_app.network_output_path / experiment_app.experiment.experiment_id
        experiment_app.output_path.mkdir(parents=True, exist_ok=True)
        (experiment_app.output_path / "protocols").mkdir(parents=True, exist_ok=True)
        (experiment_app.output_path / "results").mkdir(parents=True, exist_ok=True)
        experiment_app.network_output_path.mkdir(parents=True, exist_ok=True)
        (experiment_app.network_output_path / "protocols").mkdir(parents=True, exist_ok=True)
        (experiment_app.network_output_path / "results").mkdir(parents=True, exist_ok=True)
        "Input Variables"
        num_cells = 24
        sampling_rounds = 6
        sampling_delay_mins = 180
        input_variables_path = experiment_app.network_input_path / "input_variables.json"
        with open(input_variables_path, "r") as f:
            input_variables = json.load(f)
        num_cells = input_variables.get("num_cells", num_cells)
        sampling_rounds = input_variables.get("sampling_rounds", sampling_rounds)
        sampling_delay_mins = input_variables.get("sampling_delay_mins", sampling_delay_mins)
        csv_path = experiment_app.network_input_path / "AMEWS_Input.csv"
        with open(csv_path, "r") as f:
            with open(experiment_app.output_path / "AMEWS_Input.csv", "w") as out_f:
                out_f.write(f.read())
        try:
            with open(csv_path, "r") as f:
                with open(experiment_app.network_output_path / "AMEWS_Input.csv", "w") as out_f:
                    out_f.write(f.read())
        except Exception as e: 
                print("unable to write input csv to network")
        input_chemicals, input_volumes = parse_input_csv(csv_path)
        
        json.dump(input_variables, open(experiment_app.output_path / "input_variables.json", "w"), indent=4)
        json.dump(input_volumes, open(experiment_app.output_path / "input_volumes.json", "w"), indent=4)
        try:
            json.dump(input_variables, open(experiment_app.network_output_path / "input_variables.json", "w"), indent=4)
            json.dump(input_volumes, open(experiment_app.network_output_path / "input_volumes.json", "w"), indent=4)
        except Exception as e:
             print("unable to write to network")
        total_samples = num_cells*sampling_rounds 
        aliquots = [25]
        num_tubes = 90
        total_racks = math.ceil((total_samples + (len(aliquots) + 1)* num_cells) / num_tubes)
        latest_input_rack = None
        
        sampled_racks = []
        measured_racks = []
        starting_cell_index = 0
        current_samples = 0
        bk_workflow = None
        icp_workflow = None
        first_run = True
        
        input_locations = ["supply_slot_1", "supply_slot_2", "supply_slot_3", "supply_slot_4", "supply_slot_5"]
        while len(measured_racks) < total_racks:
            bk_workflow = experiment_app.workcell_client.query_workflow(bk_workflow.workflow_id) if bk_workflow else None
            icp_workflow = experiment_app.workcell_client.query_workflow(icp_workflow.workflow_id) if icp_workflow else None
            
            if bk_workflow and bk_workflow.status.completed:
                
                experiment_app.workcell_client.submit_workflow(experiment_app.workflow_directory / "open_door.workflow.yaml")
                experiment_app.workcell_client.submit_workflow(
                   experiment_app.workflow_directory / "transfer_from_bk.workflow.yaml", parameters={"target_location": input_locations[len(sampled_racks)]}
                )
                experiment_app.workcell_client.submit_workflow(experiment_app.workflow_directory / "close_door.workflow.yaml")
                protocol_file_path = experiment_app.output_path / "protocols" / f"tube_rack_{len(sampled_racks) + 1}_stamped.json"
                completed_protocol = experiment_app.data_client.save_datapoint_value(
                bk_workflow.get_datapoint_id_by_label("protocol"), protocol_file_path
                )
                with open(protocol_file_path, "r") as f:
                    timestamped_protocol = BigKahunaProtocol(**json.load(f))

                sampled_racks.append(assign_timestamps(timestamped_protocol, latest_input_rack))

                with open(experiment_app.output_path / f"tube_rack_{len(sampled_racks)}_info.json", "w") as f:
                    json.dump({key: value.model_dump() for key, value in sampled_racks[-1].items()}, f, indent=4)
                try:
                    with open(experiment_app.network_output_path / f"tube_rack_{len(sampled_racks)}_info.json", "w") as f:
                        json.dump({key: value.model_dump() for key, value in sampled_racks[-1].items()}, f, indent=4)
                except Exception as e:
                    print("unable to write to network")
                bk_workflow = None
            
        
            if bk_workflow is None and len(sampled_racks) < total_racks:
                
                protocol, latest_input_rack, starting_cell_index, current_samples = generate_protocol(first_run=first_run, 
                                                                                        num_cells=num_cells, 
                                                                                        input_chemicals=input_chemicals,
                                                                                        cell_volumes=input_volumes, 
                                                                                        starting_cell=starting_cell_index,
                                                                                            current_samples=current_samples,
                                                                                            total_samples=total_samples,
                                                                                            aliquots=aliquots,
                                                                                            sampling_delay = sampling_delay_mins
                                                                                        )
                protocol_path = experiment_app.output_path / "protocols" / f"tube_rack_{len(sampled_racks) + 1}.json"
                with open(protocol_path, "w") as f:
                    json.dump(protocol.model_dump(), f)
                try:
                     network_protocol_path = experiment_app.network_output_path / "protocols" / f"tube_rack_{len(sampled_racks) + 1}.json"
                     with open(network_protocol_path, "w") as f:
                        json.dump(protocol.model_dump(), f)
                except Exception as e:
                    print("unable to write protocol to network")
                first_run = False
                experiment_app.workcell_client.submit_workflow(experiment_app.workflow_directory / "open_door.workflow.yaml")
                experiment_app.workcell_client.submit_workflow(
                    experiment_app.workflow_directory / "transfer_to_bk.workflow.yaml", parameters={"source_location": input_locations[len(sampled_racks)]}
                )
                experiment_app.workcell_client.submit_workflow(experiment_app.workflow_directory / "close_door.workflow.yaml")
                bk_workflow = experiment_app.workcell_client.submit_workflow(
                        experiment_app.workflow_directory / "run_bk.workflow.yaml", parameters={"protocol": str(protocol_path)},
                        await_completion = False
                    )
                
            if icp_workflow is None and len(sampled_racks) > len(measured_racks):
                
                    stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                    dataset_name = stamp + "_r" + str(len(measured_racks)+1)
                    sample_info_file_path = create_sample_file(sampled_racks[len(measured_racks)], len(measured_racks) + 1,  experiment_app.output_path, "mina_hts_2", dataset_name, post_rinse=True, calibrate=True)
                    experiment_app.workcell_client.submit_workflow(
                        experiment_app.workflow_directory / "transfer_to_icp.workflow.yaml", parameters={"source_location": input_locations[len(measured_racks)]}
                    )
                    icp_workflow = experiment_app.workcell_client.submit_workflow(
                    experiment_app.workflow_directory / "run_icp.workflow.yaml", parameters={"dataset_name": dataset_name, "sample_info_file": str(sample_info_file_path)}, await_completion=False)

                
            if icp_workflow and icp_workflow.status.completed:
                    experiment_app.workcell_client.submit_workflow(
                            experiment_app.workflow_directory / "transfer_from_icp.workflow.yaml", parameters={"target_location": input_locations[len(measured_racks)]}
                        )
                    measured_racks.append(sampled_racks[len(measured_racks)])
                    experiment_app.data_client.save_datapoint_value(
                        icp_workflow.get_datapoint_id_by_label("result_file"), experiment_app.output_path / "results" / f"tube_rack_{len(measured_racks)}_results.csv")
                    
                    try:
                        convert_report(str(experiment_app.output_path / "results" / f"tube_rack_{len(measured_racks)}_results.csv"))
                        experiment_app.data_client.save_datapoint_value(
                            icp_workflow.get_datapoint_id_by_label("result_file"), experiment_app.network_output_path / "results" / f"tube_rack_{len(measured_racks)}_results.csv")
                        convert_report(str(experiment_app.network_output_path / "results" / f"tube_rack_{len(measured_racks)}_results.csv"))
                    except Exception as e:
                        print("unable to write results to network")
                    icp_workflow = None
                    