__author__ = 'Arnaud Vandecasteele'
__date__ = 'April 2022'
__copyright__ = '(C) 2022, Arnaud Vandecasteele'


from qgis.core import Qgis, QgsMessageLog
import traceback

PLUGIN = 'GeoFoncier'

class Logger:

    @staticmethod
    def info(message: str):
        QgsMessageLog.logMessage("***********"+str(message), PLUGIN, Qgis.Info)

    @staticmethod
    def warning(message: str):
        QgsMessageLog.logMessage("***********"+str(message), PLUGIN, Qgis.Warning)

    @staticmethod
    def critical(message: str):
        QgsMessageLog.logMessage("***********"+str(message), PLUGIN, Qgis.Critical)

    @staticmethod
    def log_exception(e: BaseException):
        """ Log a Python exception. """
        Logger.critical(
            "Critical exception:\n{e}\n{traceback}".format(
                e=e,
                traceback=traceback.format_exc()
            )
        )