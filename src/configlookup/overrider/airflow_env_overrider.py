import logging

from airflow.models import Variable

from configlookup.overrider.abstract_overrider import AbstractOverrider

log = logging.getLogger(__name__)


class AirflowEnvOverrider(AbstractOverrider):
    """
    class to override configuration values with related airflow variables
    to be used in Configuration
    example:
         AA_ENV can be set in configuration file as 'dev'
         but it can be overridden if there is AA_ENV in airflow variables with a different value
    """

    def get(self, key: str) -> str:
        log.debug(f"[get|in] ({key})")
        result = None
        try:
            result = Variable.get(key, None)
        except Exception as x:
            log.debug(f"no airflow environment variable: {key}", exc_info=x)

        log.debug(f"[get|out] => {result}")
        return result
