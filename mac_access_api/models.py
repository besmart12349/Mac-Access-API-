from __future__ import annotations

from pydantic import BaseModel, Field


class TerminalRequest(BaseModel):
    command: str = Field(..., min_length=1, max_length=4096, examples=["whoami"])


class AppleScriptRequest(BaseModel):
    script: str = Field(..., min_length=1, max_length=8192, examples=['display notification "hello"'])


class FileReadRequest(BaseModel):
    path: str = Field(..., min_length=1, max_length=1024)


class FileWriteRequest(BaseModel):
    path: str = Field(..., min_length=1, max_length=1024)
    content: str = Field(..., max_length=10_485_760)


class DirListRequest(BaseModel):
    path: str = Field(..., min_length=1, max_length=1024)


class FileDeleteRequest(BaseModel):
    path: str = Field(..., min_length=1, max_length=1024)


class FileMoveRequest(BaseModel):
    src: str = Field(..., min_length=1, max_length=1024)
    dst: str = Field(..., min_length=1, max_length=1024)


class NotificationRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=256)
    message: str = Field(..., min_length=1, max_length=1024)
    sound: bool = Field(True)


class ClipboardWriteRequest(BaseModel):
    text: str = Field(..., max_length=65536)


class VolumeRequest(BaseModel):
    level: int = Field(..., ge=0, le=100)


class BrightnessRequest(BaseModel):
    level: float = Field(..., ge=0.0, le=1.0)


class AppLaunchRequest(BaseModel):
    app_name: str = Field(..., min_length=1, max_length=256, examples=["Safari"])


class KillSwitchResetRequest(BaseModel):
    confirm: bool = Field(..., description="Must be true to reset kill switch")
