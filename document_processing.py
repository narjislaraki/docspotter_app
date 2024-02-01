import pytesseract
import cv2
import os
from PIL import Image
from pdf2image import convert_from_path
import numpy as np
import json
from pathlib import Path
import re

pytesseract.pytesseract.tesseract_cmd = r'E:\Program Files\Tesseract-OCR\tesseract.exe'

def _has_numbers(string):
    return bool(re.search(r'\d', string))

def _preprocess_image(image_path):
    """
    This method is used before applying an OCR tool in order to have a better extraction
    """
    print(image_path)
    # Transform to grayscale
    image = cv2.imread(image_path)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Noise removal
    # image = cv2.medianBlur(image,5)
    """
    # Thresholding
    image = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1] # Or use adaptive threshold ?
    
    # dilation
    kernel = np.ones((5,5),np.uint8)
    image = cv2.dilate(image, kernel, iterations = 1)
    """
    
    return image


def _extract_and_save_information(image_path):
    """
    Extract words and calculate bounding boxes of an image
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
    entry = {"index": file_path,
            "values": values,
            "bounding_boxes": bboxes }
    
    return entry

def process_files(files):
    data = []
    if not os.path.exists("./temp"):
        os.makedirs("./temp")
    print("Processing images..")
    with open('document_information.json', 'w') as json_file:

        for path in files:
            full_path = os.path.abspath(path)
            
            if path.endswith((".jpg", ".jpeg", ".png", ".bmp")):
                values, bboxes = _extract_and_save_information(full_path)
                entry = _create_json_entry(full_path, values, bboxes)
                data.append(entry)

            elif path.endswith('.pdf'):
                pages = convert_from_path(full_path, 350)
                i = 1
                for page in pages:
                    image_name = Path(path).stem + "_page_" + str(i) + ".jpg" 
                    image_path = os.path.join("./temp/", image_name)
                    page.save(image_path, "JPEG")
                    values, bboxes = _extract_and_save_information(image_path)
                    entry = _create_json_entry(image_path, values, bboxes)
                    data.append(entry)
                    i = i+1    
            elif os.path.isdir(path):
                    file_paths = [os.path.join(path, filename) for filename in os.listdir(path)]
                    print(file_paths[0])
                    process_files(file_paths)
                    
            else: 
                pass
        
        print("Processing done, saving to json file.")
        json.dump(data, json_file, indent=4)
