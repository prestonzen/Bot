import os
import sys
import time
import random
import platform
import threading
import webbrowser
from queue import Queue

import requests
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.firefox.options import Options

# Attempt to import Service for Selenium 4 (if installed)
try:
    from selenium.webdriver.firefox.service import Service
    SELENIUM_V4 = True
except ImportError:
    Service = None
    SELENIUM_V4 = False

# =============================================================================
# Constants
# =============================================================================
PROXY_TEST_TIMEOUT = 5      # Seconds for requests-based proxy check
SELENIUM_LOAD_TIMEOUT = 15  # If 10anime doesn't load in 15s, discard proxy
DEFAULT_TIMEOUT = 180       # Selenium page load timeout if user wants it
DEFAULT_STAY_TIME = 180     # Stay on site for 3 minutes (example)
TARGET_SITE = "https://10anime.com"  # Default target

# Potential proxy sources (just an example list)
PROXY_URLS = [
    "https://us-proxy.org",
    "https://free-proxy-list.net/uk-proxy.html",
    "https://free-proxy-list.net/anonymous-proxy.html",
    "https://free-proxy-list.net",
    "https://www.socks-proxy.net",
]

COLORS = [
    "\033[1;31;40m",
    "\033[1;32;40m",
    "\033[1;33;40m",
    "\033[1;34;40m",
    "\033[1;35;40m",
    "\033[1;36;40m",
]

# Dynamically resolve Geckodriver path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GECKODRIVER_PATH = os.path.join(
    BASE_DIR,
    "geckodrivers",
    "geckodriver.exe" if platform.system() == "Windows" else "geckodriver"
)

def random_color():
    return str(random.choice(COLORS))

# =============================================================================
# Banner & Setup
# =============================================================================
def banner():
    system_platform = platform.system()
    if system_platform == "Windows":
        try:
            from art import text2art
            print(text2art("APTB", font="block"))
        except ImportError:
            print("To enhance this script on Windows, install the 'art' library: pip install art")
            print("APTB - Auto Proxy Traffic Booster")
    elif system_platform == "Linux":
        os.system("clear")
        os.system("apt install toilet -y")
        os.system("toilet -f term -F metal 'APTB'")
    else:
        print("APTB - Auto Proxy Traffic Booster")

    print("    \033[1;36;40m Script Modified by: \033[1;32;40m prestonzen")
    print("    \033[1;36;40m Instagram: \033[1;32;40m www.instagram.com/prestonzen")
    print("    \033[1;36;40m Github   : \033[1;32;40m www.github.com/prestonzen")
    print("    \033[1;36;40m Dedicated to: \033[1;34;40m The Cyber Community")
    print("        \033[1;31;40mNote: Some Proxies May Be Dead :(")
    print("        \033[1;31;40mCaution: Target Website May Detect This Bot.")
    print("\n\n")

def open_geckodriver_download():
    """
    If geckodriver isn't found, open the download page in the default browser
    or a fallback if on Windows/Linux with Edge/Firefox installed.
    """
    print("\033[1;31;40mGeckodriver not found!")
    print("Opening the Geckodriver download page in your browser...")
    geckodriver_url = "https://github.com/mozilla/geckodriver/releases"

    if platform.system() == "Windows":
        edge_path = "%ProgramFiles(x86)%\\Microsoft\\Edge\\Application\\msedge.exe"
        if os.path.exists(edge_path):
            webbrowser.register('edge', None, webbrowser.BackgroundBrowser(edge_path))
            webbrowser.get('edge').open(geckodriver_url)
        else:
            print("Edge browser not found. Please install it or manually visit the link.")
    elif platform.system() == "Linux":
        firefox_path = "/usr/bin/firefox"
        if os.path.exists(firefox_path):
            webbrowser.register('firefox', None, webbrowser.BackgroundBrowser(firefox_path))
            webbrowser.get('firefox').open(geckodriver_url)
        else:
            print("Firefox browser not found. Please install it or manually visit the link.")
    else:
        webbrowser.open(geckodriver_url)

    sys.exit()

# =============================================================================
# Proxy Scraping & Testing
# =============================================================================
def fetch_proxies(proxy_url):
    """
    Fetch proxies from the given URL by scraping the table of IPs/ports.
    Returns two lists: [ip1, ...], [port1, ...].
    """
    try:
        resp = requests.get(proxy_url, timeout=10)
        soup = BeautifulSoup(resp.content, 'html.parser')
        table = soup.find(class_='table table-striped table-bordered')
        if not table:
            return [], []
        cells = table.find_all('td')
        ip_list = [cells[i].text for i in range(0, len(cells), 8)]
        port_list = [cells[i].text for i in range(1, len(cells), 8)]
        return ip_list, port_list
    except Exception as e:
        print(f"[Error] Failed to fetch from {proxy_url}: {e}")
        return [], []

def test_proxy_advanced(ip, port, test_timeout=5):
    """
    Attempt multiple checks:
    1) HTTP check -> http://example.com
    2) HTTPS check -> https://www.google.com
    3) Actual site check -> https://10anime.com
    Return True if all pass, else False.
    """
    proxy_str = f"http://{ip}:{port}"
    proxies = {"http": proxy_str, "https": proxy_str}

    # 1) Quick HTTP check
    try:
        r = requests.get("http://example.com", proxies=proxies, timeout=test_timeout)
        if r.status_code not in [200, 301, 302]:
            return False
    except:
        return False

    # 2) Quick HTTPS check
    try:
        r = requests.get("https://www.google.com", proxies=proxies, timeout=test_timeout)
        if r.status_code not in [200, 301, 302]:
            return False
    except:
        return False

    # 3) 10anime check
    try:
        r = requests.get("https://10anime.com", proxies=proxies, timeout=test_timeout)
        if r.status_code not in [200, 301, 302]:
            return False
    except:
        return False

    return True

def gather_proxies_in_background(valid_queue, stop_event):
    """
    Runs in a background thread:
      - Continuously scrapes from PROXY_URLS, tests each proxy
      - As soon as a proxy is valid, put it into `valid_queue`
      - If `stop_event` is set, exit
    """
    print("[Background] Proxy gatherer started.")
    while not stop_event.is_set():
        for url in PROXY_URLS:
            if stop_event.is_set():
                break

            ip_list, port_list = fetch_proxies(url)
            for ip, port in zip(ip_list, port_list):
                if stop_event.is_set():
                    break

                print(f"  [Background] Testing: {ip}:{port}")
                if test_proxy_advanced(ip, port, test_timeout=PROXY_TEST_TIMEOUT):
                    print(f"    [Background] Valid => {ip}:{port}. Sending to queue.")
                    valid_queue.put((ip, port))

        # If we finish all sources, wait a bit and then start again
        # (You could break instead if you only want to scrape once)
        time.sleep(10)

    print("[Background] Proxy gatherer thread stopping.")

# =============================================================================
# Selenium
# =============================================================================
def create_firefox_driver(ip, port, page_load_timeout):
    """
    Create a Firefox driver with manual proxy config.
    """
    options = Options()
    options.set_preference("network.proxy.type", 1)
    options.set_preference("network.proxy.http", ip)
    options.set_preference("network.proxy.http_port", int(port))
    options.set_preference("network.proxy.ssl", ip)
    options.set_preference("network.proxy.ssl_port", int(port))
    options.set_preference("network.proxy.allow_hijacking_localhost", True)

    if SELENIUM_V4 and Service is not None:
        service = Service(GECKODRIVER_PATH)
        driver = webdriver.Firefox(service=service, options=options)
    else:
        driver = webdriver.Firefox(executable_path=GECKODRIVER_PATH, options=options)

    driver.set_page_load_timeout(page_load_timeout)
    return driver

def try_proxy_with_selenium(ip, port, target_url, load_timeout, stay_time):
    """
    Attempt to visit `target_url` with `ip:port`.
    Returns True if successful, False otherwise.
    """
    proxy_str = f"{ip}:{port}"
    print(f"\n\033[1;32;40m[Main] Trying proxy in Selenium => {random_color()}{proxy_str}")
    try:
        driver = create_firefox_driver(ip, port, load_timeout)
        driver.get(target_url)
        print(f"\033[1;32;40m   [Main] Page loaded. Staying for {stay_time}s...\n")
        time.sleep(stay_time)
        driver.quit()
        return True
    except WebDriverException as e:
        if "executable needs to be in PATH" in str(e):
            open_geckodriver_download()
        else:
            print(f"\033[1;31;40m[Main] Selenium Error with {proxy_str}: {e}")
    except Exception as e:
        print(f"\033[1;31;40m[Main] Unexpected error with {proxy_str}: {e}")
    return False


# =============================================================================
# Main
# =============================================================================
def main():
    """
    Main flow:
      1) Start a background thread that finds valid proxies
      2) As soon as one is found, try it in Selenium
      3) Continue grabbing new proxies from the queue as they become available
    """
    print(f"Resolved Geckodriver Path: {GECKODRIVER_PATH}")
    if not os.path.exists(GECKODRIVER_PATH):
        print("Geckodriver not found at the specified path. Please verify the location.")
        open_geckodriver_download()

    banner()

    # Prompt user for target; default to 10anime
    user_target = input(
        "\033[1;33;40mEnter The Target URL (Default: https://10anime.com): "
    ).strip()
    target = user_target if user_target else TARGET_SITE

    if "prestonzen" in target.lower():
        print("You can't perform this on my Website.")
        sys.exit()

    # Timeouts
    timeout_input = input(
        f"\033[1;33;40mEnter The Timeout (in seconds) [Default: {DEFAULT_TIMEOUT}]: "
    ).strip()
    page_timeout = int(timeout_input) if timeout_input else DEFAULT_TIMEOUT

    stay_input = input(
        f"\033[1;33;40mEnter The Stay Time (in seconds) [Default: {DEFAULT_STAY_TIME}]: "
    ).strip()
    stay_time = int(stay_input) if stay_input else DEFAULT_STAY_TIME

    # Prepare a queue to receive valid proxies from the background thread
    valid_proxy_queue = Queue()
    stop_event = threading.Event()

    # Start background thread
    t = threading.Thread(
        target=gather_proxies_in_background,
        args=(valid_proxy_queue, stop_event),
        daemon=True  # Daemon so it won't block program exit
    )
    t.start()

    print("\n[Main] Waiting for valid proxies to appear in the queue...")

    try:
        # We'll loop indefinitely, pulling proxies from the queue as they come in
        while True:
            # This call blocks until we get a new valid proxy
            ip, port = valid_proxy_queue.get()
            print(f"\n[Main] Got a valid proxy from queue: {ip}:{port}")
            # Attempt a short load with SELENIUM_LOAD_TIMEOUT
            if try_proxy_with_selenium(ip, port, target, SELENIUM_LOAD_TIMEOUT, stay_time):
                print("\n[Main] Proxy worked with quick load. Now optionally re-try with full page_timeout.\n")
                final_ok = try_proxy_with_selenium(ip, port, target, page_timeout, stay_time)
                if final_ok:
                    print("\033[1;32;40m[Main] Successfully visited the site with extended timeout.\n")
                else:
                    print("\033[1;33;40m[Main] Proxy passed quick test but failed extended load.\n")

            else:
                print(f"[Main] Proxy {ip}:{port} failed in Selenium.\n")

            # If you only need 1 success, you could break here
            # break

    except KeyboardInterrupt:
        print("\n[Main] CTRL+C pressed. Stopping background thread.")
        stop_event.set()
        t.join()
        print("[Main] Exiting...")

if __name__ == "__main__":
    main()
