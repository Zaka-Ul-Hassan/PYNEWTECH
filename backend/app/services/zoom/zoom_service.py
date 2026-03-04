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
from selenium.webdriver.common.action_chains import ActionChains

from app.schemas.response_schema import ResponseSchema
from app.core.load_env import ZOOM_EXE_PATHS


def _find_zoom_exe() -> str | None:
    for path in ZOOM_EXE_PATHS:
        if os.path.isfile(path):
            return path
    return None


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

        pyautogui.press('enter')
        time.sleep(3)
        pyautogui.press('enter')

        joined = False
        for _ in range(20):
            windows = gw.getWindowsWithTitle("Zoom")
            for w in windows:
                if "Meeting" in w.title or meeting_id in w.title:
                    joined = True
                    break
            if joined:
                break
            time.sleep(1)

        if not joined:
            return ResponseSchema(
                status=False,
                message="Could not confirm meeting join.",
                data=None,
            )

        _focus_zoom_window()
        time.sleep(2)

        pyautogui.hotkey('alt', 'v')   # Video off
        time.sleep(0.5)
        pyautogui.hotkey('alt', 'a')   # Mute mic
        time.sleep(0.5)

        return ResponseSchema(
            status=True,
            message=f"Meeting {meeting_id} joined. Mic and camera turned OFF.",
            data={"meeting_id": meeting_id},
        )

    except Exception as e:
        return ResponseSchema(status=False, message=f"GUI join failed: {str(e)}", data=None)


#  2. BOT — Browser Web Client (Selenium, joins as GUEST) 

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

        prefs = {
            "profile.default_content_setting_values.media_stream_mic": 2,
            "profile.default_content_setting_values.media_stream_camera": 2,
            "profile.default_content_setting_values.notifications": 2,
            "protocol_handler.excluded_schemes.zoommtg": True,
            "protocol_handler.excluded_schemes.zoomus": True,
        }
        options.add_experimental_option("prefs", prefs)

        options.add_argument("--use-fake-ui-for-media-stream")
        options.add_argument("--disable-notifications")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-external-intent-requests")
        options.add_argument("--disable-popup-blocking")

        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        driver = webdriver.Chrome(options=options)
        wait = WebDriverWait(driver, 30)

        zoom_url = (
            f"https://app.zoom.us/wc/join/{meeting_id}"
            f"?noappdesktop=1&browser=1"
        )
        if password:
            zoom_url += f"&pwd={urllib.parse.quote(password)}"

        driver.get(zoom_url)

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
            pass

        # ── Preview screen: mute mic AND camera BEFORE clicking Join 
        _ensure_preview_mic_muted(driver)
        _ensure_preview_camera_off(driver)

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

        _dismiss_audio_dialog(driver)

        time.sleep(2)
        _reveal_toolbar(driver)
        time.sleep(1)

        _ensure_muted(driver)
        _ensure_video_off(driver)

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


# Helpers 

def _wait_for_zoom_window(timeout: int = 20):
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
    windows = gw.getWindowsWithTitle("Zoom")
    if windows:
        win = windows[0]
        cx = win.left + win.width // 2
        cy = win.top + win.height // 2
        pyautogui.click(cx, cy)
        time.sleep(0.5)


def _bypass_interstitial(driver, timeout: int = 6):
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
        pass


def _dismiss_audio_dialog(driver, timeout: int = 10):
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


def _safe_click(driver, btn):
    """Try normal click first, fall back to JS click."""
    try:
        btn.click()
    except Exception:
        driver.execute_script("arguments[0].click();", btn)


def _reveal_toolbar(driver):
    """
    The in-meeting footer has class 'footer__hidden' and auto-hides.
    Two-step approach:
      1. Move mouse to the centre-bottom of the page to trigger the hover reveal
      2. JS removes 'footer__hidden' as a hard fallback so buttons become clickable
    """
    try:
        # Step 1: hover over the meeting area to trigger the toolbar
        actions = ActionChains(driver)
        body = driver.find_element(By.TAG_NAME, "body")
        actions.move_to_element(body).perform()
        time.sleep(0.5)

        # Move to bottom-centre where the toolbar lives
        viewport_width = driver.execute_script("return window.innerWidth")
        viewport_height = driver.execute_script("return window.innerHeight")
        actions.move_by_offset(
            viewport_width // 2 - body.size["width"] // 2,
            viewport_height - 80
        ).perform()
        time.sleep(0.5)
    except Exception:
        pass

    # Step 2: JS force-remove the hidden class so buttons are interactable
    # Confirmed footer selectors from DOM screenshot:
    #   id="wc-footer"  class contains "footer__hidden"
    driver.execute_script("""
        // Remove hidden class from the main footer
        var footer = document.getElementById('wc-footer');
        if (footer) {
            footer.classList.remove('footer__hidden');
            footer.style.display = '';
            footer.style.visibility = 'visible';
            footer.style.opacity = '1';
        }

        // Also target any element with footer__hidden class
        var hiddenEls = document.querySelectorAll('.footer__hidden');
        hiddenEls.forEach(function(el) {
            el.classList.remove('footer__hidden');
            el.style.visibility = 'visible';
            el.style.opacity = '1';
        });

        // Ensure foot-bar is visible (confirmed id from DOM)
        var footBar = document.getElementById('foot-bar');
        if (footBar) {
            footBar.style.display = '';
            footBar.style.visibility = 'visible';
            footBar.style.opacity = '1';
        }
    """)
    time.sleep(0.5)


def _ensure_preview_mic_muted(driver, timeout: int = 5):
    """
    Preview screen: mute mic BEFORE clicking Join.

    Confirmed DOM:
      <button id="preview-audio-control-button">
        <span class="preview-video__control-text">Mute</span>   ← mic ON  → click
        <span class="preview-video__control-text">Unmute</span> ← mic OFF → skip
      </button>
    """
    selectors = [
        "button#preview-audio-control-button",   # confirmed ID
        "button[class*='preview-audio']",
        "button[aria-label*='microphone' i]",
        "button[aria-label*='mute' i]",
    ]
    for selector in selectors:
        try:
            btn = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            )
            label = (btn.get_attribute("aria-label") or "").lower()
            if "unmute" in label:
                return  # Already muted

            try:
                span = btn.find_element(
                    By.CSS_SELECTOR,
                    "span.preview-video__control-text, span[class*='control-text']"
                )
                if span.text.strip().lower() == "unmute":
                    return  # Already muted
            except NoSuchElementException:
                pass

            _safe_click(driver, btn)
            time.sleep(0.5)
            return

        except (TimeoutException, NoSuchElementException):
            continue


def _ensure_preview_camera_off(driver, timeout: int = 5):
    """
    Preview screen: turn camera OFF BEFORE clicking Join.

    Confirmed DOM:
      <button class="preview-video__control-button ...">
        <span class="preview-video__control-text">Stop Video</span>  ← camera ON  → click
        <span class="preview-video__control-text">Start Video</span> ← camera OFF → skip
      </button>
    """
    selectors = [
        "button[class*='preview-video__control-button']",   # confirmed class
        "button[aria-label*='stop my video' i]",
        "button[aria-label*='stop video' i]",
        "button[aria-label*='start my video' i]",
        "button[class*='preview-video']",
        "button[class*='video-preview']",
    ]
    for selector in selectors:
        try:
            btn = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            )
            label = (btn.get_attribute("aria-label") or "").lower()
            if "start" in label or "turn on" in label or "enable" in label:
                return  # Already off

            try:
                span = btn.find_element(
                    By.CSS_SELECTOR,
                    "span.preview-video__control-text, span[class*='control-text']"
                )
                if "start" in span.text.strip().lower():
                    return  # Already off
            except NoSuchElementException:
                pass

            _safe_click(driver, btn)
            time.sleep(0.5)
            return

        except (TimeoutException, NoSuchElementException):
            continue


def _ensure_muted(driver, timeout: int = 8):
    """
    In-meeting: mute mic ONLY if currently active.

    Confirmed DOM:
      class="... join-audio-container__btn"
      aria-label="mute my microphone"   ← mic ON  → click
      aria-label="unmute my microphone" ← mic OFF → skip
    """
    selectors = [
        "button.join-audio-container__btn[aria-label='mute my microphone']",
        "button.join-audio-container__btn[aria-label='unmute my microphone']",
        "button[aria-label='mute my microphone']",
        "button[aria-label='unmute my microphone']",
        "button[aria-label*='microphone' i]",
        "button[aria-label*='Mute' i]:not([aria-label*='Unmute' i])",
        "button[aria-label*='Unmute' i]",
        "button.join-audio-container__btn",
        "button[class*='mute-audio']",
    ]
    for selector in selectors:
        try:
            # Use presence_of_element_located here because toolbar is already
            # force-revealed by _reveal_toolbar — we just need to find + JS-click
            btn = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            label = (btn.get_attribute("aria-label") or "").lower()
            if not label:
                continue
            if "unmute" in label:
                return  # Already muted

            # Use JS click — bypasses any remaining visibility/interactability issues
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(0.5)
            return

        except (TimeoutException, NoSuchElementException):
            continue


def _ensure_video_off(driver, timeout: int = 8):
    """
    In-meeting: stop camera ONLY if currently active.

    Confirmed DOM:
      class="... send-video-container__btn"
      aria-label="stop my video"  ← camera ON  → click
      aria-label="start my video" ← camera OFF → skip
    """
    selectors = [
        "button.send-video-container__btn[aria-label='stop my video']",
        "button.send-video-container__btn[aria-label='start my video']",
        "button[aria-label='stop my video']",
        "button[aria-label='start my video']",
        "button[aria-label*='stop my video' i]",
        "button[aria-label*='start my video' i]",
        "button[aria-label*='Stop Video' i]",
        "button[aria-label*='Start Video' i]",
        "button.send-video-container__btn",
        "button[aria-label*='video' i]",
        "button[class*='stop-video']",
    ]
    for selector in selectors:
        try:
            btn = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            label = (btn.get_attribute("aria-label") or "").lower()
            if not label:
                continue
            if "start" in label or "turn on" in label:
                return  # Camera already OFF

            # Use JS click — bypasses visibility/interactability issues
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(0.5)
            return

        except (TimeoutException, NoSuchElementException):
            continue