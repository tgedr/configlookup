import logging
import os
from typing import List, Optional

from configlookup.overrider.databricks_keyvault_overrider import DatabricksKeyVaultOverrider
from configlookup.overrider.environment_overrider import EnvironmentOverrider
from configlookup.reader import FileSysConfigurationReader
from configlookup.singleton import SingletonMeta
from configlookup.utils import ConfigurationUtils

log = logging.getLogger(__name__)


class Configuration(metaclass=SingletonMeta):

    MANDATORY_CONFIGURATION_SECTION = "common"
    VAR_CONFIGURATION_DATABRICKS_KEYVAULT_SCOPE = "AA_CONFIGURATION_DATABRICKS_KEYVAULT_SCOPE"
    VAR_CONFIGURATION_ENABLE_AIRFLOW_VARS = "AA_CONFIGURATION_ENABLE_AIRFLOW_VARS"
    VAR_CONFIGURATION_DIR = "AA_CONFIGURATION_DIR"
    DEFAULT_CONFIGURATION_DIR = os.path.dirname(os.path.realpath(__file__))
    VAR_CONFIGURATION_FILE_PREFIX = "AA_CONFIGURATION_FILE_PREFIX"
    DEFAULT_CONFIGURATION_FILE_PREFIX = "pnd_personalization"
    DEFAULT_CONFIGURATION_FILE_SUFFIXES = ["", "_all", "_local"]
    VAR_CONFIGURATION_ENV = "AA_ENV"
    DEFAULT_CONFIGURATION_ENV = "dev"

    def __init__(
        self,
        files_path: Optional[str] = None,
        files_prefix: Optional[str] = None,
        files_additional_suffixes: Optional[List[str]] = None,
        files: Optional[List[str]] = None,
        environment: Optional[str] = None,
    ):
        """
        Parameters
        ----------
        files_path : Optional[str]
            folder where to find config files to be read
        files_prefix : Optional[str]
            config file prefix, default: "pnd_personalization", as in "pnd_personalization.json",
            "pnd_personalization_all.json", "pnd_personalization_local.json"
        files_additional_suffixes: Optional[List[str]]
            the file name additional suffixes to use when searching for config files (default: ["", "_all", "_local"]),
            as in "pnd_personalization.json", "pnd_personalization_all.json", "pnd_personalization_local.json"
        files : Optional[List[str]]
            instead of (config_path + file_prefix + file_additional_suffixes) we can just provide a list of absolute paths to config files
        environment : Optional[str]
            environment/stage hint, where are we running, enables the filtering of configuration file entries by
            its first level key, so that you can have in a single json file multiple configs, as in:
            {
                "dev": {...},
                "prod": {...}
            }
        Raises
        ------
        FileNotFoundError
            If no config files are present in directory.
        """
        super(Configuration, self).__init__()
        log.info(
            f"[__init__|in] ({files_path}, {files_prefix}, {files_additional_suffixes}, " f"{files}, {environment})"
        )
        self.__load(files_path, files_prefix, files_additional_suffixes, files, environment)
        log.info("[__init__|out]")

    def __load(
        self,
        files_path: Optional[str] = None,
        files_prefix: Optional[str] = None,
        files_additional_suffixes: Optional[List[str]] = None,
        files: Optional[List[str]] = None,
        environment: Optional[str] = None,
    ):
        log.info(
            f"[__load|in] (files_path={files_path}, files_prefix={files_prefix}, "
            f"files_additional_suffixes={files_additional_suffixes}, files={files}, environment={environment})"
        )
        data = {}
        # find runtime environment
        env = (
            ConfigurationUtils.resolve_env_or_airflow_variable(
                Configuration.VAR_CONFIGURATION_ENV, Configuration.DEFAULT_CONFIGURATION_ENV
            )
            if environment is None
            else environment
        )
        # find configuration files
        _file_suffixes = list(Configuration.DEFAULT_CONFIGURATION_FILE_SUFFIXES)
        if files_additional_suffixes is not None:
            _file_suffixes.extend(files_additional_suffixes)

        _files = ConfigurationUtils.get_config_file_paths(
            ConfigurationUtils.resolve_env_or_airflow_variable(
                Configuration.VAR_CONFIGURATION_DIR, Configuration.DEFAULT_CONFIGURATION_DIR
            )
            if files_path is None
            else files_path,
            ConfigurationUtils.resolve_env_or_airflow_variable(
                Configuration.VAR_CONFIGURATION_FILE_PREFIX,
                Configuration.DEFAULT_CONFIGURATION_FILE_PREFIX,
            )
            if files_prefix is None
            else files_prefix,
            _file_suffixes,
        )

        # load config from files
        data = FileSysConfigurationReader(_files, data, [Configuration.MANDATORY_CONFIGURATION_SECTION, env]).read()
        # handle overriders ...
        self.__overriders = []
        # ... overriders: airflow variables
        enable_airflow_vars = ConfigurationUtils.resolve_env_or_airflow_variable(
            Configuration.VAR_CONFIGURATION_ENABLE_AIRFLOW_VARS
        )
        if enable_airflow_vars is not None and enable_airflow_vars.lower() == "true":
            log.info("[__load] adding AirflowEnvOverrider")
            from configlookup.overrider.airflow_env_overrider import AirflowEnvOverrider

            self.__overriders.append(AirflowEnvOverrider())
        # ... overriders: databricks keyvault
        databricks_keyvault_scope = ConfigurationUtils.resolve_env_or_airflow_variable(
            Configuration.VAR_CONFIGURATION_DATABRICKS_KEYVAULT_SCOPE
        )
        if databricks_keyvault_scope is not None:
            log.info(f"[__load] adding DatabricksKeyVaultOverrider with scope: {databricks_keyvault_scope}")
            self.__overriders.append(DatabricksKeyVaultOverrider(databricks_keyvault_scope))
        # ... overriders: environment
        self.__overriders.append(EnvironmentOverrider())

        self.__data = data
        log.info(f"[__load|out] => {self.__data}")

    def __get_overridden(self, var: str) -> Optional[str]:
        """
        Parameters
        ----------
        var : str
            configuration key whose related variable is to be searched in the overriders
            NOTE: it must ALWAYS be part of the configuration file

        Returns
        -------
            a value if finds its key in any overrider, the last overrider always takes precedence
        """
        log.debug(f"[_get_overridden|in] ({var})")
        result = None
        for overrider in self.__overriders:
            overridden_value = overrider.get(var)
            if overridden_value is not None:
                result = overridden_value

        log.debug(f"[_get_overridden|out] => {result}")
        return result

    def __get(self, key: str):
        """
        get the configuration value

        Parameters
        ----------
        key : str
            configuration key in
            property format: common.vars.myconf
            or
            env var format: COMMON__VARS__MYCONF

        Returns
        -------
            configuration value
        """
        log.debug(f"[get|in] ({key})")
        result = None

        # remember, we want to find 'a.b.c' (property) and/or 'a__b__c' (variable)
        prop, var = ConfigurationUtils.prop_and_var_from_key(key)

        if var in self.__data.keys():
            # if it is not a complex type it should be stored as a first degree variable in the dict
            result = self.__data[var]
            # and if it is not a complex type it can be overridden
            overridden = self.__get_overridden(var)
            if overridden is not None:
                result = overridden
        else:
            # find the config in the data dict
            config = ConfigurationUtils.find_property(prop, self.__data)
            # remember every value should be defined in config, even if it is going to be overridden somewhere else
            if config is None:
                log.error(f"[__get] {prop} not found => {self.__data}")
                raise LookupError(f"[get] key {key} not found")

            config_pointer = config["pointer"]
            config_key = config["key"]
            result = config_pointer[config_key]

        log.debug(f"[get|out] => {result}")
        return result

    @staticmethod
    def get(key: str):
        if Configuration not in (Configuration._instances):
            log.info(f"[get_instance] creating a default instance as it wasn't bootstrapped before")
            Configuration()
        return Configuration._instances[Configuration].__get(key)
