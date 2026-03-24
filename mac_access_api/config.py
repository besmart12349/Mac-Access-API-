from __future__ import annotations

from pathlib import Path
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    api_key: str = Field("change-me-now", alias="MAC_ACCESS_API_KEY")
    # Default to localhost only — user must explicitly open to 0.0.0.0
    host: str = Field("127.0.0.1", alias="MAC_ACCESS_HOST")
    port: int = Field(8787, alias="MAC_ACCESS_PORT")
    allowed_paths: str = Field("/Users,/tmp", alias="MAC_ACCESS_ALLOWED_PATHS")
    command_timeout_seconds: int = Field(20, alias="MAC_ACCESS_CMD_TIMEOUT")
    schedule_enabled: bool = Field(False, alias="MAC_ACCESS_SCHEDULE_ENABLED")
    schedule_start_hour: int = Field(0, alias="MAC_ACCESS_SCHEDULE_START_HOUR")
    schedule_end_hour: int = Field(23, alias="MAC_ACCESS_SCHEDULE_END_HOUR")
    schedule_timezone: str = Field("UTC", alias="MAC_ACCESS_SCHEDULE_TZ")
    kill_switch_file: str = Field("~/.mac_access_api.kill", alias="MAC_ACCESS_KILL_SWITCH_FILE")
    # Max file size for read/write operations (bytes), default 10MB
    max_file_bytes: int = Field(10_485_760, alias="MAC_ACCESS_MAX_FILE_BYTES")
    # Command blocklist (comma-separated substrings to reject)
    command_blocklist: str = Field(
        "rm -rf /,:(){ :|:& };:,curl|bash,wget|bash,mkfs",
        alias="MAC_ACCESS_CMD_BLOCKLIST",
    )
    # Log file path
    log_file: str = Field("~/.mac_access_api.log", alias="MAC_ACCESS_LOG_FILE")

    @field_validator("schedule_start_hour", "schedule_end_hour")
    @classmethod
    def valid_hour(cls, v: int) -> int:
        if not (0 <= v <= 23):
            raise ValueError("Hour must be 0-23")
        return v

    @property
    def allowed_path_list(self) -> list[Path]:
        return [Path(p).expanduser().resolve() for p in self.allowed_paths.split(",") if p.strip()]

    @property
    def kill_switch_path(self) -> Path:
        return Path(self.kill_switch_file).expanduser().resolve()

    @property
    def log_path(self) -> Path:
        return Path(self.log_file).expanduser().resolve()

    @property
    def command_blocklist_list(self) -> list[str]:
        return [s.strip() for s in self.command_blocklist.split(",") if s.strip()]


settings = Settings()
