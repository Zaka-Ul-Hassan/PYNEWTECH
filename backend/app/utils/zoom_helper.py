# backend\app\utils\zoom_helper.py

import os
import time
import pyautogui
import pygetwindow as gw
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains

from app.core.load_env import ZOOM_EXE_PATHS


def _find_zoom_exe() -> str | None:
    for path in ZOOM_EXE_PATHS:
        if os.path.isfile(path):
            return path
    return None


def _wait_for_zoom_window(timeout: int = 20):
    for _ in range(timeout):
        if gw.getWindowsWithTitle("Zoom"):
            try:
                gw.getWindowsWithTitle("Zoom")[0].activate()
            except Exception:
                pass
            return
        time.sleep(1)
    raise TimeoutError("Zoom window did not appear.")


def _focus_zoom_window():
    windows = gw.getWindowsWithTitle("Zoom")
    if windows:
        win = windows[0]
        pyautogui.click(win.left + win.width // 2, win.top + win.height // 2)
        time.sleep(0.5)


def _bypass_interstitial(driver, timeout: int = 6):
    try:
        link = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR,
                "#btn-join-from-browser, a[class*='browser-btn'], a[href*='browser']"))
        )
        link.click()
        time.sleep(1)
    except TimeoutException:
        pass


def _dismiss_audio_dialog(driver, timeout: int = 10):
    try:
        btn = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR,
                "button.join-audio-by-voip__join-btn, "
                "button[class*='join-audio'], "
                "button[class*='audio-btn']"))
        )
        btn.click()
    except TimeoutException:
        pass


def _reveal_toolbar(driver):
    # Target footer element directly — absolute position, not cumulative offset
    try:
        footer = driver.find_element(By.ID, "wc-footer")
        ActionChains(driver).move_to_element(footer).perform()
        time.sleep(0.4)
    except Exception:
        pass
    driver.execute_script("""
        ['wc-footer', 'foot-bar'].forEach(function(id) {
            var el = document.getElementById(id);
            if (el) { el.classList.remove('footer__hidden'); el.style.visibility='visible'; el.style.opacity='1'; el.style.display='flex'; }
        });
    """)
    time.sleep(0.3)


def _ensure_preview_mic_muted(driver, timeout: int = 5):
    for sel in ["button#preview-audio-control-button", "button[class*='preview-audio']", "button[aria-label*='microphone' i]"]:
        try:
            btn = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((By.CSS_SELECTOR, sel)))
            label = (btn.get_attribute("aria-label") or "").lower()
            span_text = ""
            try:
                span_text = btn.find_element(By.CSS_SELECTOR, "span[class*='control-text']").text.strip().lower()
            except NoSuchElementException:
                pass
            if "unmute" in label or span_text == "unmute":
                return  # already muted
            btn.click()
            time.sleep(0.8)
            return
        except (TimeoutException, NoSuchElementException):
            continue


def _ensure_preview_camera_off(driver, timeout: int = 5):
    for sel in ["button[class*='preview-video__control-button']", "button[aria-label*='stop video' i]", "button[class*='preview-video']"]:
        try:
            btn = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((By.CSS_SELECTOR, sel)))
            label = (btn.get_attribute("aria-label") or "").lower()
            span_text = ""
            try:
                span_text = btn.find_element(By.CSS_SELECTOR, "span[class*='control-text']").text.strip().lower()
            except NoSuchElementException:
                pass
            if "start" in label or "start" in span_text:
                return  # already off
            btn.click()
            time.sleep(0.8)
            return
        except (TimeoutException, NoSuchElementException):
            continue


def _ensure_muted(driver, timeout: int = 8):
    # "mute my microphone" = mic ON → click to mute
    # "unmute my microphone" = already muted → skip
    _reveal_toolbar(driver)
    for sel in [
        "button.join-audio-container__btn[aria-label='mute my microphone']",
        "button.join-audio-container__btn",
        "button[aria-label='mute my microphone']",
        "button[aria-label*='microphone' i]",
    ]:
        try:
            btn = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, sel)))
            label = (btn.get_attribute("aria-label") or "").lower()
            if not label:
                continue
            if "unmute" in label:
                return  # already muted
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(0.6)
            return
        except (TimeoutException, NoSuchElementException):
            continue


def _ensure_video_off(driver, timeout: int = 8):
    # "stop my video" = camera ON → click to stop
    # "start my video" = camera OFF → skip
    _reveal_toolbar(driver)
    for sel in [
        "button.send-video-container__btn[aria-label='stop my video']",
        "button.send-video-container__btn",
        "button[aria-label='stop my video']",
        "button[aria-label*='video' i]",
    ]:
        try:
            btn = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, sel)))
            label = (btn.get_attribute("aria-label") or "").lower()
            if not label:
                continue
            if "start" in label or "turn on" in label:
                return  # already off
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(0.6)
            return
        except (TimeoutException, NoSuchElementException):
            continue