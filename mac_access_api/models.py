from __future__ import annotations

from pydantic import BaseModel, Field


class TerminalRequest(BaseModel):
    command: str = Field(..., examples=["whoami"])


class AppleScriptRequest(BaseModel):
    script: str = Field(..., examples=['display notification "hello"'])


class FileReadRequest(BaseModel):
    path: str


class FileWriteRequest(BaseModel):
    path: str
    content: str


class DirListRequest(BaseModel):
    path: str


class VolumeRequest(BaseModel):
    level: int = Field(..., ge=0, le=100)


class OpenRequest(BaseModel):
    target: str = Field(..., examples=["https://apple.com", "/Applications/Notes.app"])


class ProcessSignalRequest(BaseModel):
    pid: int = Field(..., gt=0)
    signal: str = Field("TERM", examples=["TERM", "KILL", "HUP"])


class ScreenCaptureRequest(BaseModel):
    path: str = Field(..., examples=["/tmp/mac-access-capture.png"])


class ClipboardRequest(BaseModel):
    content: str
