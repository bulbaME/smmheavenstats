from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
import yaml
from datetime import datetime
import time
from email_getter import get_mail_code

URL = 'https://smm-heaven.net/admin/'
URL_USERS = 'https://smm-heaven.net/admin/users?sort=lastlogin-desc&'
URL_PAYMENTS = 'https://smm-heaven.net/admin/payments?'
ADMIN_CRED = yaml.safe_load(open('credentials.yaml'))['SMMHEAVEN']['ADMIN']
LAST_UPDATE = datetime.timestamp(datetime.strptime(open('lastupdate.time').readline().strip(), '%Y-%m-%d %H:%M:%S'))
MAX_WAIT_TIME = 30

def get_admin_hash() -> str | None:
    try:
        fr = open('admin.hash')
        s = fr.readline()
        fr.close()
        
        return s
    except BaseException:
        return None

def set_admin_hash(h: str):
    fw = open('admin.hash', 'w')
    fw.write(h)
    fw.close()

def get_driver() -> webdriver.Firefox:
    driver_opt = Options()
    # driver_service = Service(executable_path='./geckodriver.exe')
    # driver_opt.headless = True
    driver_opt.add_argument("--window-size=800,800")
    # driver_opt.add_argument("--headless")
    driver_opt.page_load_strategy = 'eager'

    return webdriver.Firefox(options=driver_opt)

def login(driver: webdriver.Firefox):
    form: WebElement = WebDriverWait(driver, MAX_WAIT_TIME).until(
        expected_conditions.presence_of_element_located((By.TAG_NAME, 'form'))
    )
    
    inputs = form.find_elements(by=By.TAG_NAME, value='input')

    inputs = list(filter(lambda x: x.is_displayed(), inputs))

    inputs[0].send_keys(ADMIN_CRED['LOGIN'])
    inputs[1].send_keys(ADMIN_CRED['PSW'])

    print('[logging in]')

    form.submit()

def enter_passcode(driver: webdriver.Firefox, passcode) -> bool:
    form = driver.find_element(by=By.TAG_NAME, value='form')
    inputs = form.find_elements(by=By.TAG_NAME, value='input')

    inputs = list(filter(lambda x: x.is_displayed(), inputs))

    inputs[0].send_keys(passcode)
    form.submit()

    try:
        WebDriverWait(driver, MAX_WAIT_TIME).until(
            expected_conditions.presence_of_element_located((By.TAG_NAME, 'table'))
        )
    except BaseException:
        return False
    
    h = driver.get_cookie('admin_hash')['value']

    set_admin_hash(h)

    return True

def parse_users(driver: webdriver.Firefox) -> list:
    finished = False

    result = []


    page = 1
    while not finished:
        driver.get(URL_USERS + f'page={page}')

        time.sleep(5)

        table: WebElement = WebDriverWait(driver, MAX_WAIT_TIME).until(
            expected_conditions.presence_of_element_located((By.TAG_NAME, 'table'))
        )

        table = table.find_element(by=By.TAG_NAME, value='tbody')
        children = table.find_elements(by=By.XPATH, value='*')

        for c in children:
            elems = c.find_elements(by=By.TAG_NAME, value='td')
            user_id = elems[0].text
            username = elems[1].text
            mail = elems[2].text
            skype = elems[3].find_element(by=By.TAG_NAME, value='a').get_attribute('href')[6:-5]
            date = elems[8].text
            stamp_lastlog = datetime.timestamp(datetime.strptime(date, '%Y-%m-%d %H:%M:%S'))
            date = elems[7].text
            stamp_register = datetime.timestamp(datetime.strptime(date, '%Y-%m-%d %H:%M:%S'))

            if stamp_lastlog < LAST_UPDATE:
                finished = True
                break

            result.append({ 'username': username, 'mail': mail, 'skype': skype, 'timestamp_lastlog': stamp_lastlog, 'timestamp_register': stamp_register, 'user_id': user_id })

        page += 1

    return result

def parse_payments(driver: webdriver.Firefox) -> list:
    finished = False

    result = []


    page = 1
    while not finished:
        driver.get(URL_PAYMENTS + f'page={page}')

        time.sleep(5)

        table: WebElement = WebDriverWait(driver, MAX_WAIT_TIME).until(
            expected_conditions.presence_of_element_located((By.TAG_NAME, 'table'))
        )

        table = table.find_element(by=By.TAG_NAME, value='tbody')
        children = table.find_elements(by=By.XPATH, value='*')

        for c in children:
            elems = c.find_elements(by=By.TAG_NAME, value='td')
            username = elems[1].text
            amount = elems[3].text
            amount = ''.join(list(filter(lambda x: x.isdigit() or x == '.', list(amount))))
            amount = float(amount)
            date = elems[8].text
            date_stamp = datetime.timestamp(datetime.strptime(date, '%Y-%m-%d %H:%M:%S'))

            status = elems[5].text

            if status.strip().lower() != 'completed': continue

            if date_stamp < LAST_UPDATE:
                finished = True
                break

            result.append({ 'username': username, 'amount': amount, 'timestamp': date_stamp })

        page += 1

    return result


def get_updates() -> (list, list):
    global LAST_UPDATE
    driver = get_driver()

    driver.get(URL)
    driver.add_cookie({'name': 'admin_hash', 'value': get_admin_hash()})
    driver.get(URL)

    table = None
    try:
        table: WebElement = WebDriverWait(driver, MAX_WAIT_TIME).until(
            expected_conditions.presence_of_element_located((By.TAG_NAME, 'table'))
        )
    except BaseException:
        pass

    if table == None:
        try:
            login(driver)
            code = get_mail_code()
            enter_passcode(driver, str(code))

            table = WebDriverWait(driver, MAX_WAIT_TIME).until(
                expected_conditions.presence_of_element_located((By.TAG_NAME, 'table'))
            )
        except BaseException:
            driver.quit()
            return []
        
    print('[parsing data]')
    new_time = time.time()

    payments = parse_payments(driver)
    users = parse_users(driver)


    if len(payments) > 0 or len(users) > 0:
        LAST_UPDATE = new_time
    fw = open('lastupdate.time', 'w')
    fw.write(datetime.fromtimestamp(LAST_UPDATE).strftime('%Y-%m-%d %H:%M:%S'))
    fw.close()

    driver.quit()

    return (payments, users)