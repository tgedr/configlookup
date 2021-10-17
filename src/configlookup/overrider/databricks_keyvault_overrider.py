import logging

from configlookup.overrider.abstract_overrider import AbstractOverrider

log = logging.getLogger(__name__)


class DatabricksKeyVaultOverrider(AbstractOverrider):
    """
    class to override configuration values with related secrets found in a databricks keyvault
    to be used in Configuration
    example:
         "AA_XYZ_PSW" can be set in configuration file as 'dummy'
         and it can be overridden if there is "AA-XYZ-PSW" secret in a databricks keyvault
    """

    def __init__(self, keyvault_scope: str):
        log.info(f"[__init__|in] ({keyvault_scope})")
        self.__dbutils = DatabricksKeyVaultOverrider.get_dbutils()
        self.__scope = keyvault_scope
        log.info(f"[__init__|out]")

    def get(self, key: str) -> str:
        log.debug(f"[get|in] ({key})")
        result = None
        massaged_key = key.replace("_", "-")
        try:
            result = self.__dbutils.secrets.get(self.__scope, massaged_key)
        except Exception as x:
            log.debug(f"secret not found: {massaged_key}", exc_info=x)
        log.debug(f"[get|out] => {result[0:3] if result is not None else 'None'}")
        return result

    @staticmethod
    def get_dbutils():
        """
        helper method to load azure databricks dbutils instance
        accordingly to microsoft documentation:
        https://docs.microsoft.com/en-us/azure/databricks/dev-tools/databricks-connect#access-dbutils
        """
        log.info("[get_dbutils|in]")
        dbutils = None

        # this should only play out in an spark capable environment
        from pyspark.sql import SparkSession

        spark = SparkSession.builder.getOrCreate()

        DATABRICKS_VERSION_THRESHOLD = 7.3
        # we are going to diplomatically try to get some info from spark, avoiding the need for a fight here
        databricks_runtime_version = None
        try:
            databricks_runtime_version = float(spark.conf.get("spark.databricks.clusterUsageTags.sparkVersion")[:3])
        except Exception as x:
            log.info("[get_dbutils] could not get sparkVersion from spark conf", exc_info=x)

        service_client_enabled = "false"
        try:
            service_client_enabled = spark.conf.get("spark.databricks.service.client.enabled")
        except Exception as x:
            log.info("[get_dbutils] could not get service_client_enabled from spark conf", exc_info=x)

        log.info(f"[get_dbutils] databricksRuntimeVersion: {databricks_runtime_version}")
        try:
            if databricks_runtime_version is not None and databricks_runtime_version >= DATABRICKS_VERSION_THRESHOLD:
                from pyspark.dbutils import DBUtils

                dbutils = DBUtils(spark)
                log.info("[get_dbutils] got it from spark")
            elif service_client_enabled == "true":
                from pyspark.dbutils import DBUtils

                dbutils = DBUtils(spark)
                log.info("[get_dbutils] got it from spark")
            else:
                import IPython

                dbutils = IPython.get_ipython().user_ns["dbutils"]
                log.info("[get_dbutils] got it from IPython")
        except Exception as x:
            log.info("[get_dbutils] could not get it", exc_info=x)

        log.info(f"[get_dbutils|out] => {dbutils}")
        return dbutils
