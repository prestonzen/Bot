import os
import sys
import random
import time
import platform
import webbrowser

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

# Constants
COUNT = 1200
DEFAULT_TIMEOUT = 180  # Default 3 minutes
DEFAULT_STAY_TIME = 180  # Default 3 minutes
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

def fetch_proxies(proxy_url):
    """
    Fetch proxies from the given URL by scraping the table of IPs and ports.
    """
    try:
        response = requests.get(proxy_url)
        soup = BeautifulSoup(response.content, 'html.parser')
        table = soup.find(class_='table table-striped table-bordered')
        if not table:
            return [], []

        cells = table.find_all('td')
        ip_list = [cells[i].text for i in range(0, len(cells), 8)]
        port_list = [cells[i].text for i in range(1, len(cells), 8)]
        return ip_list, port_list
    except Exception as e:
        print(f"Error fetching proxies from {proxy_url}: {e}")
        return [], []

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

def create_firefox_driver(ip, port, timeout):
    """
    Create and return a Firefox driver configured for the given IP:port proxy.
    - If Selenium 4 is available, we use the Service approach.
    - Otherwise, we fall back to the Selenium 3 style constructor.
    """
    options = Options()
    # Use manual proxy config
    options.set_preference("network.proxy.type", 1)
    options.set_preference("network.proxy.http", ip)
    options.set_preference("network.proxy.http_port", int(port))
    options.set_preference("network.proxy.ssl", ip)
    options.set_preference("network.proxy.ssl_port", int(port))
    options.set_preference("network.proxy.allow_hijacking_localhost", True)

    # Selenium 4 approach
    if SELENIUM_V4 and Service is not None:
        service = Service(GECKODRIVER_PATH)
        driver = webdriver.Firefox(service=service, options=options)
    else:
        # Selenium 3 fallback
        driver = webdriver.Firefox(executable_path=GECKODRIVER_PATH, options=options)

    driver.set_page_load_timeout(timeout)
    return driver

def test_proxy(ip, port, target_url, timeout, stay_time):
    """
    Attempt to visit the target URL using the given IP:port proxy.
    """
    proxy_str = f"{ip}:{port}"
    print(f"\033[1;32;40mTrying From {random_color()}{proxy_str}")

    try:
        driver = create_firefox_driver(ip, port, timeout)
        driver.get(target_url)
        time.sleep(stay_time)
        driver.quit()

    except WebDriverException as e:
        # If it's specifically a driver not found or driver mismatch issue:
        if "executable needs to be in PATH" in str(e) or "Unable to find a matching set of capabilities" in str(e):
            open_geckodriver_download()
        else:
            print(f"Error with proxy {proxy_str}: {e}")
    except Exception as e:
        print(f"Error with proxy {proxy_str}: {e}")

def main():
    """
    Main entry point
    1) Check if geckodriver exists
    2) Show banner
    3) Gather inputs
    4) Scrape proxies
    5) Test them
    """
    # Debugging geckodriver path
    print(f"Resolved Geckodriver Path: {GECKODRIVER_PATH}")
    if not os.path.exists(GECKODRIVER_PATH):
        print("Geckodriver not found at the specified path. Please verify the location.")
        open_geckodriver_download()

    banner()

    # Prompt user for target
    target = input("\033[1;33;40mEnter The Target URL (e.g., https://www.google.com): ").strip()
    if "prestonzen" in target.lower():
        print("You can't perform this on my Website.")
        sys.exit()

    # Prompt user for timeouts
    timeout = input(f"\033[1;33;40mEnter The Timeout (in seconds) [Default: {DEFAULT_TIMEOUT}]: ").strip()
    timeout = int(timeout) if timeout else DEFAULT_TIMEOUT

    stay_time = input(f"\033[1;33;40mEnter The Stay Time (in seconds) [Default: {DEFAULT_STAY_TIME}]: ").strip()
    stay_time = int(stay_time) if stay_time else DEFAULT_STAY_TIME

    # Loop through proxy URLs
    first_loop = True
    for proxy_url in PROXY_URLS:
        if not first_loop:
            # Sleep before each subsequent proxy URL
            print("\033[1;32;40mSleeping For 10 Seconds\n")
            time.sleep(10)
        else:
            first_loop = False

        banner()
        ips, ports = fetch_proxies(proxy_url)
        for ip, port in zip(ips, ports):
            test_proxy(ip, port, target, timeout, stay_time)

if __name__ == "__main__":
    main()
