
from pathlib import Path
import PySimpleGUI as sg
from document_processing import *
from docspotter import create_craft_detector

############################### GUI FUNCTIONS ############################### 

def show_processing_popup():
    layout = [[sg.Text('Processing files, please wait...')]]
    window = sg.Window('Processing', layout, finalize=True)
    return window

def open_image(image_path):

    image_path = resize_image_for_display(image_path)
    # Create a window to display an image
    layout = [
        [sg.Image(filename=image_path)],
        [sg.Button("Close")]
    ]

    window = sg.Window(image_path, layout, finalize=True)

    while True:
        event, values = window.read()

        if event == sg.WIN_CLOSED or event == "Close":
            break

    window.close()


def open_explorer(path=Path.home(), width=60):
    """
    Function to open a file/folder explorer and select files or directories
    This section was written by Jason Yang (@jason990420)
    """
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


def open_search_results(closest_values):
    # Function to open the search results window and display closest values
    layout = [
            [sg.Text("Search Results:"), sg.Button("See Document", key="see_document")],
            [sg.Listbox(
                values=[f"Value: {item['value']} (Distance: {item['distance']})" for item in closest_values],
            size=(50, 6),
            enable_events=True,
            key="result_list", 
            select_mode = 'single')],
            [sg.Button("Back", key="back")]
        ]

    window = sg.Window('Search Results', layout)
    listbox = window['result_list']
    selected_item_key = None

    while True:
        event, values = window.read()
        if event == "back" or event == sg.WINDOW_CLOSED:
            break
        elif event == 'see_document':
            # Retrieve the associated data or key from the dictionary  
            selected_data =  closest_values[selected_item_key]
            new_image_path = draw_bounding_boxes(selected_data)
            if selected_data:
                open_image(new_image_path)

        elif event == 'result_list':
            # Handle button clicks for opening documents
            selected_item = values.get('result_list')
            if selected_item:
                    selected_item_key = listbox.get_indexes()[0]
    
    window.close()
    
############################ MAIN #######################
    
# Define icons for buttons
folder_icon = b'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAACXBIWXMAAAsSAAALEgHS3X78AAABnUlEQVQ4y8WSv2rUQRSFv7vZgJFFsQg2EkWb4AvEJ8hqKVilSmFn3iNvIAp21oIW9haihBRKiqwElMVsIJjNrprsOr/5dyzml3UhEQIWHhjmcpn7zblw4B9lJ8Xag9mlmQb3AJzX3tOX8Tngzg349q7t5xcfzpKGhOFHnjx+9qLTzW8wsmFTL2Gzk7Y2O/k9kCbtwUZbV+Zvo8Md3PALrjoiqsKSR9ljpAJpwOsNtlfXfRvoNU8Arr/NsVo0ry5z4dZN5hoGqEzYDChBOoKwS/vSq0XW3y5NAI/uN1cvLqzQur4MCpBGEEd1PQDfQ74HYR+LfeQOAOYAmgAmbly+dgfid5CHPIKqC74L8RDyGPIYy7+QQjFWa7ICsQ8SpB/IfcJSDVMAJUwJkYDMNOEPIBxA/gnuMyYPijXAI3lMse7FGnIKsIuqrxgRSeXOoYZUCI8pIKW/OHA7kD2YYcpAKgM5ABXk4qSsdJaDOMCsgTIYAlL5TQFTyUIZDmev0N/bnwqnylEBQS45UKnHx/lUlFvA3fo+jwR8ALb47/oNma38cuqiJ9AAAAAASUVORK5CYII='
file_icon = b'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAACXBIWXMAAAsSAAALEgHS3X78AAABU0lEQVQ4y52TzStEURiHn/ecc6XG54JSdlMkNhYWsiILS0lsJaUsLW2Mv8CfIDtr2VtbY4GUEvmIZnKbZsY977Uwt2HcyW1+dTZvt6fn9557BGB+aaNQKBR2ifkbgWR+cX13ubO1svz++niVTA1ArDHDg91UahHFsMxbKWycYsjze4muTsP64vT43v7hSf/A0FgdjQPQWAmco68nB+T+SFSqNUQgcIbN1bn8Z3RwvL22MAvcu8TACFgrpMVZ4aUYcn77BMDkxGgemAGOHIBXxRjBWZMKoCPA2h6qEUSRR2MF6GxUUMUaIUgBCNTnAcm3H2G5YQfgvccYIXAtDH7FoKq/AaqKlbrBj2trFVXfBPAea4SOIIsBeN9kkCwxsNkAqRWy7+B7Z00G3xVc2wZeMSI4S7sVYkSk5Z/4PyBWROqvox3A28PN2cjUwinQC9QyckKALxj4kv2auK0xAAAAAElFTkSuQmCC'

# Set the PySimpleGUI theme and options
sg.theme('DarkBlue3')
sg.set_options(font=("Courier New", 12))

# Define the main GUI layout
layout = [
    [sg.Text("Enter Numerical Value:"), sg.InputText(key="numerical_value")],
    [sg.Text("Distance Threshold (0-15):"), sg.Slider(range=(0, 15), default_value=0, orientation="h", key="threshold_slider")],
    [sg.Button("Browse")],
    [sg.Button("Search")]
]

window = sg.Window('DocSpotter', layout)

files = []
craft_obj = create_craft_detector()
file_path = ""
# Loop to handle events
while True:
    event, values = window.Read()

    if event == sg.WINDOW_CLOSED:
        break
    elif event == 'Browse':
        files = open_explorer(path='C:/', width=80)
        if files:
            print("Processing images..")
            window_process = show_processing_popup() 
            #import time
            #start_time = time.time()
            file_path = process_files(craft_obj, files)
            window_process.close()  
            #print("--- %s seconds ---" % (time.time() - start_time))
            print("Processing done, saving to json file.")
    elif event == 'Search':
        # Check if fields are valid 
        numerical_value = values["numerical_value"]
        if not numerical_value or not is_float(numerical_value):
            sg.popup_error("Invalid input. Please enter a numerical value.")
        elif not files:
            sg.popup_error("You must choose atleast one file or folder.")
        else:
            threshold_percentage = values["threshold_slider"]
            closest_values = find_closest_values(file_path, numerical_value, threshold_percentage)
            sorted_closest_values = sorted(closest_values, key=lambda x: x['distance'])
            open_search_results(sorted_closest_values);
    
# Close the main window
window.close()

