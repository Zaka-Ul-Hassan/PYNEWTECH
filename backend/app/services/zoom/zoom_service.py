# backend\app\services\zoom\zoom_service.py

import subprocess
import threading
import urllib.parse
import time
from typing import Generator

import pyautogui
import pygetwindow as gw
from fastapi.responses import StreamingResponse
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
    _enable_live_transcript,
    collect_transcript,
)
from app.core.load_env import ZOOM_DESKTOP_BASE_URL, ZOOM_WEB_BASE_URL


# ── shared: build a headless Chrome driver for the bot ──
def _build_bot_driver():
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
    return webdriver.Chrome(options=options)


# ── shared: join Zoom web client, returns driver or raises ──
def _bot_join(driver, meeting_id: str, password: str, bot_name: str):
    wait = WebDriverWait(driver, 30)

    zoom_url = f"{ZOOM_WEB_BASE_URL}{meeting_id}?noappdesktop=1&browser=1"
    if password:
        zoom_url += f"&pwd={urllib.parse.quote(password)}"

    driver.get(zoom_url)
    _bypass_interstitial(driver)

    try:
        name_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR,
            "input#input-for-name, input[placeholder*='name' i]")))
        name_field.clear()
        name_field.send_keys(bot_name)
    except TimeoutException:
        pass

    _ensure_preview_mic_muted(driver)
    _ensure_preview_camera_off(driver)

    try:
        join_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR,
            "button.preview-join-button, button[class*='join-btn'], button#joinBtn, button[class*='join']")))
        join_btn.click()
    except TimeoutException:
        raise RuntimeError("Could not find Join button.")

    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR,
            "div.meeting-info-container, div[class*='meeting-client'], "
            "div#wc-container-right, div[class*='main-layout']")))
    except TimeoutException:
        raise RuntimeError("Could not confirm meeting entry. Host approval may be required.")

    _dismiss_audio_dialog(driver)
    time.sleep(4)
    _ensure_muted(driver)
    _ensure_video_off(driver)
    # Enable captions immediately after joining so transcript is ready to scrape
    _enable_live_transcript(driver)


# 1. YOUR ACCOUNT — Desktop App (GUI Automation)
def join_meeting_gui(meeting_id: str, password: str = None):
    try:
        if not meeting_id:
            return ResponseSchema(status=False, message="Meeting ID required", data=None)

        zoom_exe = _find_zoom_exe()
        if not zoom_exe:
            return ResponseSchema(status=False, message="Zoom.exe not found.", data=None)

        zoom_url = f"{ZOOM_DESKTOP_BASE_URL}{meeting_id}"
        if password:
            zoom_url += f"&pwd={urllib.parse.quote(password)}"

        subprocess.Popen([zoom_exe, f"--url={zoom_url}"])
        _wait_for_zoom_window(timeout=20)
        time.sleep(5)
        _focus_zoom_window()

        pyautogui.press('enter')
        time.sleep(3)
        pyautogui.press('enter')

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

        time.sleep(4)
        _focus_zoom_window()
        time.sleep(1)

        # One press each — GUI always joins with mic+camera ON
        pyautogui.hotkey('alt', 'v')
        time.sleep(0.5)
        pyautogui.hotkey('alt', 'a')
        time.sleep(0.5)

        return ResponseSchema(
            status=True,
            message=f"Meeting {meeting_id} joined. Mic and camera OFF.",
            data={"meeting_id": meeting_id},
        )

    except Exception as e:
        return ResponseSchema(status=False, message=f"GUI join failed: {str(e)}", data=None)


# 2. BOT — Browser Web Client (Selenium, joins as GUEST)
def join_meeting_bot(meeting_id: str, password: str = None, bot_name: str = "Meeting Bot"):
    driver = None
    try:
        if not meeting_id:
            return ResponseSchema(status=False, message="Meeting ID required", data=None)

        driver = _build_bot_driver()
        _bot_join(driver, meeting_id, password, bot_name)

        return ResponseSchema(
            status=True,
            message=f"'{bot_name}' joined meeting {meeting_id} as guest. Camera off, mic off.",
            data={"meeting_id": meeting_id, "bot_name": bot_name},
        )

    except WebDriverException as e:
        return ResponseSchema(status=False, message=f"Browser redirected to desktop app: {str(e)}", data=None)
    except Exception as e:
        return ResponseSchema(status=False, message=f"Bot join failed: {str(e)}", data=None)


# 3. BOT — Join + capture live transcript via Zoom's built-in captions
def get_meeting_transcript(
    meeting_id: str,
    password: str = None,
    bot_name: str = "Transcript Bot",
    duration_seconds: int = 300,
):
    driver = None
    try:
        if not meeting_id:
            return ResponseSchema(status=False, message="Meeting ID required", data=None)

        driver = _build_bot_driver()
        _bot_join(driver, meeting_id, password, bot_name)
        time.sleep(2)

        # Collect transcript — captions already enabled inside _bot_join
        transcript = collect_transcript(driver, duration_seconds=duration_seconds)

        return ResponseSchema(
            status=True,
            message=f"Transcript collected for {duration_seconds}s ({len(transcript)} lines).",
            data={"meeting_id": meeting_id, "transcript": transcript},
        )

    except WebDriverException as e:
        return ResponseSchema(status=False, message=f"Browser error: {str(e)}", data=None)
    except Exception as e:
        return ResponseSchema(status=False, message=f"Transcript capture failed: {str(e)}", data=None)
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


# 4. BOT — Stream live captions in real-time via SSE (one line per event as spoken)
def stream_meeting_transcript(
    meeting_id: str,
    password: str = None,
    bot_name: str = "Transcript Bot",
    duration_seconds: int = 3600,
) -> StreamingResponse:

    def _generate() -> Generator[str, None, None]:
        driver = None
        try:
            driver = _build_bot_driver()
            _bot_join(driver, meeting_id, password, bot_name)

            yield _sse("status", {"message": "Bot joined. Captions active."})

            seen = set()
            deadline = time.time() + duration_seconds

            while time.time() < deadline:
                try:
                    # Confirmed selector from DOM: span.live-transcription-subtitle__item
                    elements = driver.find_elements(
                        By.CSS_SELECTOR, "span.live-transcription-subtitle__item"
                    )
                    for el in elements:
                        text = el.text.strip()
                        if text and text not in seen:
                            seen.add(text)
                            yield _sse("caption", {
                                "timestamp": time.strftime("%H:%M:%S"),
                                "text": text,
                            })
                except Exception:
                    pass
                time.sleep(1)

            yield _sse("status", {"message": "Transcript session ended."})

        except Exception as e:
            yield _sse("error", {"message": str(e)})
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

    return StreamingResponse(_generate(), media_type="text/event-stream")


def _sse(event: str, data: dict) -> str:
    import json
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"