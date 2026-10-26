"""
Windows Core Audio & Microphone Privacy Helpers for NOVA v1.0.2.
Provides permission verification, system-level mute detection, and automated unmuting
using standard Windows Core Audio COM interfaces via ctypes and ole32.CLSIDFromString.
"""

import sys
import os
import logging
import ctypes
from ctypes import wintypes
import winreg
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger("nova.voice.windows_audio")

class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", wintypes.BYTE * 8)
    ]

def _guid(s: str) -> GUID:
    g = GUID()
    if sys.platform.startswith("win"):
        ctypes.windll.ole32.CLSIDFromString(ctypes.c_wchar_p(s), ctypes.byref(g))
    return g

CLSCTX_INPROC_SERVER = 1
CLSCTX_ALL = 23
eCapture = 1       # Audio capture flow
eConsole = 0       # Console role


def check_windows_microphone_permission() -> Dict[str, Any]:
    """Check Windows registry consent store for microphone access."""
    if not sys.platform.startswith("win"):
        return {"status": "ok", "permission_allowed": True, "details": "Non-Windows OS"}

    results = {
        "global_allowed": True,
        "desktop_allowed": True,
        "permission_allowed": True,
        "details": "Microphone permissions granted in Windows settings."
    }

    # 1. Check Global consent store
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            val, _ = winreg.QueryValueEx(key, "Value")
            if str(val).lower() != "allow":
                results["global_allowed"] = False
                results["permission_allowed"] = False
                results["details"] = "Microphone access is disabled in Windows Privacy Settings (System > Privacy > Microphone)."
                return results
    except Exception as e:
        logger.debug(f"Could not check HKCU microphone consent: {e}")

    # 2. Check NonPackaged (Desktop Apps) consent store
    try:
        np_key_path = r"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone\NonPackaged"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, np_key_path) as key:
            val, _ = winreg.QueryValueEx(key, "Value")
            if str(val).lower() != "allow":
                results["desktop_allowed"] = False
                results["permission_allowed"] = False
                results["details"] = "Desktop apps are blocked from accessing the microphone in Windows Privacy Settings."
                return results
    except Exception as e:
        logger.debug(f"Could not check HKCU NonPackaged consent: {e}")

    return results


def get_default_capture_mute_and_volume() -> Tuple[Optional[bool], Optional[float]]:
    """
    Query the default Windows capture endpoint for mute status and master volume scalar (0.0 to 1.0).
    Uses COM IMMDeviceEnumerator and IAudioEndpointVolume.
    """
    if not sys.platform.startswith("win"):
        return False, 1.0

    ole32 = ctypes.windll.ole32
    ole32.CoInitialize(None)

    clsid_enum = _guid("{BCDE0395-E52F-467C-8E3D-C4579291692E}")
    iid_enum = _guid("{A95664D2-9614-4F35-A746-DE8DB63617E6}")
    iid_vol = _guid("{5CDF2C82-841E-4546-9722-0CF74078229A}")

    enumerator = ctypes.c_void_p()
    hr = ole32.CoCreateInstance(
        ctypes.byref(clsid_enum),
        None,
        CLSCTX_INPROC_SERVER,
        ctypes.byref(iid_enum),
        ctypes.byref(enumerator)
    )
    if hr != 0 or not enumerator:
        ole32.CoUninitialize()
        return None, None

    try:
        enum_vtable = ctypes.cast(
            ctypes.cast(enumerator, ctypes.POINTER(ctypes.c_void_p)).contents,
            ctypes.POINTER(ctypes.c_void_p)
        )
        GetDefaultAudioEndpoint_proto = ctypes.WINFUNCTYPE(
            ctypes.c_long,
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_void_p)
        )
        GetDefaultAudioEndpoint = GetDefaultAudioEndpoint_proto(enum_vtable[4])

        endpoint = ctypes.c_void_p()
        hr = GetDefaultAudioEndpoint(enumerator, eCapture, eConsole, ctypes.byref(endpoint))
        if hr != 0 or not endpoint:
            return None, None

        try:
            dev_vtable = ctypes.cast(
                ctypes.cast(endpoint, ctypes.POINTER(ctypes.c_void_p)).contents,
                ctypes.POINTER(ctypes.c_void_p)
            )
            Activate_proto = ctypes.WINFUNCTYPE(
                ctypes.c_long,
                ctypes.c_void_p,
                ctypes.POINTER(GUID),
                wintypes.DWORD,
                ctypes.c_void_p,
                ctypes.POINTER(ctypes.c_void_p)
            )
            Activate = Activate_proto(dev_vtable[3])

            audio_vol = ctypes.c_void_p()
            hr = Activate(endpoint, ctypes.byref(iid_vol), CLSCTX_ALL, None, ctypes.byref(audio_vol))
            if hr != 0 or not audio_vol:
                return None, None

            try:
                vol_vtable = ctypes.cast(
                    ctypes.cast(audio_vol, ctypes.POINTER(ctypes.c_void_p)).contents,
                    ctypes.POINTER(ctypes.c_void_p)
                )

                GetMute_proto = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.POINTER(wintypes.BOOL))
                GetMute = GetMute_proto(vol_vtable[14])

                GetMasterVolumeLevelScalar_proto = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.POINTER(ctypes.c_float))
                GetMasterVolumeLevelScalar = GetMasterVolumeLevelScalar_proto(vol_vtable[9])

                is_muted = wintypes.BOOL()
                GetMute(audio_vol, ctypes.byref(is_muted))

                vol_level = ctypes.c_float()
                GetMasterVolumeLevelScalar(audio_vol, ctypes.byref(vol_level))

                return bool(is_muted.value), float(vol_level.value)

            finally:
                Release_proto = ctypes.WINFUNCTYPE(wintypes.ULONG, ctypes.c_void_p)
                Release_proto(vol_vtable[2])(audio_vol)

        finally:
            Release_proto = ctypes.WINFUNCTYPE(wintypes.ULONG, ctypes.c_void_p)
            Release_proto(dev_vtable[2])(endpoint)

    finally:
        Release_proto = ctypes.WINFUNCTYPE(wintypes.ULONG, ctypes.c_void_p)
        Release_proto(enum_vtable[2])(enumerator)
        ole32.CoUninitialize()


def unmute_default_capture() -> bool:
    """Attempt to unmute the default capture endpoint if muted."""
    if not sys.platform.startswith("win"):
        return True

    ole32 = ctypes.windll.ole32
    ole32.CoInitialize(None)

    clsid_enum = _guid("{BCDE0395-E52F-467C-8E3D-C4579291692E}")
    iid_enum = _guid("{A95664D2-9614-4F35-A746-DE8DB63617E6}")
    iid_vol = _guid("{5CDF2C82-841E-4546-9722-0CF74078229A}")

    enumerator = ctypes.c_void_p()
    hr = ole32.CoCreateInstance(
        ctypes.byref(clsid_enum),
        None,
        CLSCTX_INPROC_SERVER,
        ctypes.byref(iid_enum),
        ctypes.byref(enumerator)
    )
    if hr != 0 or not enumerator:
        ole32.CoUninitialize()
        return False

    try:
        enum_vtable = ctypes.cast(
            ctypes.cast(enumerator, ctypes.POINTER(ctypes.c_void_p)).contents,
            ctypes.POINTER(ctypes.c_void_p)
        )
        GetDefaultAudioEndpoint_proto = ctypes.WINFUNCTYPE(
            ctypes.c_long,
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_void_p)
        )
        GetDefaultAudioEndpoint = GetDefaultAudioEndpoint_proto(enum_vtable[4])

        endpoint = ctypes.c_void_p()
        hr = GetDefaultAudioEndpoint(enumerator, eCapture, eConsole, ctypes.byref(endpoint))
        if hr != 0 or not endpoint:
            return False

        try:
            dev_vtable = ctypes.cast(
                ctypes.cast(endpoint, ctypes.POINTER(ctypes.c_void_p)).contents,
                ctypes.POINTER(ctypes.c_void_p)
            )
            Activate_proto = ctypes.WINFUNCTYPE(
                ctypes.c_long,
                ctypes.c_void_p,
                ctypes.POINTER(GUID),
                wintypes.DWORD,
                ctypes.c_void_p,
                ctypes.POINTER(ctypes.c_void_p)
            )
            Activate = Activate_proto(dev_vtable[3])

            audio_vol = ctypes.c_void_p()
            hr = Activate(endpoint, ctypes.byref(iid_vol), CLSCTX_ALL, None, ctypes.byref(audio_vol))
            if hr != 0 or not audio_vol:
                return False

            try:
                vol_vtable = ctypes.cast(
                    ctypes.cast(audio_vol, ctypes.POINTER(ctypes.c_void_p)).contents,
                    ctypes.POINTER(ctypes.c_void_p)
                )
                SetMute_proto = ctypes.WINFUNCTYPE(
                    ctypes.c_long,
                    ctypes.c_void_p,
                    wintypes.BOOL,
                    ctypes.POINTER(GUID)
                )
                SetMute = SetMute_proto(vol_vtable[14])
                empty_guid = GUID()
                hr = SetMute(audio_vol, wintypes.BOOL(False), ctypes.byref(empty_guid))
                return hr == 0
            finally:
                Release_proto = ctypes.WINFUNCTYPE(wintypes.ULONG, ctypes.c_void_p)
                Release_proto(vol_vtable[2])(audio_vol)
        finally:
            Release_proto = ctypes.WINFUNCTYPE(wintypes.ULONG, ctypes.c_void_p)
            Release_proto(dev_vtable[2])(endpoint)
    finally:
        Release_proto = ctypes.WINFUNCTYPE(wintypes.ULONG, ctypes.c_void_p)
        Release_proto(enum_vtable[2])(enumerator)
        ole32.CoUninitialize()
