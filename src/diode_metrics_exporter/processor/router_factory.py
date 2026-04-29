# from diode_metrics_exporter.processor.healthcheck_processor import (
#     HealthcheckMonitor,
#     HealthcheckProcessor,
# )
# from diode_metrics_exporter.processor.ignore_processor import IgnoreProcessor
# from diode_metrics_exporter.processor.processor import FileProcessorRouter
# from diode_metrics_exporter.processor.tarball_processor import TarballProcessor


# def build_default_router(
#     healthcheck_monitor: HealthcheckMonitor,
# ) -> FileProcessorRouter:
#     return FileProcessorRouter(
#         processors=[
#             HealthcheckProcessor(healthcheck_monitor),
#             TarballProcessor(),
#             IgnoreProcessor(),
#         ]
#     )
