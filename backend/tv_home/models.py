from typing import Optional

from pydantic import BaseModel


class InstallBody(BaseModel):
    id: Optional[str] = None
    name: str
    url: str
    ua: Optional[str] = None


class MoveBody(BaseModel):
    dir: str  # "left" | "right"


class RadioBody(BaseModel):
    on: bool


class WifiConnectBody(BaseModel):
    ssid: str
    password: Optional[str] = None
    saved: Optional[bool] = False


class WifiForgetBody(BaseModel):
    ssid: str


class BtPowerBody(BaseModel):
    on: bool


class BtDeviceBody(BaseModel):
    mac: str
    name: str


class SoundActionBody(BaseModel):
    action: str  # up | down | mute | output
    id: Optional[str] = None


class DisplaySetBody(BaseModel):
    id: str


class DisplayConfirmBody(BaseModel):
    token: str


class ScreenOffBody(BaseModel):
    minutes: int


class PowerBody(BaseModel):
    action: str  # sleep | restart | poweroff | desktop
