import json
import os
import logging
import boto3
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains



def get_secret():
    secret_name = os.environ.get("SECRET_NAME", "easytithe/login-creds")
    region_name = (
    os.environ.get("REGION")
    or os.environ.get("AWS_REGION")
    or os.environ.get("AWS_DEFAULT_REGION")
    or "us-east-1"
    )    
    client = boto3.client("secretsmanager", region_name=region_name)
    resp = client.get_secret_value(SecretId=secret_name)
    return json.loads(resp["SecretString"])


def assert_on_attendance_reports(driver, wait):

    WebDriverWait(driver, 30).until(EC.url_contains("/reports/attendance"))

    title_text = ""
    try:
        header_el = WebDriverWait(driver, 5).until(EC.visibility_of_element_located((
            By.XPATH, "//*[self::h1 or self::h2 or contains(@class,'page-title')][contains(., 'Attendance Reports')]"
        )))
        try:
            title_text = header_el.text.strip()
        except Exception:
            title_text = "Attendance Reports"
    except Exception:
        pass

    try:
        wait.until(EC.visibility_of_element_located((
            By.XPATH, "//a[normalize-space()='Sessions']"
        )))
    except Exception:
        pass

    try:
        wait.until(EC.visibility_of_element_located((
            By.XPATH, "//table//th[normalize-space()='Session']"
        )))
    except Exception:
        wait.until(EC.presence_of_element_located((
            By.CSS_SELECTOR, "table"
        )))

    return title_text or "Attendance Reports"


def log_url(driver, logger, msg):
    try:
        u = driver.current_url
        if logger:
            logger.info(f"{msg} | url={u}")
        print(f"[NAV] {msg} | url={u}")
    except Exception:
        pass


def click_attendance_tab(driver, wait, label="Absences", logger=None):

    tab = WebDriverWait(driver, 20).until(EC.presence_of_element_located((
        By.XPATH, f"//a[normalize-space()='{label}']"
    )))
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", tab)
        driver.execute_script("arguments[0].click();", tab)
    except Exception:
        try:
            ActionChains(driver).move_to_element(tab).pause(0.1).click(tab).perform()
        except Exception:
            pass
    try:
        WebDriverWait(driver, 10).until(
            lambda d: d.find_element(
                By.XPATH,
                f"//a[normalize-space()='{label}'][@aria-selected='true' or contains(@class,'active')]",
            )
        )
    except Exception:
        try:
            WebDriverWait(driver, 5).until(EC.url_contains("absences"))
        except Exception:
            pass
    log_url(driver, logger, f"Selected tab '{label}'")

def lambda_handler(event, context):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Ensure writable dirs for Lambda
    os.environ["HOME"] = "/tmp"
    os.environ["XDG_RUNTIME_DIR"] = "/tmp"
    os.environ["XDG_CACHE_HOME"] = "/tmp"
    for p in ["/tmp/chrome-user-data", "/tmp/data-path", "/tmp/cache-path"]:
        os.makedirs(p, exist_ok=True)

    # Paths to packaged binaries (as in example_code.py expectation)
    driver_path = "/var/task/chromedriver"
    binary_path = "/var/task/headless-chromium"
    # Prefer system paths when running in a container image
    if os.path.exists("/usr/bin/chromedriver"):
        driver_path = "/usr/bin/chromedriver"
    if os.path.exists("/usr/bin/chromium"):
        binary_path = "/usr/bin/chromium"
    elif os.path.exists("/usr/bin/google-chrome"):
        binary_path = "/usr/bin/google-chrome"

    options = Options()
    options.binary_location = binary_path
    # Selenium 3-compatible flags similar to example_code.py
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--single-process")
    options.add_argument("--window-size=1280,1024")
    # Use Lambda writable dirs
    options.add_argument("--user-data-dir=/tmp/chrome-user-data")
    options.add_argument("--data-path=/tmp/data-path")
    options.add_argument("--disk-cache-dir=/tmp/cache-path")

    driver = None
    try:
        creds = get_secret()

        # Initialize driver (Selenium 3 style)
        driver = Chrome(executable_path=driver_path, options=options)
        driver.set_page_load_timeout(60)

        # Navigate and log in
        driver.get("https://spotc.easytitheplus.com/user/login")
        wait = WebDriverWait(driver, 20)
        log_url(driver, logger, "Opened login page")

        email_el = wait.until(EC.element_to_be_clickable((By.NAME, "username")))
        pwd_el = wait.until(EC.presence_of_element_located((By.NAME, "password")))
        email_el.clear(); email_el.send_keys(creds["username"])  # email/username from secret
        pwd_el.clear(); pwd_el.send_keys(creds["password"])
        driver.find_element(By.TAG_NAME, "form").submit()

        # Wait for redirect away from login page
        WebDriverWait(driver, 20).until(lambda d: "/user/login" not in d.current_url)
        log_url(driver, logger, "After login redirect")
        try:
            reports_container = wait.until(EC.presence_of_element_located((
                By.CSS_SELECTOR, "#main-collapsed-theReports"
            )))
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", reports_container)

            try:
                hover_target = reports_container.find_element(By.CSS_SELECTOR, "a,button,[role='button'], .collapse-title, .link")
            except Exception:
                hover_target = reports_container

            try:
                ActionChains(driver).move_to_element(hover_target).pause(0.2).perform()
            except Exception:
                driver.execute_script(
                    "var ev=new MouseEvent('mouseover',{bubbles:true}); arguments[0].dispatchEvent(ev);",
                    hover_target,
                )

            try:
                WebDriverWait(driver, 5).until(EC.visibility_of_element_located((
                    By.CSS_SELECTOR, "#main-collapsed-theReports .collapse-box-items"
                )))
            except Exception:
                pass

            attendance_link = WebDriverWait(driver, 10).until(EC.presence_of_element_located((
                By.CSS_SELECTOR,
                "#main-collapsed-theReports > div > div.collapse-box-items.sub-side-links.sub-link-theAttendanceReports.unity-color > a, "
                "#main-collapsed-theReports .sub-link-theAttendanceReports a, "
                "a[href*='/reports/attendance']"
            )))
            try:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", attendance_link)
                driver.execute_script("arguments[0].click();", attendance_link)
            except Exception:
                attendance_link.click()
            wait.until(EC.url_contains("/reports/attendance"))
            log_url(driver, logger, "Attendance reports (menu click)")
        except Exception as e:
            driver.get("https://spotc.easytitheplus.com/reports/attendance")
            WebDriverWait(driver, 20).until(EC.url_contains("/reports/attendance"))
            print("Got here thru exception: ", str(e))
            log_url(driver, logger, "Attendance reports (direct nav)")
        
        # Strong confirmation we reached the Attendance Reports page
        title = assert_on_attendance_reports(driver, wait)
        logger.info(f"Confirmed Attendance Reports page | url={driver.current_url} | header={title}")
        try:
            click_attendance_tab(driver, wait, "Absences", logger)
        except Exception:
            pass
        
        success = "/user/login" not in driver.current_url

        body = {
            "message": "✅ Login successful!" if success else "⚠️ Login may have failed.",
            "current_url": driver.current_url,
        }
        return {"statusCode": 200 if success else 400, "body": json.dumps(body)}

    except Exception as e:
        logger.exception("Login flow failed")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
    finally:
        try:
            if driver:
                driver.quit()
        except Exception:
            pass
