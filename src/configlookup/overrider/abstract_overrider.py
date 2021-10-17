import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List

log = logging.getLogger(__name__)


class AbstractOverrider(ABC):
    """
    abstract class to extend in order to override configuration values
    """

    @staticmethod
    def validate_configuration(keys: List[str], config: Dict[str, Any]):
        log.info(f"[validate_configuration|in] (keys:{keys} config:{[k + ':' + v[0:3] for k, v in config.items()]})")
        if not set(keys).issubset(set(config.keys())):
            raise ValueError(f"mandatory config keys not provided: {keys} not a subset of {config.keys()}")
        log.info(f"[validate_configuration|out]")

    @abstractmethod
    def get(self, key: str) -> str:
        """
        this method should get the value from a configuration/variable store,
        that might be as an example the environment, an application specific parameters source,
        etc...

        Parameters
        ----------
        key : str
            the key that maps a value
        Returns
        -------
            the value for the key
        """
