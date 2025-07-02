import pandas as pd
def parse_input_csv(path: str):
    with open(path, "r") as file:
       data = pd.read_csv(file, sep=",", header=0)
    input_chemicals = data.columns.to_list()
    cells = []
    for row in data.iterrows():
        cell = {}
        for i in range(len(input_chemicals)):
            if row[1][i] != 0 and not pd.isna(row[1][i]):
                cell[input_chemicals[i]] =  int(row[1][i])
        cells.append(cell)
    return input_chemicals, cells
        
        

