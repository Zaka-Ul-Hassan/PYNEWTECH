# backend\app\services\zoom\zoom_service.py

import subprocess
import urllib.parse
import time

import pyautogui
import pygetwindow as gw
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from app.schemas.response_schema import ResponseSchema
from app.utils.zoom_helper import (
    _find_zoom_exe,
    _wait_for_zoom_window,
    _focus_zoom_window,
    _bypass_interstitial,
    _ensure_preview_mic_muted,
    _ensure_preview_camera_off,
    _dismiss_audio_dialog,
    _ensure_muted,
    _ensure_video_off,
    _gui_force_mute,
    _gui_force_video_off,
)


# 1. YOUR ACCOUNT — Desktop App (GUI Automation)
def join_meeting_gui(meeting_id: str, password: str = None):
    try:
        if not meeting_id:
            return ResponseSchema(status=False, message="Meeting ID required", data=None)

        zoom_exe = _find_zoom_exe()
        if not zoom_exe:
            return ResponseSchema(status=False, message="Zoom.exe not found.", data=None)

        zoom_url = f"zoommtg://zoom.us/join?action=join&confno={meeting_id}"
        if password:
            zoom_url += f"&pwd={urllib.parse.quote(password)}"

        subprocess.Popen([zoom_exe, f"--url={zoom_url}"])
        _wait_for_zoom_window(timeout=20)
        time.sleep(5)
        _focus_zoom_window()

        # Dismiss join/password prompts
        pyautogui.press('enter')
        time.sleep(3)
        pyautogui.press('enter')

        # Wait for meeting window to appear
        joined = False
        for _ in range(20):
            for w in gw.getWindowsWithTitle("Zoom"):
                if "Meeting" in w.title or meeting_id in w.title:
                    joined = True
                    break
            if joined:
                break
            time.sleep(1)

        if not joined:
            return ResponseSchema(status=False, message="Could not confirm meeting join.", data=None)

        # Wait for toolbar to fully render before touching mic/camera
        time.sleep(5)
        _focus_zoom_window()

        # State-aware: only press hotkey if currently in wrong state
        # _gui_force_mute checks current icon before pressing alt+a
        # _gui_force_video_off checks current icon before pressing alt+v
        _gui_force_video_off()
        _gui_force_mute()

        # Second pass after short delay — catches any Zoom re-enable on entry
        time.sleep(2)
        _focus_zoom_window()
        _gui_force_video_off()
        _gui_force_mute()

        return ResponseSchema(
            status=True,
            message=f"Meeting {meeting_id} joined. Mic and camera OFF.",
            data={"meeting_id": meeting_id},
        )

    except Exception as e:
        return ResponseSchema(status=False, message=f"GUI join failed: {str(e)}", data=None)


# 2. BOT — Browser Web Client (Selenium, joins as GUEST)
def join_meeting_bot(
    meeting_id: str,
    password: str = None,
    bot_name: str = "Meeting Bot",
):
    driver = None
    try:
        if not meeting_id:
            return ResponseSchema(status=False, message="Meeting ID required", data=None)

        options = webdriver.ChromeOptions()
        options.add_experimental_option("prefs", {
            "profile.default_content_setting_values.media_stream_mic": 2,
            "profile.default_content_setting_values.media_stream_camera": 2,
            "profile.default_content_setting_values.notifications": 2,
            "protocol_handler.excluded_schemes.zoommtg": True,
            "protocol_handler.excluded_schemes.zoomus": True,
        })
        options.add_argument("--use-fake-ui-for-media-stream")
        options.add_argument("--use-fake-device-for-media-stream")
        options.add_argument("--disable-notifications")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-external-intent-requests")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        driver = webdriver.Chrome(options=options)
        wait = WebDriverWait(driver, 30)

        zoom_url = f"https://app.zoom.us/wc/join/{meeting_id}?noappdesktop=1&browser=1"
        if password:
            zoom_url += f"&pwd={urllib.parse.quote(password)}"

        driver.get(zoom_url)
        _bypass_interstitial(driver)

        # Enter bot name
        try:
            name_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR,
                "input#input-for-name, input[placeholder*='name' i]")))
            name_field.clear()
            name_field.send_keys(bot_name)
        except TimeoutException:
            pass

        # Mute mic and camera on preview screen BEFORE joining
        _ensure_preview_mic_muted(driver)
        _ensure_preview_camera_off(driver)

        # Click Join
        try:
            join_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR,
                "button.preview-join-button, button[class*='join-btn'], button#joinBtn, button[class*='join']")))
            join_btn.click()
        except TimeoutException:
            return ResponseSchema(status=False, message="Could not find Join button.", data=None)

        # Confirm we entered the meeting
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR,
                "div.meeting-info-container, div[class*='meeting-client'], div#wc-container-right, div[class*='main-layout']")))
        except TimeoutException:
            return ResponseSchema(status=False, message="Could not confirm meeting entry. Host approval may be required.", data=None)

        _dismiss_audio_dialog(driver)

        # Wait for Zoom to finish initialising toolbar
        time.sleep(4)

        # Mute + video off — state-aware (only clicks if currently wrong state)
        _ensure_muted(driver)
        _ensure_video_off(driver)

        # Second pass — catches any delayed re-enable by Zoom
        time.sleep(3)
        _ensure_muted(driver)
        _ensure_video_off(driver)

        return ResponseSchema(
            status=True,
            message=f"'{bot_name}' joined meeting {meeting_id} as guest. Camera off, mic off.",
            data={"meeting_id": meeting_id, "bot_name": bot_name},
        )

    except WebDriverException as e:
        return ResponseSchema(status=False, message=f"Browser redirected to desktop app: {str(e)}", data=None)
    except Exception as e:
        return ResponseSchema(status=False, message=f"Bot join failed: {str(e)}", data=None)