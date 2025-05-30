from big_kahuna_protocol_types import BigKahunaProtocol, BigKahunaDispense, BigKahunaPlate, BigKahunaChemical, BigKahunaParameter, BigKahunaStir, BigKahunaTransfer
import string
def generate_fill_protocol():
    counter_wells=["A3"]#, "A4", "B3", "B4", "C3", "C4"]
    tube_rack_wells = [] 
    for i in range(0, 6):
        for j in range(1, 16):
            tube_rack_wells.append(string.ascii_uppercase[i] + str(j))
    sample_volume = 250
            
    protocol = BigKahunaProtocol(
                                name="AMEWS 6 cell fill",
                                units="ul",
                                parameters=[
                                     BigKahunaParameter(name="Delay", type="Time", unit="min"),
                                     BigKahunaParameter(name="StirRate", type="Stir Rate", unit="rpm"),
                                     BigKahunaParameter(name="Pause", type="Text", unit="")

                                 ],
                                 plates={
                                     "source_plate_1": BigKahunaPlate(name="source_plate_1", type="Rack 2x4 20mL Vial", rows=2, columns=4, deck_position="Deck 10-11 Position 2", source=True),
                                     "cell_plate_1": BigKahunaPlate(name="cell_plate_1", type="Rack 3x4 six Kaufmann H-cells", rows=3, columns=4, deck_position="Deck 12-13 Heat-Cool-Stir 1"),
                
                                 },
                                 chemicals=[
                                     BigKahunaChemical(name="mixture_1", source_plate="source_plate_1", deck_position="Deck 10-11 Position 2", row=1, column=1, volume=10000),
                                     BigKahunaChemical(name="mixture_2", source_plate="source_plate_1", deck_position="Deck 10-11 Position 2", row=1, column=2, volume=10000),
                                     BigKahunaChemical(name="mixture_3", source_plate="source_plate_1", deck_position="Deck 10-11 Position 2", row=1, column=3, volume=10000),
                                     BigKahunaChemical(name="mixture_4", source_plate="source_plate_1", deck_position="Deck 10-11 Position 2", row=1, column=4, volume=10000),
                                     BigKahunaChemical(name="mixture_5", source_plate="source_plate_1", deck_position="Deck 10-11 Position 2", row=2, column=1, volume=10000),
                                     BigKahunaChemical(name="mixture_6", source_plate="source_plate_1", deck_position="Deck 10-11 Position 2", row=2, column=2, volume=10000),
                                     BigKahunaChemical(name="mixture_7", source_plate="source_plate_1", deck_position="Deck 10-11 Position 2", row=2, column=3, volume=10000),
                                     BigKahunaChemical(name="mixture_8", source_plate="source_plate_1", deck_position="Deck 10-11 Position 2", row=2, column=4, volume=10000),
                                 ]
    

                                
                                 )
    protocol.actions.append(
        BigKahunaStir(target_plate="cell_plate_1", rate=500)
    )
    target_well_index = 0
    for well in counter_wells:
        protocol.actions.append(
            BigKahunaDispense(source_chemical="mixture_1", target_plate="cell_plate_1", target_well=well, volume=sample_volume, tags=["SyringePump","SingleTip"])
        )
        target_well_index += 1
    return protocol