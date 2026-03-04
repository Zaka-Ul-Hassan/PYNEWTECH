# backend\app\services\zoom\zoom_service.py

import os
import subprocess
import urllib.parse
import time

import pyautogui
import pygetwindow as gw
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

from app.schemas.response_schema import ResponseSchema
from app.core.load_env import ZOOM_EXE_PATHS

def _find_zoom_exe() -> str | None:
    for path in ZOOM_EXE_PATHS:
        if os.path.isfile(path):
            return path
    return None


# 1.YOUR ACCOUNT Desktop App (GUI Automation)

def join_meeting_gui(meeting_id: str, password: str = None):
    try:
        if not meeting_id:
            return ResponseSchema(status=False, message="Meeting ID required", data=None)

        zoom_exe = _find_zoom_exe()
        if not zoom_exe:
            return ResponseSchema(
                status=False,
                message="Zoom.exe not found. Add your path to ZOOM_EXE_PATHS in zoom_service.py.",
                data=None,
            )

        zoom_url = f"zoommtg://zoom.us/join?action=join&confno={meeting_id}"
        if password:
            zoom_url += f"&pwd={urllib.parse.quote(password)}"

        subprocess.Popen([zoom_exe, f"--url={zoom_url}"])

        _wait_for_zoom_window(timeout=20)
        time.sleep(4)
        _focus_zoom_window()

        pyautogui.hotkey('alt', 'v')
        time.sleep(0.8)
        pyautogui.hotkey('alt', 'a')
        time.sleep(0.8)

        pyautogui.press('enter')
        time.sleep(4)
        pyautogui.press('enter') 
        time.sleep(1)

        return ResponseSchema(
            status=True,
            message=f"Your account joined meeting {meeting_id} (camera off, mic off).",
            data={"meeting_id": meeting_id},
        )

    except Exception as e:
        return ResponseSchema(status=False, message=f"GUI join failed: {str(e)}", data=None)



# 2. BOT — Browser Web Client (Selenium, joins as GUEST — separate participant)
def join_meeting_bot(
    meeting_id: str,
    password: str = None,
    bot_name: str = "Meeting Bot",
):

    driver = None
    try:
        if not meeting_id:
            return ResponseSchema(status=False, message="Meeting ID required", data=None)

        #  Chrome options 
        options = webdriver.ChromeOptions()

        # Block mic & camera at OS permission level (value 2 = block)
        prefs = {
            "profile.default_content_setting_values.media_stream_mic": 2,
            "profile.default_content_setting_values.media_stream_camera": 2,
            "profile.default_content_setting_values.notifications": 2,
            # CRITICAL: stop Chrome from launching the zoommtg:// desktop app
            "protocol_handler.excluded_schemes.zoommtg": True,
            "protocol_handler.excluded_schemes.zoomus": True,
        }
        options.add_experimental_option("prefs", prefs)

        options.add_argument("--use-fake-ui-for-media-stream")   # silently deny cam/mic
        options.add_argument("--disable-notifications")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-external-intent-requests")  # block app handoff
        options.add_argument("--disable-popup-blocking")

        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        #  Launch browser 
        driver = webdriver.Chrome(options=options)
        wait = WebDriverWait(driver, 30)

        #  Navigate to Zoom Web Client 
        # noappdesktop=1 & browser=1 suppress the desktop app redirect
        zoom_url = (
            f"https://app.zoom.us/wc/join/{meeting_id}"
            f"?noappdesktop=1&browser=1"
        )
        if password:
            zoom_url += f"&pwd={urllib.parse.quote(password)}"

        driver.get(zoom_url)

        # Handle "Launching Zoom…" interstitial if it appears 
        _bypass_interstitial(driver)

        #  Enter bot display name 
        try:
            name_field = wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR,
                     "input#input-for-name, "
                     "input[placeholder*='name' i], "
                     "input[placeholder*='your name' i]")
                )
            )
            name_field.clear()
            name_field.send_keys(bot_name)
        except TimeoutException:
            pass  # Name screen skipped by meeting config

        #  Click Join button 
        try:
            join_btn = wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR,
                     "button.preview-join-button, "
                     "button[class*='join-btn'], "
                     "button#joinBtn, "
                     "button[class*='join']")
                )
            )
            join_btn.click()
        except TimeoutException:
            return ResponseSchema(
                status=False,
                message="Could not find the Join button. Check the meeting ID or passcode.",
                data=None,
            )

        #  Confirm we are inside the meeting room 
        try:
            wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR,
                     "div.meeting-info-container, "
                     "div[class*='meeting-client'], "
                     "div#wc-container-right, "
                     "div[class*='main-layout']")
                )
            )
        except TimeoutException:
            return ResponseSchema(
                status=False,
                message="Bot reached the meeting page but could not confirm entry. "
                        "Host approval may be required.",
                data=None,
            )

        #  Dismiss audio dialog & mute everything 
        _dismiss_audio_dialog(driver)
        _click_mute_buttons(driver)

        return ResponseSchema(
            status=True,
            message=f"'{bot_name}' joined meeting {meeting_id} as a guest (camera off, mic off).",
            data={"meeting_id": meeting_id, "bot_name": bot_name},
        )

    except WebDriverException as e:
        return ResponseSchema(
            status=False,
            message=f"Browser was redirected to desktop app. Session lost: {str(e)}",
            data=None,
        )
    except Exception as e:
        return ResponseSchema(status=False, message=f"Bot join failed: {str(e)}", data=None)


#  Helpers 

def _wait_for_zoom_window(timeout: int = 20):
    """Poll until a Zoom window appears and bring it to the foreground."""
    for _ in range(timeout):
        windows = gw.getWindowsWithTitle("Zoom")
        if windows:
            try:
                windows[0].activate()
            except Exception:
                pass
            return
        time.sleep(1)
    raise TimeoutError("Zoom window did not appear. Check ZOOM_EXE_PATHS.")


def _focus_zoom_window():
    """Click the center of the Zoom window to ensure keyboard focus."""
    windows = gw.getWindowsWithTitle("Zoom")
    if windows:
        win = windows[0]
        cx = win.left + win.width // 2
        cy = win.top + win.height // 2
        pyautogui.click(cx, cy)
        time.sleep(0.5)


def _bypass_interstitial(driver, timeout: int = 6):
    """Click 'join from your browser' if the Zoom launching interstitial appears."""
    try:
        link = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR,
                 "#btn-join-from-browser, "
                 "a[class*='browser-btn'], "
                 "a[href*='browser']")
            )
        )
        link.click()
        time.sleep(1)
    except TimeoutException:
        pass  # No interstitial — already on web client


def _dismiss_audio_dialog(driver, timeout: int = 10):
    """Click 'Join with Computer Audio' if the audio dialog appears."""
    try:
        btn = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR,
                 "button.join-audio-by-voip__join-btn, "
                 "button[class*='join-audio'], "
                 "button[class*='audio-btn']")
            )
        )
        btn.click()
    except TimeoutException:
        pass


def _click_mute_buttons(driver):
    """Click mute-audio and stop-video buttons in the meeting toolbar."""
    selectors = [
        "button[aria-label*='Mute' i], button[class*='mute-audio']",
        "button[aria-label*='Stop Video' i], button[class*='stop-video']",
    ]
    for selector in selectors:
        try:
            btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            )
            btn.click()
            time.sleep(0.5)
        except (TimeoutException, NoSuchElementException):
            pass