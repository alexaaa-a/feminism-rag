from .di import LoggingProvider, SettingsProvider


common_provider = [SettingsProvider(), LoggingProvider()]
