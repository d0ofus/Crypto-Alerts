import time
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import StaleElementReferenceException

# Inputs 
url = "https://www.tradingview.com/watchlists/44936899/"
section = "KEY FOR TODAY"

# Set up Selenium
options = Options()
options.add_argument('--headless')

options.binary_location = "/tmp/chromium/headless-chromium"
options.add_argument("--no-sandbox")
options.add_argument("--disable-gpu")


driver = None

def setup_driver():
    global driver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(url)
    driver.implicitly_wait(15)
    time.sleep(15)

def get_symbols():
    print("--------- Extracting Symbols from TradingView Watchlist -------------")
    collecting_symbols = False
    filtered_symbols = []
    retry_count = 0

    try:
        # Get all elements in order
        all_elements = driver.find_elements(By.XPATH, "//*")

        # Iterate through all elements in order
        for element in all_elements:
            if element.get_attribute("class") == "title-i4kte_DY toggleable-i4kte_DY apply-overflow-tooltip" \
            and section in element.text:
                print(f"'{section}' section found, starting collection..")
                collecting_symbols = True

            if collecting_symbols:
                if element.get_attribute("class") == "symbol-nNqEjNlw":
                    filtered_symbols.append(element.text)
                
                elif element.get_attribute("class") == "title-i4kte_DY toggleable-i4kte_DY apply-overflow-tooltip" \
                and section not in element.text:
                    collecting_symbols = False

        print(f"Symbols in watchlist: {filtered_symbols}")
        return filtered_symbols
     
    except StaleElementReferenceException:
        print("Encountered a stale element reference; re-fetching elements.") 
        retry_count += 1
        if retry_count <= 3:
            return get_symbols()  # Retry processing
        else:
            print("Reloaded more than 3 times, exiting process")
            return []
    
def close_driver():
    if driver:
        driver.quit()

if __name__ == "__main__":
    setup_driver()
    symbols = get_symbols()
    close_driver()
