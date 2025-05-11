import os
import json
from typing import Dict, Any, Optional

class ConfigFileParser:
    """
    Parses a config JSON file for MCP server definitions and provides easy access to each server's launch details.
    """
    def __init__(self, config_path: str):
        self.config_path = os.path.abspath(config_path)
        self.config_data = self._load_config_file()

    def _load_config_file(self) -> Dict[str, Any]:
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        with open(self.config_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except Exception as e:
                raise ValueError(f"Error parsing config file: {e}")
        if 'mcpServers' not in data or not isinstance(data['mcpServers'], dict):
            raise ValueError("Config file missing 'mcpServers' section or not a dict")
        return data

    def get_server_names(self):
        return list(self.config_data['mcpServers'].keys())

    def get_server_config(self, server_name: str) -> Optional[Dict[str, Any]]:
        return self.config_data['mcpServers'].get(server_name)

    def iter_servers(self):
        for name, conf in self.config_data['mcpServers'].items():
            yield name, conf

    def get_all_server_configs(self) -> Dict[str, Dict[str, Any]]:
        return dict(self.config_data['mcpServers'])
