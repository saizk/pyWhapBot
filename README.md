![whapbot_logo](https://raw.githubusercontent.com/saizk/pywhapbot/master/images/whapbot.png)
![PyPI version](https://img.shields.io/pypi/v/pywhapbot)

WhatsApp Web API Wrapper for Chrome, Firefox, Opera, Brave and Edge.

## Installation
```Python
pip install pywhapbot
```

## Features
+ Send messages by phone number
+ Store WhatsApp Web sessions in all the browsers. (Edge only available on Windows)
+ Automate the download of Selenium drivers

## Simple Usage
```Python
from pywhapbot import WhapBot
bot = WhapBot("chrome")  # downloads current driver automatically
bot.log()  # optional
bot.send("+34123456789", "Hello world!")  # forces log
bot.quit()
```

## Download specific drivers automatically
```Python
from pywhapbot.install import download_driver
from pywhapbot.utils import get_version

download_driver("firefox", version="0.29.1", root="drivers")
download_driver("opera", version="latest")
download_driver("edge", version="current")

lversion = get_version("brave", "latest")
cversion = get_version("brave", "current")

if cversion < lversion:
    print("You should update your browser to the last version")
```

## More advanced example
```Python
from pywhapbot import WhapBot

whapbot = WhapBot(
    browser="firefox",
    driver_path="geckodriver.exe",
    profile_path="profiles/firefox-profile",
    proxy="169.210.345.10:4567",
    kiosk=True  # kiosk mode (not supported on opera)
)
whapmsgs = [("+34696969420", "Open!"),
            ("+34696942069", "Sourcerer!")]

with whapbot as bot:  # Context manager of selenium webdriver class
    bot.get("https://github.com/saizk")
    # Selenium Webdriver command examples
    bot.driver.set_window_position(210, 210)
    assert len(bot.driver.window_handles) == 1 
    bot.driver.find_element_by_link_text("new window").click()
    bot.driver.switch_to.new_window('tab')
    
    for idx, (phone, message) in enumerate(whapmsgs):
        bot.send(phone, message, timeout=15, retries=5)  # forces log
        bot.screenshot(f"whapbot-{idx}.png")
        print(f"{idx+1}/{len(whapmsgs)} messages sent")    

# bot.quit() called by the context manager
```

## Contribute
Would you like to contribute to this project? Here are a few starters:
- Improve documentation
- Add Testing examples
- Bug hunts and refactor
- Additional features/ More integrations
- Phantom JS support
- Implement default browser functions for Mac 