import os
import time
import json
import shutil
from sys import platform
from pathlib import Path
from urllib.parse import quote

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.command import Command
from selenium.webdriver.support.ui import WebDriverWait

from selenium.webdriver import Chrome, Firefox, Opera, Remote
from msedge.selenium_tools import Edge


from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, \
                                       ElementNotInteractableException, UnexpectedAlertPresentException, \
                                       WebDriverException, SessionNotCreatedException, \
                                       NoSuchWindowException, InvalidSessionIdException

BRAVE_PATHS = {
    "win32": "C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe",
    "linux": "/opt/brave.com/brave/brave-browser",
    "darwin": "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
}


class WhapBot(object):
    _URL = "https://web.whatsapp.com/"
    _LOCAL_STORAGE = "whatsapp_cookies.json"
    _SELECTORS = {
        "main_page": '.two',
        "qr_code": 'canvas',
        "send_button": '//*[@id="main"]/footer/div[1]/div[3]/button',
        "chat_bar": 'div.input',
        "qr_reloader": 'div[data-ref] > span > div'
    }

    def __init__(self, browser: str, driver_path: str = "", profile_path: str = "",
                 headless: bool = False, kiosk: bool = False, proxy: str = None, command_executor: str = None):

        self.browser = browser.lower()
        self.headless = headless
        self.kiosk = kiosk

        self.proxy = proxy
        self.command_executor = command_executor

        self._logged = False

        if not driver_path:
            from .install import download_driver
            from .utils import search_driver
            download_driver(self.browser)
            driver_path = search_driver(browser=self.browser)
        self._driver_path = Path(driver_path).absolute()
        if not self._driver_path.exists():
            raise RuntimeError("Driver path does not exist")

        if not profile_path:
            profile_path = Path(f"{self._driver_path.parent}/{self.browser}-profile")
        self._profile_path = Path(profile_path).absolute()

        self._whatsapp_cookies = Path(f"{self._profile_path}/{self._LOCAL_STORAGE}")

        try:
            self._driver = self._create_selenium_driver()
        except OSError:
            raise RuntimeError(f"Incorrect executable path for {self.browser} driver")
        except SessionNotCreatedException:
            raise RuntimeError(f"Cannot create {self.browser} process with the current driver.\n"
                               f"Update your browser to the latest version or download the specific driver")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.quit()

    @property
    def is_logged(self):
        return self._logged

    @property
    def driver(self):
        return self._driver

    @driver.setter
    def driver(self, driver):
        self._driver = driver

    def _create_selenium_driver(self):
        options = self._create_options()

        if self.command_executor:  # remote driver
            driver = Remote(command_executor=self.command_executor, options=options)

        elif self.browser in ["chrome", "brave"]:
            driver = Chrome(executable_path=self._driver_path, options=options)

        elif self.browser == "opera":
            driver = Opera(executable_path=self._driver_path, options=options)

        elif self.browser == "edge":
            driver = Edge(executable_path=self._driver_path, options=options)

        elif self.browser == "firefox":
            from selenium.webdriver.firefox.options import FirefoxProfile

            if self._profile_path.exists():
                profile = FirefoxProfile(self._profile_path)
            else:
                profile = FirefoxProfile()

            driver = Firefox(
                executable_path=self._driver_path,
                options=options,
                firefox_profile=profile,
                service_log_path=Path(f"{self._driver_path.parent}/geckodriver.log")
            )
        else:
            raise RuntimeError(f"Cannot load Selenium driver for {self.browser}")

        # self.maximize_window()
        return driver

    def _create_options(self):

        if self.browser in ["chrome", "brave"]:
            from selenium.webdriver.chrome.options import Options as ChromeOptions
            options = ChromeOptions()
            if self.browser == "brave":
                options.binary_location = BRAVE_PATHS[platform]

        elif self.browser == "firefox":
            from selenium.webdriver.firefox.options import Options as FirefoxOptions
            options = FirefoxOptions()

        elif self.browser == "opera":
            from selenium.webdriver.opera.options import Options as OperaOptions
            options = OperaOptions()

        elif self.browser == "edge":
            from msedge.selenium_tools import EdgeOptions
            options = EdgeOptions()
            options.use_chromium = True
        else:
            raise RuntimeError(f"Unknown browser {self.browser}")

        options.headless = self.headless
        if self.kiosk:  # not supported on opera driver
            options.add_argument("--kiosk")
        if self.browser == "firefox":
            options.set_preference('dom.webnotifications.enabled', False)
        else:
            options.add_argument(f"user-data-dir={self._profile_path}")
            options.add_argument("--disable-notifications")

        if self.proxy is not None:
            self._set_proxy(options)

        return options

    def _set_proxy(self, options):
        if self.browser == "firefox":
            proxy_address, proxy_port = self.proxy.split(":")
            options.set_preference("network.proxy.type", 1)
            options.set_preference("network.proxy.http", proxy_address)
            options.set_preference("network.proxy.http_port", int(proxy_port))
            options.set_preference("network.proxy.ssl", proxy_address)
            options.set_preference("network.proxy.ssl_port", int(proxy_port))
        else:
            options.add_argument(f"--proxy-server={self.proxy}")

    def load_profile(self):
        local_storage_file = os.path.join(self.driver.profile.path, self._whatsapp_cookies)
        if Path(local_storage_file).exists():
            with open(local_storage_file) as f:
                data = json.loads(f.read())
                self.driver.execute_script("".join(
                    [f'window.localStorage.setItem(\'{k}\', \'{v}\'); '
                     for k, v in data.items()])
                )
            self.refresh()

    def save_profile(self, remove_old=False):
        if self._profile_path.exists():
            return
        driver_profile, local_path = self.driver.profile.path, self._profile_path
        ignore_rule = shutil.ignore_patterns("parent.lock", "lock", ".parentlock")
        os.mkdir(local_path)
        if remove_old:
            try:
                shutil.rmtree(local_path)
            except OSError:
                pass
            shutil.copytree(
                src=os.path.join(driver_profile), dst=local_path,
                ignore=ignore_rule,
            )
        else:
            for item in os.listdir(driver_profile):
                if item in ["parent.lock", "lock", ".parentlock"]:
                    continue
                src, dst = os.path.join(driver_profile, item), local_path
                if os.path.isdir(src):
                    shutil.copytree(src=src, dst=dst,
                                    ignore=ignore_rule)
                else:
                    shutil.copy2(src, dst)

        with open(self._whatsapp_cookies, "w+") as f:
            f.write(json.dumps(self.driver.execute_script("return window.localStorage;")))  # get local storage

    def get(self, url):
        self.driver.get(url)

    def log(self, url=_URL, timeout=15, retries=0):
        self.get(url)

        if self.browser == "firefox":
            self.load_profile()

        while not self.is_logged:
            try:
                WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, self.select_by("main_page", "qr_code"))))
                self.driver.find_element_by_css_selector(self.select_by("main_page"))
                self._logged = True
            except NoSuchElementException:
                self._logged = False
            except (UnexpectedAlertPresentException, TimeoutException) as e:
                if retries == 0:
                    raise RuntimeError("Number of retries exceeded")
                self.retry(self.log, url, retries=retries - 1)

        if self.browser == "firefox":  # and not self._profile_path.exists():
            self.save_profile()

    def send(self, phone, message, timeout=15, retries=0):
        url = f"{self._URL}send?phone={phone}&text={quote(message)}"
        if not self.is_logged:
            self.log()
        try:
            self.get(url)
            send_button = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, self.select_by("send_button"))))  # presence_of_element_located
            time.sleep(.5)
            send_button.click()
            time.sleep(1.5)  # Used to avoid most of the exceptions
        except (ElementNotInteractableException, UnexpectedAlertPresentException, TimeoutException) as e:
            if retries == 0:
                raise RuntimeError("Number of retries exceeded")
            self.retry(self.send, phone, message, retries=retries - 1)

    @staticmethod
    def retry(func, *args, **kwargs):
        func(*args, **kwargs)

    def add_selectors(self, selectors: dict):
        self._SELECTORS.update(selectors)

    def select_by(self, *selectors: str):
        try:
            return ",".join([self._SELECTORS[sel] for sel in selectors])
        except KeyError:
            raise RuntimeError("Unknown selector. If you want to add custom selectors use add_selectors()")

    def maximize_window(self):
        self.driver.maximize_window()

    def refresh(self):
        self.driver.refresh()

    def reload_qr(self):
        self.driver.find_element_by_css_selector(self.select_by("qr_reloader")).click()

    def close(self):
        self.driver.close()

    def quit(self):
        self.driver.quit()

    def screenshot(self, filename):
        self.driver.save_screenshot(filename)
