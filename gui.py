
from pathlib import Path
import PySimpleGUI as sg
import sys 
import os 
from document_processing import process_files
import json 
import Levenshtein
############################### FUNCTIONS ############################### 

def find_closest_values(user_input, threshold):
    with open('document_information.json', 'r') as json_file:
        data = json.load(json_file)

    closest_values = []

    for entry in data:
        values = entry['values']
        path = entry['index']
        i = 0
        for extracted_value in values:
            distance = Levenshtein.distance(user_input, extracted_value)
            if distance <= threshold:
                closest_values.append({
                'value': extracted_value,
                'distance': distance,
                'image_path': path,
                'bounding_box': entry['bounding_boxes'][i]
            })
            
            i = i+1
    
    return closest_values

# This section (file and folder browsing) was written by Jason Yang (@jason990420)
def popup_paths(path=Path.home(), width=60):

    def short(file, width):
        return file[:width//2-3] + '...' + file[-width//2:] if len(file)>width else file

    def create_win(path):
        files = sorted(sorted(Path(path).iterdir()), key=lambda x:Path(x).is_file())
        treedata = sg.TreeData()
        for i, file in enumerate(files):
            f = str(file)
            treedata.insert("", i, short(f, width-8), [f], icon=folder_icon if Path(f).is_dir() else file_icon)
        layout = [
            [sg.Tree(data=treedata, headings=['Notes',], pad=(0, 0),
             show_expanded=True, col0_width=width, auto_size_columns=False,
            visible_column_map=[False,], select_mode=sg.TABLE_SELECT_MODE_EXTENDED,
            num_rows=15, row_height=16, font=('Courier New', 10), key="TREE")],
            [sg.Button('OK'), sg.Button('Cancel'), sg.Button('UP')],
        ]
        window = sg.Window("Select files or directories", layout, modal=True, finalize=True)
        tree = window['TREE']
        tree.Widget.configure(show='tree')      # Hide Tree Header
        tree.bind("<Double-1>", "_DOUBLE_CLICK")
        while True:
            event, values = window.read()
            if event == 'TREE_DOUBLE_CLICK':
                if values['TREE'] != []:
                    value = values['TREE'][0]
                    path = treedata.tree_dict[value].values[0]
                    if Path(path).is_dir():
                        result = path
                        break
                continue
            elif event in (sg.WINDOW_CLOSED, 'Cancel'):
                result = []
            elif event == 'OK':
                result = [treedata.tree_dict[i].values[0] for i in values['TREE']]
            elif event == 'UP':
                result = str(Path(path).parent)
            break
        window.close()
        return result

    while True:
        result = create_win(path)
        if isinstance(result, str):
            path = result
        else:
            break
    return result

def is_float(value):
    try:
        float(value)
        return True
    except ValueError:
        return False
    
def open_window(closest_values):
    layout = [
            [sg.Text("Search Results:")],
            [sg.Listbox(values=[f"Value: {item['value']} (Distance: {item['distance']})" for item in closest_values], size=(50,6))],
            [sg.Button("Show Image")],
            [sg.Button("Back to Search")]
        ]

    window = sg.Window('Search Results', layout)
    
    while True:
        event, values = window.read()
        if event == "Back to Search" or event == sg.WINDOW_CLOSED:
            break
    window.close()
    
############################### MAIN ############################### 

folder_icon = b'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAACXBIWXMAAAsSAAALEgHS3X78AAABnUlEQVQ4y8WSv2rUQRSFv7vZgJFFsQg2EkWb4AvEJ8hqKVilSmFn3iNvIAp21oIW9haihBRKiqwElMVsIJjNrprsOr/5dyzml3UhEQIWHhjmcpn7zblw4B9lJ8Xag9mlmQb3AJzX3tOX8Tngzg349q7t5xcfzpKGhOFHnjx+9qLTzW8wsmFTL2Gzk7Y2O/k9kCbtwUZbV+Zvo8Md3PALrjoiqsKSR9ljpAJpwOsNtlfXfRvoNU8Arr/NsVo0ry5z4dZN5hoGqEzYDChBOoKwS/vSq0XW3y5NAI/uN1cvLqzQur4MCpBGEEd1PQDfQ74HYR+LfeQOAOYAmgAmbly+dgfid5CHPIKqC74L8RDyGPIYy7+QQjFWa7ICsQ8SpB/IfcJSDVMAJUwJkYDMNOEPIBxA/gnuMyYPijXAI3lMse7FGnIKsIuqrxgRSeXOoYZUCI8pIKW/OHA7kD2YYcpAKgM5ABXk4qSsdJaDOMCsgTIYAlL5TQFTyUIZDmev0N/bnwqnylEBQS45UKnHx/lUlFvA3fo+jwR8ALb47/oNma38cuqiJ9AAAAAASUVORK5CYII='
file_icon = b'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAACXBIWXMAAAsSAAALEgHS3X78AAABU0lEQVQ4y52TzStEURiHn/ecc6XG54JSdlMkNhYWsiILS0lsJaUsLW2Mv8CfIDtr2VtbY4GUEvmIZnKbZsY977Uwt2HcyW1+dTZvt6fn9557BGB+aaNQKBR2ifkbgWR+cX13ubO1svz++niVTA1ArDHDg91UahHFsMxbKWycYsjze4muTsP64vT43v7hSf/A0FgdjQPQWAmco68nB+T+SFSqNUQgcIbN1bn8Z3RwvL22MAvcu8TACFgrpMVZ4aUYcn77BMDkxGgemAGOHIBXxRjBWZMKoCPA2h6qEUSRR2MF6GxUUMUaIUgBCNTnAcm3H2G5YQfgvccYIXAtDH7FoKq/AaqKlbrBj2trFVXfBPAea4SOIIsBeN9kkCwxsNkAqRWy7+B7Z00G3xVc2wZeMSI4S7sVYkSk5Z/4PyBWROqvox3A28PN2cjUwinQC9QyckKALxj4kv2auK0xAAAAAElFTkSuQmCC'

sg.theme('DarkBlue3')
sg.set_options(font=("Courier New", 12))

# Define the layout with fields
layout = [
    [sg.Text("Enter Numerical Value:"), sg.InputText(key="numerical_value")],
    [sg.Text("Distance Threshold (0-15):"), sg.Slider(range=(0, 15), default_value=0, orientation="h", key="threshold_slider")],
    [sg.Button("Browse")],
    [sg.Button("Search")]
]

window = sg.Window('DocSpotter', layout)

files = []

# Loop identifying events
while True:
    event, values = window.Read()
    if event == sg.WINDOW_CLOSED:
        break
    elif event == 'Browse':
        files = popup_paths(path='C:/', width=80)
        if files:
            process_files(files)
    elif event == 'Search':
        # Check all fields
        numerical_value = values["numerical_value"]
        threshold_percentage = values["threshold_slider"]

        if not numerical_value or not is_float(numerical_value):
            sg.popup_error("Invalid input. Please enter a numerical value.")

        if not files:
            sg.popup_error("You must choose atleast one file or folder.")

        closest_values = find_closest_values(numerical_value, threshold_percentage)
        
        open_window(closest_values);
        



window.close()
