import cv2
import json
import os
import re
from pathlib import Path
from PIL import Image
from pdf2image import convert_from_path
from concurrent.futures import ThreadPoolExecutor, as_completed
import pytesseract
import Levenshtein
import hashlib
from docspotter import detect_text, skew_and_extract_text

pytesseract.pytesseract.tesseract_cmd = r'E:\Program Files\Tesseract-OCR\tesseract.exe'
TEMP_DIR = "./temp"
CACHED_DIR = "./cached_files"

# Utility Functions 

def _get_image_name(path):
    return Path(path).stem

def is_float(value):
    """
    Check if the value can be converted to a float.
    """
    try:
        float(value)
        return True
    except ValueError:
        return False

def _has_numbers(string):
    """
    Check if the string contains any number.
    """
    return bool(re.search(r'\d', string))


def _preprocess_image(image_path):
    """
    Preprocess the image for better OCR results.
    """
    # Read the image and convert to grayscale
    image = cv2.imread(image_path)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    return image

def resize_image_for_display(image_path, max_size=(700, 700)):
    """
    Resize an image to fit within a window, maintaining aspect ratio.
    :param image_path: Path to the image file
    :param max_size: Maximum size (width, height) for the image to fit within
    :return: Path to the resized image
    """
    with Image.open(image_path) as img:
        img.thumbnail(max_size, Image.LANCZOS)
        resized_image_path = f"{TEMP_DIR}/{_get_image_name(image_path)}.png"
        img.save(resized_image_path)
    return resized_image_path

def calculate_files_hash(files_list):
    """
    Calculate a hash value based on the content of files list.
    """
    hasher = hashlib.sha256()
    for file_path in files_list:
        with open(file_path, 'rb') as file:
            while True:
                chunk = file.read(4096)
                if not chunk:
                    break
                hasher.update(chunk)
    return hasher.hexdigest()
    
# Main OCR and Image Processing Functions

def _extract_and_save_information(craft_obj, image_path):
    """
    Extract words and calculate bounding boxes from an image.
    """
    image = cv2.imread(image_path)
    prediction_result = detect_text(craft_obj, image)
    values, rois = skew_and_extract_text(image, prediction_result)
    serializable_rois = [roi.tolist() for roi in rois]
    return values, serializable_rois


def _create_json_entry(file_path, values, bboxes):
    """
    Create a JSON entry for the processed file.
    """
    entry = {"index": file_path,
            "values": values,
            "bounding_boxes": bboxes }
    
    return entry

def _process_single_file(craft_obj, path):
    """
    Process a single file, extracting text and saving information.
    """
    full_path = os.path.abspath(path)
    data = []
    if path.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', 'webp')):
        values, bboxes = _extract_and_save_information(craft_obj, full_path)
        data.append(_create_json_entry(full_path, values, bboxes))
    elif path.lower().endswith('.pdf'):
        pages = convert_from_path(full_path, 350)
        for i, page in enumerate(pages, start=1):
            image_name = f"{_get_image_name(path)}_page_{i}.jpg"
            image_path = os.path.join(TEMP_DIR, image_name)
            page.save(image_path, "JPEG")
            values, bboxes = _extract_and_save_information(craft_obj, image_path)
            data.append(_create_json_entry(image_path, values, bboxes))
    return data

def process_files(craft_obj, files):
    """
    Process a list of files, extracting text and saving information using multithreading.
    """
    os.makedirs(TEMP_DIR, exist_ok=True)
    os.makedirs(CACHED_DIR, exist_ok=True)
    data = []

    # Flatten all files and directories into a list of files
    all_files = []
    for file_or_dir in files:
        if os.path.isdir(file_or_dir):
            for root, _, filenames in os.walk(file_or_dir):
                for filename in filenames:
                    all_files.append(os.path.join(root, filename))
        else:
            all_files.append(file_or_dir)

    hash_result = calculate_files_hash(all_files)
    filename = os.path.join(CACHED_DIR, f"{hash_result}.json")

    if (os.path.exists(filename)):
        print(f"File has already been processed. Currently located in {CACHED_DIR}/{hash_result}.json")
    else:
        with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
            futures = [executor.submit(_process_single_file, craft_obj, file) for file in all_files]
            for future in as_completed(futures):
                data.extend(future.result())

        if data:
            filename = os.path.join(CACHED_DIR, f"{hash_result}.json")
            with open(filename, 'w') as json_file:
                json.dump(data, json_file, indent=4)
    
    return filename


def find_closest_values(file_path, user_input, threshold):
    with open(file_path, 'r') as json_file:
        data = json.load(json_file)

    closest_values = []
    for entry in data:
        for i, extracted_value in enumerate(entry['values']):
            distance = Levenshtein.distance(user_input, extracted_value)
            if distance <= threshold:
                closest_values.append({
                    'value': extracted_value,
                    'distance': distance,
                    'image_path': entry['index'],
                    'bounding_box': entry['bounding_boxes'][i]
                })
    return closest_values


def draw_bounding_boxes(selected_data):
    """
    Draw around the specified data on the image.
    """
    path, value, bbox = selected_data['image_path'], selected_data['value'], selected_data['bounding_box']
    annotated_image = cv2.imread(path)
    top_left = tuple(bbox[0])
    bottom_right = tuple(bbox[2])
    cv2.rectangle(annotated_image, top_left, bottom_right, (0, 0, 255), 2)
    new_image_path = f"./temp/{_get_image_name(path)}.png"
    cv2.imwrite(new_image_path, annotated_image)

    return new_image_path
    """
    # CODE FOR SVG GENERATION
    image_name = _get_image_name(path)
    img = Image.open(path)
    width, height = img.size

    # Extract bounding box coordinates
    x1, y1 = bbox[0]  # Coordinates of the top-left corner
    x2, y2 = bbox[2]  # Coordinates of the bottom-right corner

    # Calculate SVG coordinates based on image dimensions and bounding box
    x1_scaled = (x1 / width) * 100  
    y1_scaled = (y1 / height) * 100  
    x2_scaled = (x2 / width) * 100  
    y2_scaled = (y2 / height) * 100  

    # Generate SVG markup for rectangle
    svg_markup = f\"""
    <svg width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
        <image href="{path}" width="100%" height="100%" />
        <rect x="{x1_scaled}%" y="{y1_scaled}%" width="{x2_scaled - x1_scaled}%" height="{y2_scaled - y1_scaled}%" 
              stroke="red" stroke-width="2" fill="none" />
    </svg>
    \"""

    svg_filename = f"{TEMP_DIR}/{image_name}.svg"
    with open(svg_filename, 'w') as svg_file:
        svg_file.write(svg_markup)

    return svg_filename
    """

