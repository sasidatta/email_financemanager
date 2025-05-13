import yaml
import os

class Config:
    def __init__(self, config_path="config.yaml"):
        with open(config_path, 'r') as f:
            self._config = yaml.safe_load(f)

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