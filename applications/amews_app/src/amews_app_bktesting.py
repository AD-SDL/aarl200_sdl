import datetime
import json
from madsci.common.types.workflow_types import WorkflowDefinition
from madsci.common.types.step_types import StepDefinition
from madsci.client.experiment_application import ExperimentApplication, ExperimentDesign
from pathlib import Path
from utils.generate_protocol import generate_protocol
from utils.assign_timestamps import assign_timestamps
from utils.create_sample_file import create_sample_file

class AMEWSApp(ExperimentApplication):
    """A demonstration and benchmarking experimental application: mixing colors autonomously."""
    url = "http://controlroom1.cse.anl.gov:8002/"
    workflow_directory = Path("../workflows").resolve()
    experiment_design = ExperimentDesign(experiment_name="AMEWS First Test")
    output_path = Path("/home/aarl/Documents/AMEWS_output")

    

if __name__ == "__main__":
    experiment_app = AMEWSApp()
    current_time = datetime.datetime.now()
    with experiment_app.manage_experiment(
        run_name=f"AMEWS Experiment Run {current_time}",
        run_description=f"Run for AMEWS experiment, started at ~{current_time}",
    ):
        num_cell_plates = 1
        input_volumes = []
        input_chemicals = []
        tube_rack = 1
        total_racks = 2
        latest_input_rack = None
        sampled_racks = []
        measured_racks = []
        starting_cell_plate = 0
        starting_cell_well = 0
        bk_workflow = None
        icp_workflow = None
        first_run = True
        input_locations = ["supply_slot_1", "supply_slot_2"]
        while len(measured_racks) < total_racks:
         if bk_workflow and bk_workflow.status.completed:
            #experiment_app.workcell_client.submit_workflow(experiment_app.workflow_directory / "open_door.workflow.yaml")
            # experiment_app.workcell_client.submit_workflow(
            #     experiment_app.workflow_directory / "transfer_from_bk.workflow.yaml", parameters={"target_location": input_locations[tube_rack - 1]}
            # )
            #experiment_app.workcell_client.submit_workflow(experiment_app.workflow_directory / "close_door.workflow.yaml")
            completed_protocol = experiment_app.data_client.get_datapoint_value(
               bk_workflow.get_datapoint_id_by_label("protocol")
               )
            sampled_racks.append(assign_timestamps(completed_protocol, latest_input_rack))
            json.dump(sampled_racks[-1].model_dump(), experiment_app.output_path / f"tube_rack_{tube_rack}_info.json", indent=4)
            tube_rack += 1
            bk_workflow = None
            break

         if bk_workflow is None:
            protocol, latest_input_rack, last_cell_plate, last_cell_well = generate_protocol(first_run=first_run, 
                                                                                     num_cell_plates=num_cell_plates, 
                                                                                     cell_volumes=input_volumes, 
                                                                                     starting_cell_plate=starting_cell_plate, 
                                                                                     starting_cell_well=starting_cell_well)
            protocol_path = experiment_app.output_path / "protocols" / f"tube_rack_{tube_rack}.json"
            with open(protocol_path, "w") as f:
                json.dump(protocol.model_dump(), f)
            first_run = False
            # experiment_app.workcell_client.submit_workflow(experiment_app.workflow_directory / "open_door.workflow.yaml")
            # experiment_app.workcell_client.submit_workflow(
            #     experiment_app.workflow_directory / "transfer_to_bk.workflow.yaml", parameters={"source_location": input_locations[tube_rack - 1]}
            # )
            # experiment_app.workcell_client.submit_workflow(experiment_app.workflow_directory / "close_door.workflow.yaml")
            bk_workflow = experiment_app.workcell_client.submit_workflow(
                      experiment_app.workflow_directory / "run_bk.workflow.yaml", parameters={"protocol": str(protocol_path)}
                  )
            
            # if icp_workflow is None and len(sampled_racks) > len(measured_racks):
            #     experiment_app.workcell_client.submit_workflow(experiment_app.workflow_directory / "transfer_to_icp.yaml", payload={"source_location": input_locations[len(measured_racks)]})
            #     sample_info_file_path = create_sample_file(sampled_racks[len(measured_racks)])
            #     dataset_name = experiment_app.experiment.experiment_id + "_tube_rack_" + str(len(measured_racks) + 1)
            #     icp_workflow = experiment_app.workcell_client.submit_workflow(
            #         experiment_app.workflow_directory / "run_icp.workflow.yaml", parameters={"dataset_name": dataset_name, "sample_info_file": str(sample_info_file_path)}
            #     )

               
            # if icp_workflow and icp_workflow.status.completed:
            #     experiment_app.workcell_client.submit_workflow(
            #         experiment_app.workflow_directory / "transfer_from_icp.workflow.yaml", parameters={"target_location": input_locations[len(measured_racks)]}
            #     )
            #     experiment_app.data_client.save_datapoint_value(
            #         icp_workflow.get_datapoint_id_by_label("result"), experiment_app.output_filepath / "results" / f"tube_rack_{len(measured_racks) + 1}_results.csv")
                
            #     measured_racks.append(sampled_racks[len(measured_racks)])