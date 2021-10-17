import json
import logging
import os
import re
import zipfile
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from configlookup.utils import ConfigurationUtils

log = logging.getLogger(__name__)


class ConfigurationReader(ABC):
    """
    abstract class to define the interface of a generic configuration reader,
    main purpose will be to extend it to a class somehow and then call its 'read' method
    that in turn will read and provide us a dict with all the configuration read
    """

    @abstractmethod
    def read(self) -> dict:
        """
        reads configuration values from some source to be defined in the constructor, eventually
        Returns
        -------
            a dictionary with the overall configuration structure
        """


class FileSysConfigurationReader(ConfigurationReader):
    """
    ConfigurationReader file system implementation, reads configuration from files in the local file system
    """

    # pattern to figure out if we are trying to work with a file contained in a zip file
    ZIP_INCLUDED_FILE_PATTERN_COMPILED = re.compile(".*\\.zip/.*")
    ZIP_INCLUDED_FILE_PATTERN = r"(.*\.zip)/(.*)"

    def __init__(self, fs_refs: Union[List[str], str], data: Optional[Dict[str, Any]], filter_keys: List[str]):
        """
        loads values from configuration json files into a dict

        Parameters
        ----------
        fs_refs : Union[list, str]
            references to json files and/or folders containing them
        data : dict = None
            dict to load with the values
        filter_keys : List[str] = []
            enables the filtering of configuration file entries by its first level key, so that you can have in a
                single json file multiple configs, as in:
                {
                    "dev": {...},
                    "prod": {...}
                }
        """
        super().__init__()
        log.info(f"[__init__|in] (fs_refs: {fs_refs}, data: ..., filter_keys: {filter_keys})")
        self.__fs_refs = fs_refs
        self.__data = data or {}
        self.__filter_keys = filter_keys or []
        log.info(f"[__init__|out]")

    def read(self) -> dict:
        """
        reads configuration values from the provided json files and/or folders

        Returns
        -------
            a dictionary with the overall configuration structure
        """
        log.debug(f"[read|in]")

        input_type = type(self.__fs_refs).__name__
        if input_type == "str":
            if os.path.isdir(self.__fs_refs):
                self.__handle_dir(self.__fs_refs)
            elif os.path.isfile(self.__fs_refs) or FileSysConfigurationReader.ZIP_INCLUDED_FILE_PATTERN_COMPILED.match(
                self.__fs_refs
            ):
                # handle special case of zip file, it is a special file that need further peeling
                self.__handle_file(self.__fs_refs)
            else:
                raise ValueError(f"[read] {self.__fs_refs} is neither a file nor a folder")
        elif input_type == "list":
            self.__handle_array(self.__fs_refs)
        else:
            raise TypeError(f"[read] {self.__fs_refs} is neither a list nor a string")

        log.debug(f"[read|out] => {self.__data}")
        return self.__data

    def __process_file_content(self, content: Dict[str, Any]):
        """
        parses the configuration content, normally a dict reflecting the json configuration,
        and loads it into the private data structure (self.__data)
        Parameters
        ----------
        content : str
            the content of a configuration file, conveyed in a dict
        """
        log.debug(f"[__process_file_content|in] ({content})")
        if 0 < len(self.__filter_keys):
            # we must filter first level keys in the dict
            filtered_content = {}
            for filter_key in self.__filter_keys:
                if filter_key in content.keys():
                    filtered_entry = content[filter_key]

                    filtered_entry_type = type(filtered_entry).__name__
                    if filtered_entry_type != "dict":
                        raise ValueError(
                            f"[__process_file_content] filter key:{filter_key} does not correspond to a nested dict"
                        )
                    else:
                        ConfigurationUtils.merge_dict(filtered_entry, filtered_content)
            content = filtered_content

        ConfigurationUtils.merge_dict(content, self.__data)
        log.debug(f"[__process_file_content|out]")

    def __handle_array(self, source: List[str]):
        log.debug(f"[handle_array|in] ({source})")

        for entry in source:
            if os.path.isdir(entry):
                self.__handle_dir(entry)
            elif os.path.isfile(entry) or FileSysConfigurationReader.ZIP_INCLUDED_FILE_PATTERN_COMPILED.match(entry):
                self.__handle_file(entry)
            else:
                raise ValueError(f"[handle_array] {entry} is neither a file nor a folder")

        log.debug(f"[handle_array|out]")

    def __handle_file(self, source: str):
        log.debug(f"[handle_file|in] ({source})")

        if source.lower().endswith(".json"):
            # check if the source file is in a zip file and if so extract it
            potential_zip_wrapper = re.match(FileSysConfigurationReader.ZIP_INCLUDED_FILE_PATTERN, source)
            if potential_zip_wrapper:
                archive = zipfile.ZipFile(potential_zip_wrapper[1], "r")
                content = archive.read(potential_zip_wrapper[2]).decode("utf-8")
                self.__process_file_content(json.loads(content))
            else:
                with open(source) as json_file:
                    # json content is in itself a dict
                    content = json.load(json_file)
                    self.__process_file_content(content)
        else:
            raise ValueError(f"[handle_file] {source} is not a json file")

        log.debug(f"[handle_file|out]")

    def __handle_dir(self, source: str):
        log.debug(f"[handle_dir|in] ({source})")

        for file in os.listdir(source):
            entry = os.path.join(source, file)
            if os.path.isdir(entry):
                self.__handle_dir(entry)
            elif os.path.isfile(entry):
                self.__handle_file(entry)
            else:
                raise ValueError(f"[handle_dir] {entry} is neither a file nor a folder")

        log.debug(f"[handle_dir|out]")
