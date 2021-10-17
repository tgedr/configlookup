import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger(__name__)


class ConfigurationUtils:
    @staticmethod
    def merge_dict(
        source: Dict[str, Any],
        target: Dict[str, Any],
        target_property: Optional[str] = None,
        target_root: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        merges dictionary values recurrently

        Parameters
        ----------
        source : Dict[str, Any]
            the source dictionary to merge
        target : Dict[str, Any]
            the destination dictionary
        target_property: Optional[str]
            target dict equivalent property if not in the root of the target dict
        target_root: Optional[Dict[str, Any]]

        Raises
        ------
        ValueError
            if source or target are None
        TypeError
            when key types do not match across dictionaries

        """
        log.debug(f"[merge_dict|in] ({source}, {target}, {target_property}, {target_root}")

        if source is None:
            raise ValueError("mandatory to provide at least the source dict")
        if target is None:
            raise ValueError("mandatory to provide at least the target dict")

        if target_root is None:
            target_root = target

        for adding_key in source.keys():
            # for every entry in the source dictionary
            adding_value = source[adding_key]
            adding_value_type = type(adding_value).__name__

            if adding_value_type == "dict":
                # if value we want to add is a 'dict' then define the entry in the target and drill down recursively
                if adding_key not in target.keys():
                    target[adding_key] = {}
                elif type(target[adding_key]).__name__ != "dict":
                    raise TypeError(f"key: {adding_key} type does not match")

                adding_property = f"{'' if target_property is None else (target_property + '.')}{adding_key}"
                ConfigurationUtils.merge_dict(adding_value, target[adding_key], adding_property, target_root)
            elif adding_value_type == "list":
                # if value we want to add is a 'list' then define the list entry and extend it with the new values
                if adding_key not in target.keys():
                    target[adding_key] = []
                elif type(target[adding_key]).__name__ != "list":
                    raise TypeError(f"key: {adding_key} type does not match")

                existing_list = target[adding_key]
                existing_list.extend(adding_value)
                target[adding_key] = list(set(existing_list))
                # set the equivalent variable
                if target_root != target:
                    adding_property = f"{'' if target_property is None else (target_property + '.')}{adding_key}"
                    adding_var = adding_property.replace(".", "__").upper()
                    log.debug(f"[merge_dict] adding new entry {adding_var}: {target[adding_key]}")
                    target_root[adding_var] = target[adding_key]

            else:
                # if a scalar/text then just upsert the value
                log.debug(f"[merge_dict] adding new entry {adding_key}: {adding_value}")
                target[adding_key] = adding_value
                # set the equivalent variable
                if target_root == target:
                    adding_var = adding_key.upper()
                    target[adding_var] = adding_value
                else:
                    adding_property = f"{'' if target_property is None else (target_property + '.')}{adding_key}"
                    adding_var = adding_property.replace(".", "__").upper()
                    log.debug(f"[merge_dict] adding new entry {adding_var}: {target[adding_key]}")
                    target_root[adding_var] = target[adding_key]

        log.debug(f"[merge_dict|out] => {target}")

    @staticmethod
    def find_property(key: str, target: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        finds a property/variable with key format example "a.b.c" in the target dictionary
        Parameters
        ----------
        key : str
            the key to search for in the dictionary, in format "a.b.c"
        target : Dict[str, Any]
            the dictionary where to search for the key

        Returns
        -------
        Optional[Dict[str, Any]]
            a dict in the format {"pointer": target, "key": subkey} or None

        Raises
        ------
        ValueError
            if key or target are None
        """
        log.debug(f"[ConfigurationUtils.find_property|in] ({key}, {target})")

        if key is None:
            raise ValueError("no key name")
        if target is None:
            raise ValueError("no target")

        result = None

        # split the key in sub keys and start descending the dict structure from its root
        components = key.split(sep=".")

        for index, subkey in enumerate(components):
            # at every level of the structure check if the current sub key is present
            if subkey in target.keys():
                if index + 1 == len(components):
                    # if in last iteration and subkey and is part of the structure then wrap up in this dict format
                    result = {"pointer": target, "key": subkey}
                else:
                    # if not last iteration, then resume the search with the remaining subkeys in the child structure found
                    remaining_subkeys = ".".join(components[index + 1 :])
                    child_structure = target[subkey]
                    result = ConfigurationUtils.find_property(remaining_subkeys, child_structure)
                if result:
                    # don't iterate further if we have a solution
                    break
        log.debug(f"[ConfigurationUtils.find_property|out] => {result}")
        return result

    @staticmethod
    def get_config_file_paths(config_dir: str, config_file_prefix: str, config_file_suffixes: List[str]):
        """Function that looks for the required config files in dir_path.

        Parameters
        ----------
        config_dir : str
            The absolute path to a directory to look for files.
        config_file_prefix: str
            the file name prefix to look for, when appended with suffixes
        config_file_suffixes: List[str]
            the file name additional suffixes to use when searching for config files

        Returns
        -------
        list
            A list with the correct order of the config files.

        Raises
        ------
        FileNotFoundError
            If no config files are present in directory.
        """
        log.info(
            f"[ConfigurationUtils.get_config_file_paths|in] ({config_dir}, {config_file_prefix}, "
            f"{config_file_suffixes})"
        )
        file_paths = []
        files_to_find = [f"{config_file_prefix}{x}.json" for x in config_file_suffixes]
        log.info(f"[ConfigurationUtils.get_config_file_paths] files_to_find: {files_to_find}")
        available_files = [x.name for x in Path(config_dir).iterdir() if x.is_file()]
        for file_to_find in files_to_find:
            if file_to_find in available_files:
                file_paths.append(f"{config_dir}/{file_to_find}")

        if not file_paths:
            raise FileNotFoundError(
                f"[ConfigurationUtils.get_config_file_paths] Cannot locate configuration files in specified directory: "
                f"{config_dir}."
            )
        log.info(f"[ConfigurationUtils.get_config_file_paths|out] => {file_paths}")
        return file_paths

    @staticmethod
    def resolve_env_or_airflow_variable(variable: str, default: Optional[str] = None) -> str:
        log.info(f"[ConfigurationUtils.resolve_env_or_airflow_variable|in] ({variable}, {default})")

        _result = None
        log.debug("[ConfigurationUtils.resolve_env_or_airflow_variable] trying to find it in system variables")
        try:
            _result = os.environ[variable]
        except Exception as x:
            log.debug(
                f"[ConfigurationUtils.resolve_env_or_airflow_variable] not found: {variable}",
                exc_info=x,
            )

        if _result is None:
            log.debug("[ConfigurationUtils.resolve_env_or_airflow_variable] trying to find it in airflow variables")
            try:
                from airflow.models import Variable

                _result = Variable.get(variable)
            except Exception as x:
                log.debug(
                    f"[ConfigurationUtils.resolve_env_or_airflow_variable] no airflow variable: {variable}",
                    exc_info=x,
                )

        result = _result if _result is not None else default

        log.info(f"[ConfigurationUtils.resolve_env_or_airflow_variable|out] => {result}")
        return result

    @staticmethod
    def property_to_variable(prop: str) -> str:
        return prop.upper().replace(".", "__")

    @staticmethod
    def variable_to_property(var: str) -> str:
        return var.lower().replace("__", ".")

    @staticmethod
    def prop_and_var_from_key(key: str) -> Tuple[str, str]:
        prop = None
        var = None
        if 0 == key.count("."):
            # assume variable
            var = key.upper()
            prop = ConfigurationUtils.variable_to_property(var)
        else:
            prop = key.lower()
            var = ConfigurationUtils.property_to_variable(prop)

        return prop, var
