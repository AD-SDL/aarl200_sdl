import datetime
import json
from madsci.common.types.workflow_types import WorkflowDefinition
from madsci.common.types.step_types import StepDefinition
from madsci.client.experiment_application import ExperimentApplication, ExperimentDesign
from pathlib import Path
from generate_blank import generate_blank_protocol
import time


class AMEWSApp(ExperimentApplication):
    """A demonstration and benchmarking experimental application: mixing colors autonomously."""
    url = "http://controlroom1.cse.anl.gov:8002/"
    workflow_directory = Path("../workflows").resolve()
    experiment_design = ExperimentDesign(experiment_name="AMEWS First Test")

    

if __name__ == "__main__":
    experiment_app = AMEWSApp()
    current_time = datetime.datetime.now()
    with experiment_app.manage_experiment(
        run_name=f"AMEWS Experiment Run {current_time}",
        run_description=f"Run for AMEWS experiment, started at ~{current_time}",
    ):
        # open_door = experiment_app.workcell_client.submit_workflow(
        #         experiment_app.workflow_directory / "open_door.workflow.yaml"
        #     )
        # transfer_1 = experiment_app.workcell_client.submit_workflow(    
        #     experiment_app.workflow_directory / "transfer_to_bk.workflow.yaml", parameters={"source_location": "supply_slot_1"}
        #     )
        # close_door = experiment_app.workcell_client.submit_workflow(
        #         experiment_app.workflow_directory / "close_door.workflow.yaml"
        #     )
        # blank_workflow = experiment_app.workcell_client.submit_workflow(
        #         experiment_app.workflow_directory / "blank.workflow.yaml"
        #     )
        # info_id = blank_workflow.get_datapoint_id_by_label("info")
        # info = experiment_app.data_client.get_datapoint_value(info_id)
        # fill_workflow = experiment_app.workcell_client.submit_workflow(
        #         experiment_app.workflow_directory / "fill.workflow.yaml", parameters={"info": info}
        #     )
        # info_id = fill_workflow.get_datapoint_id_by_label("info")
        # info = experiment_app.data_client.get_datapoint_value(info_id)
        # time.sleep(600)
        # calibrate_workflow = experiment_app.workcell_client.submit_workflow(
        #         experiment_app.workflow_directory / "calibrate.workflow.yaml", parameters={"info": info}
        #     )
        # info_id = calibrate_workflow.get_datapoint_id_by_label("info")
        # info = experiment_app.data_client.get_datapoint_value(info_id)
        # sample_workflow = experiment_app.workcell_client.submit_workflow(
        #         experiment_app.workflow_directory / "sample.workflow.yaml", parameters={"info": info}
        #     )
        # info_id = sample_workflow.get_datapoint_id_by_label("info")
        # info = experiment_app.data_client.get_datapoint_value(info_id)

        
        # open_door = experiment_app.workcell_client.submit_workflow(
        #         experiment_app.workflow_directory / "open_door.workflow.yaml"
        #     )
        # transfer_2 = experiment_app.workcell_client.submit_workflow(    
        #     experiment_app.workflow_directory / "transfer_from_bk.workflow.yaml", parameters={"target_location": "supply_slot_1"}
        #     )
        # close_door = experiment_app.workcell_client.submit_workflow(
        #         experiment_app.workflow_directory / "close_door.workflow.yaml"
        #     )
        # transfer_3 = experiment_app.workcell_client.submit_workflow(    
        #     experiment_app.workflow_directory / "transfer_to_icp.workflow.yaml", parameters={"source_location": "supply_slot_1"}
        #     )
        icp_workflow = experiment_app.workcell_client.submit_workflow(
                      experiment_app.workflow_directory / "run_icp.workflow.yaml", parameters={"container": info["last_container"]}
                  )
        # transfer_4 = experiment_app.workcell_client.submit_workflow(    
        #     experiment_app.workflow_directory / "transfer_from_icp.workflow.yaml", parameters={"target_location": "supply_slot_1"}
        #     )         

       
        # protocol = generate_blank_protocol()
        # with open("/home/aarl/Dropbox/Instruments cloud/Robotics/Unchained BK/AS Scripts/API Scripts/BK done/1486/TestContainer.json") as f:
        #     container = json.load(f)
        # icp_workflow = experiment_app.workcell_client.submit_workflow(
        #              experiment_app.workflow_directory / "run_icp.workflow.yaml", parameters={"container": container}
        #          )
        # icp_workflow = experiment_app.workcell_client.submit_workflow(
        #             experiment_app.workflow_directory / "blank_good.workflow.yaml", parameters={"protocol": protocol.model_dump()}
        #         )
        # print(icp_workflow)