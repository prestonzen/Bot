"""
Auto Proxy Traffic Booster - Turbo Version
------------------------------------------
- Scrapes free proxy sites in parallel
- Tests each proxy in parallel with `requests`
- Runs 3 headless Selenium sessions simultaneously
- Colorizes output for readability

"""

import os
import sys
import time
import random
import platform
import threading
import webbrowser
from queue import Queue
from concurrent.futures import ThreadPoolExecutor

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
# COLOR CONSTANTS
# =============================================================================
RESET = "\033[0m"
RED   = "\033[1;31;40m"
GREEN = "\033[1;32;40m"
YELLOW= "\033[1;33;40m"
BLUE  = "\033[1;34;40m"
CYAN  = "\033[1;36;40m"
MAGENTA = "\033[1;35;40m"

COLOR_LIST = [RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN]

def color_text(color, text):
    return f"{color}{text}{RESET}"

# =============================================================================
# CONFIG
# =============================================================================
# Where to scrape free proxies from:
PROXY_URLS = [
    "https://us-proxy.org",
    "https://free-proxy-list.net/uk-proxy.html",
    "https://free-proxy-list.net/anonymous-proxy.html",
    "https://free-proxy-list.net",
    "https://www.socks-proxy.net",
]

TARGET_URL = "https://10anime.com"      # Default target site
MAX_PROXY_CHECK_THREADS = 10            # How many proxies to check in parallel
PROXY_TEST_TIMEOUT = 5                  # Seconds for each proxy check
NUM_SELENIUM_WORKERS = 3               # Run 3 headless browsers in parallel
PAGE_LOAD_TIMEOUT = 15                 # Selenium's load timeout
STAY_TIME = 180                          # How long each browser stays on the site
GECKODRIVER_DIR = "geckodrivers"       # Subfolder for geckodriver
GECKODRIVER_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    GECKODRIVER_DIR,
    "geckodriver.exe" if platform.system() == "Windows" else "geckodriver"
)

# =============================================================================
# BANNER & DISCLAIMER
# =============================================================================
def banner():
    """
    Basic ASCII banner with color. 
    If you have the `art` library installed, it can do fancy text.
    """
    print(color_text(YELLOW, "=========================================="))
    print(color_text(YELLOW, "  Auto Proxy Traffic Booster - TURBO MODE  "))
    print(color_text(YELLOW, "==========================================\n"))
    print(color_text(CYAN, "DISCLAIMER: This script is for EDUCATIONAL PURPOSES ONLY."))
    print(color_text(CYAN, "Any unethical use (like blackhat SEO) is strongly discouraged.\n"))

def open_geckodriver_download():
    """
    If geckodriver isn't found, open the download page in the default browser.
    """
    print(color_text(RED, "Geckodriver not found!"))
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
# PROXY SCRAPER + TEST
# =============================================================================
def fetch_proxies(url):
    """
    Scrape proxies (IP:port) from a table, return ([ips], [ports]).
    """
    try:
        resp = requests.get(url, timeout=10)
        soup = BeautifulSoup(resp.content, 'html.parser')
        table = soup.find(class_='table table-striped table-bordered')
        if not table:
            return [], []
        cells = table.find_all('td')
        ip_list = [cells[i].text for i in range(0, len(cells), 8)]
        port_list = [cells[i].text for i in range(1, len(cells), 8)]
        return ip_list, port_list
    except Exception as e:
        print(color_text(RED, f"[ERROR] Unable to fetch from {url}: {e}"))
        return [], []

def test_proxy(ip, port, timeout=PROXY_TEST_TIMEOUT):
    """
    Perform multiple checks with 'requests':
      1) http://example.com
      2) https://www.google.com
      3) TARGET_URL (10anime.com by default)
    Return True if all pass, else False.
    """
    proxy_str = f"http://{ip}:{port}"
    proxies = {"http": proxy_str, "https": proxy_str}

    # 1) HTTP
    try:
        r = requests.get("http://example.com", proxies=proxies, timeout=timeout)
        if r.status_code not in [200, 301, 302]:
            return False
    except:
        return False

    # 2) HTTPS
    try:
        r = requests.get("https://www.google.com", proxies=proxies, timeout=timeout)
        if r.status_code not in [200, 301, 302]:
            return False
    except:
        return False

    # 3) Actual target
    try:
        r = requests.get(TARGET_URL, proxies=proxies, timeout=timeout)
        if r.status_code not in [200, 301, 302]:
            return False
    except:
        return False

    return True

def proxy_scraper_thread(proxy_queue, stop_event):
    """
    Runs in background:
     - Iterates over PROXY_URLS
     - Fetches proxies
     - Uses ThreadPoolExecutor to test them in parallel
     - Immediately enqueues valid proxies
     - Repeats every 10 seconds unless stop_event is set
    """
    print(color_text(GREEN, "[Scraper] Starting. We'll gather & test proxies in parallel..."))

    while not stop_event.is_set():
        for url in PROXY_URLS:
            if stop_event.is_set():
                break

            print(color_text(BLUE, f"[Scraper] Fetching from: {url}"))
            ips, ports = fetch_proxies(url)
            if not ips:
                print(color_text(YELLOW, f"   [Scraper] No proxies from {url}"))
                continue

            # Test the proxies in parallel
            with ThreadPoolExecutor(max_workers=MAX_PROXY_CHECK_THREADS) as executor:
                futures = []
                for ip, port in zip(ips, ports):
                    if stop_event.is_set():
                        break
                    futures.append(executor.submit(test_proxy, ip, port))

                # Check results
                idx = 0
                for f in futures:
                    if stop_event.is_set():
                        break
                    valid = f.result()
                    if valid:
                        ip_valid = ips[idx]
                        port_valid = ports[idx]
                        proxy_queue.put((ip_valid, port_valid))
                        print(color_text(GREEN, f"   [Scraper] VALID => {ip_valid}:{port_valid}"))
                    idx += 1

        # Sleep a bit, then repeat (or break if you only want 1 pass)
        time.sleep(10)

    print(color_text(RED, "[Scraper] Stop event detected. Exiting scraper thread."))

# =============================================================================
# SELENIUM WORKER
# =============================================================================
def create_firefox_driver(ip, port, load_timeout):
    """
    Creates a headless Firefox instance with the specified proxy.
    """
    options = Options()
    # HEADLESS for speed
    options.headless = True

    # Manual proxy
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

    driver.set_page_load_timeout(load_timeout)
    return driver

def selenium_worker(worker_id, proxy_queue, stop_event):
    """
    Each worker waits for a valid proxy in proxy_queue.
    When it gets one, it launches headless Firefox, visits TARGET_URL,
    stays for STAY_TIME, then finishes.
    Repeats until stop_event is set.
    """
    print(color_text(CYAN, f"[Worker-{worker_id}] Online. Waiting for proxies..."))

    while not stop_event.is_set():
        try:
            ip, port = proxy_queue.get(timeout=3)
        except:
            # No proxy found in time -> check if we should stop
            continue

        proxy_str = color_text(random.choice(COLOR_LIST), f"{ip}:{port}")
        print(color_text(MAGENTA, f"[Worker-{worker_id}] Launching Selenium with {proxy_str}"))
        try:
            driver = create_firefox_driver(ip, port, PAGE_LOAD_TIMEOUT)
            driver.get(TARGET_URL)
            print(color_text(GREEN, f"   [Worker-{worker_id}] Loaded {TARGET_URL}. Sleeping {STAY_TIME}s..."))
            time.sleep(STAY_TIME)
            driver.quit()
            print(color_text(GREEN, f"   [Worker-{worker_id}] Done with {proxy_str}."))
        except WebDriverException as e:
            print(color_text(RED, f"   [Worker-{worker_id}] Selenium Error: {e}"))
        except Exception as e:
            print(color_text(RED, f"   [Worker-{worker_id}] Unexpected error: {e}"))

        proxy_queue.task_done()

    print(color_text(RED, f"[Worker-{worker_id}] Stop event. Exiting."))

# =============================================================================
# MAIN
# =============================================================================
def main():
    global TARGET_URL
    global STAY_TIME

    # Basic checks
    if not os.path.exists(GECKODRIVER_PATH):
        print(color_text(RED, "[Main] Geckodriver not found. Please install or place it correctly."))
        open_geckodriver_download()

    banner()

    # Optionally let user override target, timeouts, etc.
    user_target = input(color_text(YELLOW, f"Enter Target URL [Default: {TARGET_URL}]: ")).strip()
    if user_target:
        TARGET_URL = user_target

    user_stay = input(color_text(YELLOW, f"Stay Time in seconds [Default: {STAY_TIME}]: ")).strip()
    if user_stay:
        try:
            STAY_TIME = int(user_stay)
        except:
            pass

    # Start concurrency
    proxy_queue = Queue()
    stop_event = threading.Event()

    # 1) Start the background scraper thread
    scraper_t = threading.Thread(target=proxy_scraper_thread, args=(proxy_queue, stop_event), daemon=True)
    scraper_t.start()

    # 2) Start multiple Selenium worker threads
    workers = []
    for i in range(NUM_SELENIUM_WORKERS):
        t = threading.Thread(target=selenium_worker, args=(i+1, proxy_queue, stop_event), daemon=True)
        t.start()
        workers.append(t)

    print(color_text(CYAN, "[Main] Running. Press Ctrl+C to stop."))

    try:
        while True:
            time.sleep(2)
    except KeyboardInterrupt:
        print(color_text(YELLOW, "\n[Main] Caught Ctrl+C. Shutting down..."))

    # Signal threads to stop
    stop_event.set()

    # Wait briefly for them to exit
    for w in workers:
        w.join(timeout=3)
    scraper_t.join(timeout=3)

    print(color_text(GREEN, "[Main] All threads joined. Exiting now."))

if __name__ == "__main__":
    main()
