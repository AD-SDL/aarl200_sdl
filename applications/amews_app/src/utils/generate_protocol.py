import math
import string
from utils.big_kahuna_protocol_types import BigKahunaDelay, BigKahunaProtocol, BigKahunaDispense, BigKahunaPlate, BigKahunaChemical, BigKahunaParameter, BigKahunaStir, BigKahunaTransfer
from utils.AMEWS_types import AMEWS_tube
def generate_protocol(first_run: bool, num_cell_plates: int = 6, input_chemicals = [], cell_volumes = [], starting_cell_plate = 0, starting_cell_well = 0): 
    """
    Generates a protocol for the AMEWS application.

    Args:
        first_run (bool): Indicates if this is the first tube rack to run.

    Returns:
        None
    """
    tube_rack_info = {}
    full_tube_volume = 2500
    sample_volume = 250
    sampling_delay = 120
    if first_run:
        name = "AMEWS 24 Cells Initialize and Sample"
    else:
        name = "AMEWS 24 Cells Sample"
    if input_chemicals == []:
        input_chemicals = ["mixture_1", "mixture_2", "mixture_3", "mixture_4", "mixture_5", "mixture_6", "mixture_7", "mixture_8"]

    cell_plate_locations = [
            "Deck 12-13 Heat-Cool-Stir 1",
            "Deck 12-13 Heat-Stir 2",
            "Deck 12-13 Heat-Stir 3",
            "Deck 14-15 Heat-Stir 1",
            "Deck 14-15 Heat-Stir 2",
            "Deck 14-15 Heat-Stir 3",
        ]
    output_wells = ["A1", "A2", "B1", "B2"]
    input_wells = ["C1", "C2", "D1", "D2"]
    aliquots = [25]
    tube_rack_wells = []
    for i in range(0, 6):
        for j in range(1, 16):
            tube_rack_wells.append(string.ascii_uppercase[i] + str(j))

    protocol = BigKahunaProtocol(
                                name=name,
                                units="ul",
                                parameters=[
                                     BigKahunaParameter(name="Delay", type="Time", unit="min"),
                                     BigKahunaParameter(name="StirRate", type="Stir Rate", unit="rpm"),
                                     BigKahunaParameter(name="Pause", type="Text", unit="")

                                 ],
                                 plates={
                                     "ICP_rack": BigKahunaPlate(name="ICP_rack", type="Rack 6x15 ICP robotic", rows=6, columns=15, deck_position="Deck 16-17 Waste 1")
                                 },
                                 chemicals=[
                                     BigKahunaChemical(name="solvent"),
                                     BigKahunaChemical(name="standard")
                                 ]
                                 )
    protocol.actions.append(
         BigKahunaStir(target_plate="ICP_rack", rate=500)
    )
    for i in range(num_cell_plates):
        plate_name = f"cell_plate_{i+1}"
        protocol.plates[plate_name] = BigKahunaPlate(name=plate_name, type="Rack 4x2 Mina H-cell", rows=4, columns=2, deck_position=cell_plate_locations[i])
        protocol.actions.append(
         BigKahunaStir(target_plate=plate_name, rate=500)
     )
        for j in range(len(output_wells)):
            protocol.actions.append(
                BigKahunaDispense(source_chemical="standard", target_plate=plate_name, target_well=output_wells[j], volume=10000, tags=["SkipMap"])
            )
            protocol.actions.append(
                BigKahunaDispense(source_chemical="standard", target_plate=plate_name, target_well=input_wells[j], volume=10000, tags=["SkipMap"])
            )
    well_index = 0
    if first_run:
        for i in range(len(input_chemicals)):
            row = 1 if i < 3 else 2
            column = i + 1 if i < 3 else i - 2
            protocol.chemicals.append(
                BigKahunaChemical(name=input_chemicals[i], source_plate="source_plate", deck_position="Deck 10-11 Position 2", row=row, column=column, volume=10000)
            )
        protocol.plates["source_plate"] =  BigKahunaPlate(name="source_plate", type="Rack 2x4 20mL Vial", rows=2, columns=4, deck_position="Deck 10-11 Position 2", source=True)
        
        """Blank Samples"""
        for i in range(0, num_cell_plates):
            for j in range(len(output_wells)):
                    target_well = tube_rack_wells[well_index]
                    cell_plate = f"cell_plate_{i+1}"
                    source_well = output_wells[j]
                    # protocol.actions.append(
                    #     BigKahunaDispense(source_chemical=input_chemicals[j], target_plate="ICP_rack", target_well=target_well, volume=full_tube_volume-sample_volume, tags=["Chaser", "Backsolvent"])
                    # )
                    protocol.actions.append(
                        BigKahunaTransfer(source_plate=cell_plate, target_plate="ICP_rack", source_well=source_well, target_well=target_well, volume=sample_volume, tags=["SyringePump","SingleTip"])
                    )
                    # protocol.actions.append(
                    #     BigKahunaDispense(source_chemical="solvent", target_plate=cell_plate, target_well=source_well, volume=sample_volume, tags=["SyringePump","SingleTip", "Backsolvent"])
                    # )
                    tube_rack_info[target_well] = AMEWS_tube(well=target_well, type="Blank", sampled_plate=cell_plate, sampled_well=source_well)
                    well_index += 1
        """Fill"""
        for i in range(len(cell_volumes)):
            plate = f"cell_plate_{math.floor(i / 4)+1}"
            well = input_wells[i % 4]
            for chemical, volume in cell_volumes[i].items():
                protocol.actions.append(
                    BigKahunaDispense(source_chemical=chemical, target_plate=plate, target_well=well, volume=volume, tags=["SyringePump","SingleTip"])
                )
        """Calibrate"""
        for i in range(num_cell_plates):
            for j in range(len(input_wells)):
                for aliquot in aliquots:
                    target_well = tube_rack_wells[well_index]
                    source_well = input_wells[j]
                    cell_plate = f"cell_plate_{i+1}"
                    # protocol.actions.append(
                    #     BigKahunaDispense(source_chemical="solvent", target_plate="ICP_rack", target_well=target_well, volume=full_tube_volume-aliquot, tags=["Chaser", "Backsolvent"])
                    # )
                    protocol.actions.append(
                        BigKahunaTransfer(source_plate=cell_plate, target_plate="ICP_rack", source_well=source_well, target_well=target_well, volume=aliquot, tags=["SyringePump","SingleTip"])
                    )
                    # protocol.actions.append(
                    #     BigKahunaDispense(source_chemical="solvent", target_plate=cell_plate, target_well=source_well, volume=aliquot, tags=["SyringePump","SingleTip", "Backsolvent"])
                    # )
                    tube_rack_info[target_well] = AMEWS_tube(well=target_well, type="Calibrate", sampled_plate=cell_plate, sampled_well=source_well)
                    well_index += 1
    while well_index < 12: #len(tube_rack_wells):
        for i in range(starting_cell_plate, num_cell_plates):
            for j in range(starting_cell_well, len(output_wells)):
                if well_index >= len(tube_rack_wells):
                    break
                target_well = tube_rack_wells[well_index]
                source_well = output_wells[j]
                cell_plate = f"cell_plate_{i+1}"
                # protocol.actions.append(
                #     BigKahunaDispense(source_chemical="solvent", target_plate="ICP_rack", target_well=target_well, volume=full_tube_volume-sample_volume, tags=["Chaser", "Backsolvent"])
                # )
                protocol.actions.append(
                    BigKahunaTransfer(source_plate=cell_plate, target_plate="ICP_rack", source_well=source_well, target_well=target_well, volume=sample_volume, tags=["SyringePump","SingleTip"])
                )
                # protocol.actions.append(
                #     BigKahunaDispense(source_chemical="solvent", target_plate=cell_plate, target_well=source_well, volume=sample_volume, tags=["SyringePump","SingleTip", "Backsolvent"])
                # )
                
                tube_rack_info[target_well] = AMEWS_tube(well=target_well, type="Sample", sampled_plate=cell_plate, sampled_well=source_well)
                last_cell_well = j
                last_cell_plate = i
                well_index += 1
            starting_cell_well = 0
        starting_cell_plate = 0
        # protocol.actions.append(
        #             BigKahunaDelay(target_plate=cell_plate, delay=sampling_delay)
        #         )
    return protocol, tube_rack_info, last_cell_plate, last_cell_well




         