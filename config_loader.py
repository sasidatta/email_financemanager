import yaml
import os

# Custom exception for config errors
class ConfigError(Exception):
    pass

class Config:
    def __init__(self, config_path="config.yaml"):
        if not os.path.exists(config_path):
            raise ConfigError(f"Config file not found: {config_path}")
        with open(config_path, 'r') as f:
            try:
                self._config = yaml.safe_load(f)
            except yaml.YAMLError as e:
                raise ConfigError(f"Error parsing config file: {e}")
        if self._config is None:
            self._config = {}

    @property
    def email(self):
        return self._config.get('email', {})

    @property
    def database(self):
        return self._config.get('database', {})

    @property
    def app(self):
        return self._config.get('app', {})

# Usage:
# config = Config()
# config.email['address'], config.database['host'], etc. 