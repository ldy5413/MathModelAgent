from utils.common_utils import load_toml
from utils.enums import CompTemplate
import os


class Config:
    def __init__(self, config: dict):
        self.api_key = config["api_key"]
        self.model = config["model"]
        self.base_url = config["base_url"]

        self.max_chat_turns: int | None = config["max_chat_turns"]
        self.max_retries: int | None = config["max_retries"]

    def get_model_config(self):
        return {
            "api_key": self.api_key,
            "model": self.model,
            "base_url": self.base_url,
        }

    def get_max_chat_turns(self):
        return self.max_chat_turns

    def get_max_retries(self):
        return self.max_retries

    def get_config_template(self, comp_template: CompTemplate):
        if comp_template == CompTemplate.CHINA:
            return load_toml(os.path.join("config", "md_template.toml"))

    def __str__(self):
        return f"api_key: {self.api_key}, model: {self.model}, base_url: {self.base_url} max_chat_turns: {self.max_chat_turns} max_retries: {self.max_retries}"
