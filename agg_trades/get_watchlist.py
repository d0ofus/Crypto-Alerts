import time

# from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver import Chrome, ChromeOptions
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import StaleElementReferenceException

# Inputs 
url = "https://www.tradingview.com/watchlists/44936899/"
section = "KEY FOR TODAY"

# Set up Selenium
# options = Options()
options = ChromeOptions()

options.add_argument("--headless")
options.add_argument('--disable-gpu')
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = None

def setup_driver():
    global driver
    try:
        print("--------- Starting up selenium driver -------------")
        driver = Chrome(options=options)
        # driver = webdriver.Chrome(options=options)
        driver.get(url)
        driver.implicitly_wait(30)
        time.sleep(30)

        # Check if page loaded correctly
        page_title = driver.title
        print(f"Page loaded: {page_title}")

        # Check if the driver is not None
        if driver is None:
            raise Exception("WebDriver initialization failed. Driver is None.")

    except Exception as e:
        print(f"Error starting ChromeDriver: {e}")
        driver = None

def get_symbols():
    print("--------- Extracting Symbols from TradingView Watchlist -------------")
    collecting_symbols = False
    filtered_symbols = []
    retry_count = 0

    if driver is None:
        print("Driver is not initialized. Exiting symbol extraction.")
        return []

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
