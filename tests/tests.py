import os
from geonadir_upload_cli.util import (geonadir_filename_trans, get_filelist_from_collection,
                   original_filename)
import requests

def add_suffix_if_needed(file_path, file_name, file_dict):
    """
    Adds a suffix to the filename if it already exists in file_dict.

    Args:
        filename (str): The original file name.
        file_dict (dict): Dictionary that stores file names and their full paths.

    Returns:
        str: A unique file name with a suffix if needed.
    """
    # Split the filename into name and extension
    name, extension = os.path.splitext(file_name)
    suffix_count = 1

    # Check if the file name exists in the dictionary
    unique_file_name = file_name
    while unique_file_name in file_dict:
        # Check if the file path matches; if so, return the existing name
        if file_dict[unique_file_name] == file_path:
            return unique_file_name  # No need to add another suffix
        # If there's a conflict with a different path, add a suffix
        unique_file_name = f"{name}_Copy_{suffix_count}{extension}"
        suffix_count += 1

    return unique_file_name

def paginate_dataset_images(url, token, image_names: list):
    """
    Paginate through the dataset images API response to retrieve all image names.

    Args:
        url (str): URL of the API endpoint.
        image_names (list): List to store the image names.

    Returns:
        list: List of image names.
    """
    headers = {
        "authorization": token
    }
    try:
        print(f"get dataset images from {url}")
        response = requests.get(url, headers=headers, timeout=60)
        data = response.json()
        results = data["results"]
        for result in results:
            image_name = result["upload_files"]
            # image_name = re.search(r'([^/]+?)(?:_\d+)?\.JPG', image_url).group(1) + ".JPG"
            image_names.append(image_name)
        next_page = data["next"]
        if next_page:
            paginate_dataset_images(next_page, image_names)
        return image_names
    except Exception as exc:
        if "data" in locals():
            print(f"No image found in {url}")
        else:
            print(
                f"Failed to get dataset images from {url}: {str(exc)}")
        return []


img_dir = "/home/jli/geonadir-upload-cli/tests/bulk_upload_test"
file_list = os.listdir(img_dir)
file_list = [
        file for file in file_list if file.lower().endswith(
            ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tif')
        )
    ]
print(file_list)

file_dict={}
file_list=[]
for root, dirs, files in os.walk(img_dir):
    dirs.sort()
    files.sort()
    for file in files:
        if file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tif')):
            full_path = os.path.join(root, file)
            unique_file_name = add_suffix_if_needed(full_path, file, file_dict) # Ensure unique file name
            file_list.append(unique_file_name) # Add the unique file name to the list
            file_dict[unique_file_name] = full_path # Map the unique file name to the full path
print(file_list)

base_url="https://api.geonadir.com"
dataset_id="8769"
token="Token 85d639564fa162e054dec1423fcb740f6e5a7ccf"


url = f"{base_url}/api/uploadfiles/?page=1&project_id={dataset_id}"
existing_image_list = [original_filename(
    name) for name in paginate_dataset_images(url, token, [])]
existing_images = set(existing_image_list)
file_list = [file for file in file_list if geonadir_filename_trans(
    file) not in existing_images]
print(file_list)