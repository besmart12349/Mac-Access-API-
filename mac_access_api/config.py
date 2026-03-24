from __future__ import annotations

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    api_key: str = Field("change-me-now", alias="MAC_ACCESS_API_KEY")
    host: str = Field("0.0.0.0", alias="MAC_ACCESS_HOST")
    port: int = Field(8787, alias="MAC_ACCESS_PORT")
    allowed_paths: str = Field("/Users,/tmp", alias="MAC_ACCESS_ALLOWED_PATHS")
    command_timeout_seconds: int = Field(20, alias="MAC_ACCESS_CMD_TIMEOUT")
    schedule_enabled: bool = Field(True, alias="MAC_ACCESS_SCHEDULE_ENABLED")
    schedule_start_hour: int = Field(0, alias="MAC_ACCESS_SCHEDULE_START_HOUR")
    schedule_end_hour: int = Field(23, alias="MAC_ACCESS_SCHEDULE_END_HOUR")
    schedule_timezone: str = Field("UTC", alias="MAC_ACCESS_SCHEDULE_TZ")
    kill_switch_file: str = Field("~/.mac_access_api.kill", alias="MAC_ACCESS_KILL_SWITCH_FILE")
    allow_insecure_default_key: bool = Field(False, alias="MAC_ACCESS_ALLOW_INSECURE_KEY")

    @property
    def allowed_path_list(self) -> list[Path]:
        return [Path(p).expanduser().resolve() for p in self.allowed_paths.split(",") if p.strip()]

    @property
    def kill_switch_path(self) -> Path:
        return Path(self.kill_switch_file).expanduser().resolve()


settings = Settings()
