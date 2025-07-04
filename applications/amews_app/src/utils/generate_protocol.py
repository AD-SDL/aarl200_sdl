import math
import string
from utils.big_kahuna_protocol_types import BigKahunaDelay, BigKahunaProtocol, BigKahunaDispense, BigKahunaPlate, BigKahunaChemical, BigKahunaParameter, BigKahunaStir, BigKahunaTransfer
from utils.AMEWS_types import AMEWS_tube
def generate_protocol(first_run: bool, num_cells: int = 24, input_chemicals = [], cell_volumes = [], starting_cell=0, total_samples=1, current_samples=0, aliquots = [25], sampling_delay=5): 
    """
    Generates a protocol for the AMEWS application.

    Args:
        first_run (bool): Indicates if this is the first tube rack to run.

    Returns:
        None
    """
    num_cell_plates = math.ceil(num_cells / 4)
    tube_rack_info = {}
    reagent_fill_volume = 2000
    total_cell_volume = 17000
    full_tube_volume = 2500
    sample_volume = 250
    fill_delay = 10
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
            "Deck 14-15 Heat-Stir 3"
        ]
    input_wells = ["A1", "A2", "B1", "B2"]
    output_wells = ["C1", "C2", "D1", "D2"]
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
    for i in range(num_cell_plates):
        plate_name = f"cell_plate_{i+1}"
        protocol.plates[plate_name] = BigKahunaPlate(name=plate_name, type="Rack 4x2 Mina H-cell", rows=4, columns=2, deck_position=cell_plate_locations[i])
        protocol.actions.append(
         BigKahunaStir(target_plate=plate_name, rate=100)
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
            row = 1 if i < 4 else 2
            column = i + 1 if i < 4 else i-3
            protocol.chemicals.append(
                BigKahunaChemical(name=input_chemicals[i], source_plate="source_plate", deck_position="Deck 10-11 Position 2", row=row, column=column, volume=10000)
            )
        protocol.plates["source_plate"] =  BigKahunaPlate(name="source_plate", type="Rack 2x4 20mL Vial", rows=2, columns=4, deck_position="Deck 10-11 Position 2", source=True)
        
        """Blank Samples"""
        for i in range(0, num_cells):
                cell_plate = f"cell_plate_{math.floor(i / 4)+1}"
                source_well = output_wells[i % 4]
                target_well = tube_rack_wells[well_index]
                protocol.actions.append(
                    BigKahunaDispense(source_chemical="solvent", target_plate="ICP_rack", target_well=target_well, volume=full_tube_volume-sample_volume, tags=["Chaser", "Backsolvent"])
                )
                protocol.actions.append(
                BigKahunaTransfer(source_plate=cell_plate, target_plate="ICP_rack", source_well=source_well, target_well=target_well, volume=sample_volume, tags=["SyringePump","SingleTip"])
                    )
                protocol.actions.append(
                    BigKahunaDispense(source_chemical="solvent", target_plate=cell_plate, target_well=source_well, volume=sample_volume, tags=["SyringePump","SingleTip", "Backsolvent"])
                )
                tube_rack_info[target_well] = AMEWS_tube(well=target_well, type="Blank", sampled_plate=cell_plate, sampled_well=source_well)
                well_index += 1
        """Fill Reagents"""
        for i in range(len(cell_volumes)):
            plate = f"cell_plate_{math.floor(i / 4)+1}"
            well = input_wells[i % 4]
            output_well = output_wells[i % 4]
            filled_volume = 0
            total_fill_volume = len(cell_volumes[i])*reagent_fill_volume
            for chemical, volume in cell_volumes[i].items():
                protocol.actions.append(
                    BigKahunaDispense(source_chemical="solvent", target_plate=plate, target_well=well, volume=reagent_fill_volume-volume, tags=["Chaser", "Backsolvent"])
                )
                protocol.actions.append(
                    BigKahunaDispense(source_chemical=chemical, target_plate=plate, target_well=well, volume=volume, tags=["SyringePump","SingleTip"])
                )
                filled_volume += reagent_fill_volume
            if filled_volume < total_fill_volume:
                protocol.actions.append(
                    BigKahunaDispense(source_chemical="solvent", target_plate=plate, target_well=well, volume=total_fill_volume-filled_volume, tags=["SyringePump","SingleTip", "Backsolvent"])
                )
            protocol.actions.append(
                    BigKahunaDispense(source_chemical="solvent", target_plate=plate, target_well=output_well, volume=total_fill_volume, tags=["SyringePump","SingleTip", "Backsolvent"])
                )

        protocol.actions.append(
            BigKahunaDelay(target_plate="cell_plate_1", delay=fill_delay)
            )
        """Calibrate"""
        for i in range(0, num_cells):
               for aliquot in aliquots:
                    target_well = tube_rack_wells[well_index]
                    source_well = input_wells[i % 4]
                    cell_plate = f"cell_plate_{math.floor(i / 4)+1}"
                    protocol.actions.append(
                        BigKahunaDispense(source_chemical="solvent", target_plate="ICP_rack", target_well=target_well, volume=full_tube_volume-aliquot, tags=["Chaser", "Backsolvent"])
                    )
                    protocol.actions.append(
                        BigKahunaTransfer(source_plate=cell_plate, target_plate="ICP_rack", source_well=source_well, target_well=target_well, volume=aliquot, tags=["SyringePump","SingleTip"])
                    )
                    protocol.actions.append(
                        BigKahunaDispense(source_chemical="solvent", target_plate=cell_plate, target_well=source_well, volume=aliquot, tags=["SyringePump","SingleTip", "Backsolvent"])
                    )
                    tube_rack_info[target_well] = AMEWS_tube(well=target_well, type="Calibrate", sampled_plate=cell_plate, sampled_well=source_well)
                    well_index += 1
    while well_index < len(tube_rack_wells) and current_samples < total_samples:
        for i in range(starting_cell, num_cells):
                if well_index >= len(tube_rack_wells) or current_samples >= total_samples:
                    break
                target_well = tube_rack_wells[well_index]
                source_well = output_wells[i % 4]
                cell_plate = f"cell_plate_{math.floor(i / 4)+1}"
                protocol.actions.append(
                    BigKahunaDispense(source_chemical="solvent", target_plate="ICP_rack", target_well=target_well, volume=full_tube_volume-sample_volume, tags=["Chaser", "Backsolvent"])
                )
                protocol.actions.append(
                    BigKahunaTransfer(source_plate=cell_plate, target_plate="ICP_rack", source_well=source_well, target_well=target_well, volume=sample_volume, tags=["SyringePump","SingleTip"])
                )
                protocol.actions.append(
                    BigKahunaDispense(source_chemical="solvent", target_plate=cell_plate, target_well=source_well, volume=sample_volume, tags=["SyringePump","SingleTip", "Backsolvent"])
                )
                
                tube_rack_info[target_well] = AMEWS_tube(well=target_well, type="Sample", sampled_plate=cell_plate, sampled_well=source_well)
                next_cell = i + 1
                well_index += 1
                current_samples += 1
        if well_index <= len(tube_rack_wells) and current_samples < total_samples and total_samples > 90:
          protocol.actions.append(
                    BigKahunaDelay(target_plate=cell_plate, delay=sampling_delay)
                )
          next_cell = 0
        starting_cell = 0
        
    return protocol, tube_rack_info, next_cell, current_samples




         