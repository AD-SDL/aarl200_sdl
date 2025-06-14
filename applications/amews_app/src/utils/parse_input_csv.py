import pandas as pd
def parse_input_csv(path: str):
    with open(path, "r") as file:
       data = pd.read_csv(file, sep=",", header=0)
    input_chemicals = data.columns.to_list()
    cells = []
    for row in data.iterrows():
        for i in range(len(input_chemicals)):
            if row[1][i] != 0:
                cells.append({input_chemicals[i]: int(row[1][i])})
    return input_chemicals, cells
        
        

