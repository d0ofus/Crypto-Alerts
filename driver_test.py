from selenium.webdriver import Chrome, ChromeOptions

options = ChromeOptions()
options.add_argument('--headless')
options.add_argument('--disable-gpu')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

driver = Chrome(options=options)

driver.get('https://google.com')

print(driver.page_source)

driver.quit()