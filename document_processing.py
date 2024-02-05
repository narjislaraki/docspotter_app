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

pytesseract.pytesseract.tesseract_cmd = r'E:\Program Files\Tesseract-OCR\tesseract.exe'


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
        resized_image_path = f"./temp/{_get_image_name(image_path)}.png"
        img.save(resized_image_path)
    return resized_image_path
    
# Main OCR and Image Processing Functions

def _extract_and_save_information(image_path):
    """
    Extract words and calculate bounding boxes from an image.
    """

    image = _preprocess_image(image_path)
    d =  pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

    # Extract words and bounding boxes
    values = []
    bboxes = []
    # Iterate through the detected data
    for i in range(len(d['text'])):
        text_elem = d['text'][i].strip()
        if text_elem:  # Check if the word is not empty
            if _has_numbers(text_elem):
                values.append(text_elem)
                left, top, width, height = int(d['left'][i]), int(d['top'][i]), int(d['width'][i]), int(d['height'][i])
                right, bottom = left + width, top + height
                bboxes.append((left, top, right, bottom))
            

    return values, bboxes


def _create_json_entry(file_path, values, bboxes):
    """
    Create a JSON entry for the processed file.
    """
    entry = {"index": file_path,
            "values": values,
            "bounding_boxes": bboxes }
    
    return entry

def _process_single_file(path, temp_dir):
    """
    Process a single file, extracting text and saving information.
    """
    full_path = os.path.abspath(path)
    data = []
    if path.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
        values, bboxes = _extract_and_save_information(full_path)
        data.append(_create_json_entry(full_path, values, bboxes))
    elif path.lower().endswith('.pdf'):
        pages = convert_from_path(full_path, 350)
        for i, page in enumerate(pages, start=1):
            image_name = f"{_get_image_name(path)}_page_{i}.jpg"
            image_path = os.path.join(temp_dir, image_name)
            page.save(image_path, "JPEG")
            values, bboxes = _extract_and_save_information(image_path)
            data.append(_create_json_entry(image_path, values, bboxes))
    return data

def process_files(files):
    """
    Process a list of files, extracting text and saving information using multithreading.
    """
    temp_dir = "./temp"
    os.makedirs(temp_dir, exist_ok=True)
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

    with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
        futures = [executor.submit(_process_single_file, file, temp_dir) for file in all_files]
        for future in as_completed(futures):
            data.extend(future.result())

    if data:
        with open('document_information.json', 'w') as json_file:
            json.dump(data, json_file, indent=4)



def find_closest_values(user_input, threshold):
    with open('document_information.json', 'r') as json_file:
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
    left, top, right, bottom = bbox
    cv2.rectangle(annotated_image, (left, top), (right, bottom), (0, 0, 255), 2)
    new_image_path = f"./temp/{_get_image_name(path)}.png"
    cv2.imwrite(new_image_path, annotated_image)

    return new_image_path
