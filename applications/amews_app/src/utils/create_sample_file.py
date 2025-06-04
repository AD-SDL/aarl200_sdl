from utils.AMEWS_types import AMEWS_tube
from ulid import ULID
import string
def well_to_icp_location(well: str) -> int:
    """
    Converts a well identifier to an ICP location.
    
    Args:
        well (str): The well identifier (e.g., "A1", "B2").
        
    Returns:
        str: The corresponding ICP location (e.g., 1, 2).
    """


    row = well[0].upper()  # Get the row letter (A, B, C, etc.)
    column = int(well[1:])  # Get the column number (1, 2, 3, etc.)
    row = string.ascii_uppercase.find(row) + 1
    return 10 + row*15 - (column - 1)
def create_sample_file(
    tube_rack_info: dict[str, AMEWS_tube],
    tube_rack_number: int,
    output_path: str,
    method: str = "Mina_HTS",
    file_name: str = "sample_info.sifx",
    description: str = "Sample information for AMEWS experiment",
    post_rinse: bool = True,
    calibrate: bool = True
) -> None:
    """
    Creates a JSON file containing information about the samples in the tube rack.

    Args:
        tube_rack_info (dict[str, AMEWS_tube]): Dictionary containing information about the tubes in the tube rack.
        output_path (str): The directory where the sample file will be saved.
        file_name (str): The name of the output file. Defaults to "sample_info.json".
    """

    from pathlib import Path

    output_file = Path(output_path) / file_name

    n = 2*calibrate + len(tube_rack_info.keys()) + int(post_rinse) + 1

    with open(output_file, "w") as file:
        file.write("[System Description]\n")
        file.write("Description=%s\n" % description)
        file.write("MaxNoOfSamples=%d\n" % n)
        file.write("[Constant Parameters]\n")
        file.write("BatchID=%s\n" % str(ULID()))
        file.write("VolumeUnits=Vol,mL,0.001,,\n")
        file.write("WeightUnits=Wt,g,1.00,,\n")
        file.write("[User Defined List]\n")
        file.write("NumberOfUserDefined=2\n")
        file.write("UserDefined1=kind\n")
        file.write("UserDefined2=method\n")
        file.write("UserDefined3=\n")
        file.write("UserDefined4=\n")
        file.write("UserDefined5=\n")
        file.write("[Variable Parameter List]\n")
        file.write("NumberOfParameters=5\n")
        file.write("Parameter1=SampleNo\n")
        file.write("Parameter2=AutosamplerLocation\n")
        file.write("Parameter3=SampleID\n")    
        file.write("Parameter4=UserDefField1\n")
        file.write("Parameter5=UserDefField2\n")
        file.write("[Variable Parameter Data]\n")
        file.write("NumberOfDataValues=%d\n" % n)

        sample_counter=1 # item counter

        # important: sample wetting, home
        file.write("Data%d=1,0,rinse,rinse,%s\n" % (sample_counter, method))
        sample_counter+=1
        if calibrate:
            file.write("Data%d=2,1,qualitycontrol,qc,%s\n" % (sample_counter, method)) # well 1
            sample_counter+=1

        for well, tube_info in tube_rack_info.items():
                    label = "rack" + str(tube_rack_number) + "well" + well 
                    file.write("Data%d=%d,%d,%s,sample,%s\n" % (sample_counter, 
                                                                sample_counter, 
                                                                well_to_icp_location(well), 
                                                                label, 
                                                                method,
                                                               ))
                    
                    sample_counter+=1


        if calibrate:
            file.write("Data%d=%d,1,qualitycontrol,qc,%s\n" % (sample_counter, sample_counter, method)) # well 1
            sample_counter+=1

        if post_rinse: # optional extra rinse at the end of a sequence, home
            
                file.write("Data%d=%d,0,rinse,rinse,%s\n" % (sample_counter, sample_counter, method))
                sample_counter+=1

        file.close()
        return output_file