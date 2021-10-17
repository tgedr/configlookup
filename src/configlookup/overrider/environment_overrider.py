import logging
import os

from configlookup.overrider.abstract_overrider import AbstractOverrider

log = logging.getLogger(__name__)


class EnvironmentOverrider(AbstractOverrider):
    """
    class to override configuration values with related values found in environment variables
    to be used in Configuration
    example:
         "AA_VARIABLE" can be set in configuration file as 'XYZ'
         and it can be overridden if there is "AA_VARIABLE" environment variable with a different value
    """

    def get(self, key: str) -> str:
        log.debug(f"[get|in] ({key})")
        result = None
        try:
            result = os.environ[key]
        except KeyError as x:
            log.debug(f"environment variable not found: {key}", exc_info=x)

        log.debug(f"[get|out] => {result if result is not None else 'None'}")
        return result
