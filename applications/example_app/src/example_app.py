#!/usr/bin/env python3
"""Example experiment application that uses the WEI client to run a workflow."""

from pathlib import Path

from wei import ExperimentClient
from wei.types.experiment_types import ExperimentDesign


def main() -> None:
    """Runs an example WEI workflow"""
    # This defines the Experiment object that will communicate with the WEI server
    experiment = ExperimentDesign(
        experiment_name="RAPID200_Demo",
        experiment_description="Pick and place example"
    )
    exp = ExperimentClient(
        server_host="localhost",
        server_port="8000",
        experiment=experiment
    )

    pickup_ur_locations = ["ur_RAPID200.supply_rack_icp1", "ur_RAPID200.supply_rack_icp2", "ur_RAPID200.supply_rack_icp3"]
    pickup_rail_locations = [175, 211, 247]
    trash_ur_locations = ["ur_RAPID200.trash_rack_icp1", "ur_RAPID200.trash_rack_icp2", "ur_RAPID200.trash_rack_icp3"]
    trash_rail_locations = [282, 318, 353]
    wf_dir = (Path(__file__).parent.parent / "workflows").resolve()


    wf_run = exp.start_run(
            workflow=wf_dir / "home_rail.workflow.yaml",
        )
    while True:
        for i in range(3):
            wf_run = exp.start_run(
                workflow=wf_dir / "pick_tube_rack.workflow.yaml",
                payload={
                    "travel_safe_joints": "ur_RAPID200.travel_container_joints",
                     "rail_position": pickup_rail_locations[i],
                     "arm_position": pickup_ur_locations[i],
                     "arm_safe_joints": "ur_RAPID200.supply_station_safe_joints"
                }
            )
        # 
            wf_run = exp.start_run(
                workflow=wf_dir / "place_tube_rack.workflow.yaml",
                payload={
                    "travel_safe_joints": "ur_RAPID200.travel_container_joints",
                    "rail_position": 650,
                    "arm_position": "ur_RAPID200.pal_robot_1",
                    "arm_safe_joints": "ur_RAPID200.pal_safe_joints",
                }
            )
            wf_run = exp.start_run(
                workflow=wf_dir / "pick_tube_rack.workflow.yaml",
                payload={
                    "travel_safe_joints": "ur_RAPID200.travel_container_joints",
                    "rail_position": 650,
                    "arm_position": "ur_RAPID200.pal_robot_1",
                    "arm_safe_joints": "ur_RAPID200.pal_safe_joints",
                }
            )

            wf_run = exp.start_run(
                workflow=wf_dir / "place_tube_rack.workflow.yaml",
                payload={
                    "travel_safe_joints": "ur_RAPID200.travel_container_joints",
                    "rail_position": 150,
                    "arm_position": "ur_RAPID200.icp",
                    "arm_safe_joints": "ur_RAPID200.icp_safe_joints"
                }
            )

            wf_run = exp.start_run(
                workflow=wf_dir / "pick_tube_rack.workflow.yaml",
                payload={
                    "travel_safe_joints": "ur_RAPID200.travel_container_joints",
                    "rail_position": 150,
                    "arm_position": "ur_RAPID200.icp",
                    "arm_safe_joints": "ur_RAPID200.icp_safe_joints"
                }
            )

            wf_run = exp.start_run(
                workflow=wf_dir / "place_tube_rack.workflow.yaml",
                payload={
                    "travel_safe_joints": "ur_RAPID200.travel_container_joints",
                    "rail_position": trash_rail_locations[i],
                    "arm_position": trash_ur_locations[i],
                    "arm_safe_joints": "ur_RAPID200.supply_station_safe_joints"
                }
            )
        break


if __name__ == "__main__":
    main()
