import logging
import time

from playsound import playsound
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait

logging.basicConfig(
    format='%(asctime)s\t%(levelname)s\t%(message)s',
    level=logging.INFO,
)


class WebDriver:
    def __init__(self):
        self._driver: webdriver.Chrome
        self._implicit_wait_time = 400

    def __enter__(self) -> webdriver.Chrome:
        logging.info("Opening browser")
        # prevent selenium detection
        options = webdriver.ChromeOptions()
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        # let selenium manager get chromedriver
        self._driver = webdriver.Chrome(options=options)
        self._driver.implicitly_wait(self._implicit_wait_time)  # seconds
        self._driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self._driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.53 Safari/537.36'})
        return self._driver

    def __exit__(self, exc_type, exc_value, exc_tb):
        logging.info("Closing browser")
        self._driver.quit()


class BerlinBot:
    def __init__(self, citizenship, applicants, family, appointment_type, reason_category, reason_type,
                 citizenship_family=None):
        # individual parameters
        self.citizenship = citizenship
        self.applicants = applicants
        self.family = family
        self.citizenship_family = citizenship_family
        self.appointment_type = appointment_type
        self.reason_category = reason_category
        self.reason_type = reason_type
        # max timeout
        self.timeout = 400
        # time before resubmitting form
        self.cycle_time = 20
        self._error_message = """Für die gewählte Dienstleistung sind aktuell keine Termine frei! Bitte"""

    def proceed(self, driver):
        # wait for proceed button to be clickable
        WebDriverWait(driver, self.timeout).until(
            EC.invisibility_of_element_located((By.CLASS_NAME, "loading")))
        # press button to proceed
        driver.find_element(By.ID, 'applicationForm:managedForm:proceed').click()
        # wait for loading to finish before continuing
        WebDriverWait(driver, self.timeout).until(
            EC.invisibility_of_element_located((By.CLASS_NAME, "loading")))

    @staticmethod
    def visit_start_page(driver: webdriver.Chrome):
        logging.info("Visiting start page")
        driver.get("https://otv.verwalt-berlin.de/ams/TerminBuchen")
        driver.find_element(By.XPATH, "//a[text()='Termin buchen']").click()

    def tick_off_agreement(self, driver: webdriver.Chrome):
        logging.info("Ticking off agreement")
        driver.find_element(By.ID, 'xi-cb-1').click()
        self.proceed(driver)

    def fill_form(self, driver: webdriver.Chrome):
        logging.info("Filling out form")
        # select citizenship
        Select(driver.find_element(By.ID, 'xi-sel-400')).select_by_visible_text(self.citizenship)
        # select number of applicants
        Select(driver.find_element(By.ID, 'xi-sel-422')).select_by_visible_text(self.applicants)
        # select family member
        Select(driver.find_element(By.ID, 'xi-sel-427')).select_by_visible_text(self.family)

        if self.family == "ja":
            Select(driver.find_element(By.ID, 'xi-sel-428')).select_by_visible_text(self.citizenship_family)

        time.sleep(2)

        # select appointment type
        driver.find_element(By.XPATH, f'//*[@id="xi-div-30"]/div[{self.appointment_type}]').click()
        time.sleep(2)

        # select reason category
        driver.find_element(By.XPATH, f'//*[@id="inner-436-0-1"]/div/div[{self.reason_category}]').click()
        time.sleep(2)

        # select reason type
        driver.find_element(By.XPATH, f'//*[@id="inner-436-0-1"]/div/div[2]/div/div[{self.reason_type}]/label').click()
        time.sleep(2)

        # submit form
        self.proceed(driver)

    def _is_success(self, driver):
        terminauswahl = driver.find_element(By.XPATH,
                                            '//*[@id="main"]/div[2]/div[4]/div[2]/div/div[1]/ul/li[3]')

        if self._error_message not in driver.page_source and 'antcl_active' in terminauswahl.get_attribute(
                'class').split():
            logging.info("!!!SUCCESS - do not close the window!!!!")
            while True:
                playsound('alarm.wav')
                time.sleep(15)

    def cycle(self):
        with WebDriver() as driver:
            self.visit_start_page(driver)
            self.tick_off_agreement(driver)
            self.fill_form(driver)

            # retry submitting form
            for _ in range(10):
                # are appointments available?
                self._is_success(driver=driver)
                time.sleep(self.cycle_time)

                logging.info("Resubmitting form")
                self.proceed(driver)

    def start(self):
        while True:
            logging.info("Starting new cycle")
            self.cycle()
            time.sleep(self.cycle_time)


if __name__ == "__main__":
    citizenship = "Indien"
    applicants = "eine Person"
    family = "nein"
    appointment_type = 1
    reason_category = 1
    reason_type = 5

    BerlinBot(citizenship=citizenship, applicants=applicants, family=family, appointment_type=appointment_type,
              reason_category=reason_category,
              reason_type=reason_type).start()
