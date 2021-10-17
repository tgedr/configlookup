"""
not an actual automated unit tests
for manual testing purposes
"""
import json
import os
import re
import zipfile
from typing import List

CONFIG_FILE_PATTERN = re.compile("config_.*\\.json$")
ZIP_FILE_PATTERN = re.compile(".*\\.zip$")
TEMPLATE_FILE_PATTERN = re.compile("^config_local_template.json$")


def process_file(source: str):
    print(f"[process_file|in] ({source})")

    # check if the source file is in a zip file
    potential_zip_wrapper = re.match(r"(.*\.zip)/(.*)", source)
    if potential_zip_wrapper:
        print("[process_file] zip wrapper? yes")
        archive = zipfile.ZipFile(potential_zip_wrapper[1], "r")
        content = archive.read(potential_zip_wrapper[2]).decode("utf-8")
        print(json.loads(content))
    else:
        print("[process_file] zip wrapper? no")
        with open(source) as json_file:
            # json content is in itself a dict
            print(json.load(json_file))

    print(f"[process_file|out]")


def find_config_files(folder: str) -> List[str]:
    print(f"[find_config_files|in] ({folder})")

    result = []

    if ZIP_FILE_PATTERN.match(folder):
        result += sorted(
            [
                os.path.join(folder, file)
                for file in zipfile.ZipFile(folder).namelist()
                if CONFIG_FILE_PATTERN.match(file) and not TEMPLATE_FILE_PATTERN.match(file)
            ]
        )
    elif os.path.isdir(folder):
        result += sorted(
            [
                os.path.join(folder, file)
                for file in os.listdir(folder)
                if CONFIG_FILE_PATTERN.match(file) and not TEMPLATE_FILE_PATTERN.match(file)
            ]
        )
    print(f"[find_config_files|out] ({result})")
    return result


def main():
    print(f"[main|in]")
    config_files = find_config_files(f"{os.path.dirname(os.path.dirname(os.path.realpath(__file__)))}")
    for f in config_files:
        process_file(f)
    print(f"[main|out]")


if __name__ == "__main__":
    main()
