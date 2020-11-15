from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.select import Select

from flask import Flask, jsonify, abort, make_response, request
from flask_cors import CORS

from bs4 import BeautifulSoup

import csv
import time
import logging
import base64
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta

class Gym:
    def __init__(self):
        self.name = ''
        self.courts = []
        self.address = ''

    def getName(self):
        return self.name

    def setName(self, name):
        self.name = name

class Court:
    def __init__(self):
        self.name = ''
        self.bookings = []

    def getName(self):
        return self.name

    def getBooking(self):
        return self.bookings

    def setName(self, name):
        self.name = name

    def addBooking(self, booking):
        self.bookings.append(booking)

class Booking:
    def __init__(self):
        self.date = ''
        self.booked = False

    def getDate(self):
        return self.date

    def setDate(self, year, month, day):
        self.date = year + '/' + month + '/' + day

    def setBooked(self, booked):
        self.booked = booked

LOGIN_URL = 'https://reserve.opas.jp/osakashi/menu/Login.cgi'
ID1 = '27041850'
PASS1 = 'OPASyskt1829'
gym_list = {}
weekly_htmls = []

chrome_path = '/usr/bin/chromium-browser'
chromedriver_path = '/usr/lib/chromium/chromedriver'
options = Options()
# options.binary_location = '/usr/bin/chromium-browser'
options.add_argument('--headless')
options.add_argument('--disable-gpu')
options.add_argument('--no-sandbox')
options.add_argument('--window-size=1200x600')
# options.add_argument("user-data-dir=/Users/<ユーザー名>/Library/Application Support/Google/Chrome") 

"""
user defined functions
"""
def select_date(driver, y, m, d):
    opt_year_obj = Select(driver.find_element_by_id("optYear"))
    opt_year_obj.select_by_value("{}".format(y))
    opt_month_obj = Select(driver.find_element_by_id("optMonth"))
    opt_month_obj.select_by_value("{:02d}".format(m))
    opt_day_obj = Select(driver.find_element_by_id("optDay"))
    opt_day_obj.select_by_value("{:02d}".format(d))

api = Flask(__name__)
CORS(api)

@api.route('/book', methods=['POST'])
def book_gym(using_selenium):
    try:
        if using_selenium:
            # driver = webdriver.Chrome(chromedriver_path, options=options)
            driver = webdriver.Chrome(options=options)
            driver.get(LOGIN_URL)

            """
            # ログインバージョン
            # ログイン
            riyosha_code = driver.find_element_by_name("txtRiyoshaCode")
            riyosha_code.send_keys(ID1)
            riyosha_code = driver.find_element_by_name("txtPassWord")
            riyosha_code.send_keys(PASS1)
            login_btn_p = driver.find_element_by_class_name("loginbtn")
            login_btn_p.find_element_by_tag_name("img").click()

            # 空き照会・予約
            first_menu_button = driver.find_element_by_xpath(
                "//ul[@class='menu_buttons'][1]")
            first_menu_button.find_element_by_xpath(
                "//ul[@class='menu_buttons'][1]/li[1]/a[@class='bgpng']").click()
            """

            # 未ログインバージョン
            # 空き照会・予約
            driver.find_element_by_xpath("//p[@class='menu_button'][1]/a/img").click()

            # 利用目的から絞り込む
            driver.find_element_by_xpath(
                "//div[@id='mmaincolumn']/div/table/tbody/tr[2]").click()

            # 利用目的選択（大分類選択）：バドミントン
            driver.find_element_by_xpath(
                "//div[@id='mmaincolumn']/div/table/tbody/tr[4]").click()

            # 利用目的選択（小分類選択）：バドミントン
            driver.find_element_by_xpath(
                "//div[@id='mmaincolumn']/div/table/tbody/tr[2]").click()

            # 施設絞り込み（場所選択）
            # 全て選択する
            driver.find_element_by_xpath(
                "//div[@id='mmaincolumn']/div[@class='tablebox']/div[@class='btncenter']/a[1]/img").click()

            # 次に進む
            driver.find_element_by_xpath(
                "//div[@id='fmaincolumn']/div[@id='pagerbox']/a[2]").click()

            # ------------------------
            # 翌月の月初（第1週）
            # ------------------------
            # 予約対象区分選択
            today = date.today()
            first_week = today + relativedelta(months=1)
            first_week = first_week.replace(day=1)
            select_date(driver, first_week.year, first_week.month, first_week.day)

            # 表示ボタン
            driver.find_element_by_xpath(
                "//table[@class='none_style']/tbody/tr/td[3]").click()

            # 予約対象区分選択（日付選択後）
            inner_html = driver.find_element_by_xpath(
                "//div[@id='mmaincolumn']/div[@class='tablebox']").get_attribute('innerHTML')
            # weekly_htmls.append(inner_html)

            # ------------------------
            # 翌月の月初の翌週（第2週）
            # ------------------------
            # 予約対象区分選択
            second_week = first_week + relativedelta(weeks=+1)
            select_date(driver, second_week.year, second_week.month, second_week.day)

            # 表示ボタン
            driver.find_element_by_xpath(
                "//table[@class='none_style']/tbody/tr/td[3]").click()

            # 予約対象区分選択（日付選択後）
            inner_html = driver.find_element_by_xpath(
                "//div[@id='mmaincolumn']/div[@class='tablebox']").get_attribute('innerHTML')
            weekly_htmls.append(inner_html)

            # ------------------------
            # 翌月の月初の翌週（第3週）
            # ------------------------
            # 予約対象区分選択
            third_week = second_week + relativedelta(weeks=+1)
            select_date(driver, third_week.year, third_week.month, third_week.day)

            # 表示ボタン
            driver.find_element_by_xpath(
                "//table[@class='none_style']/tbody/tr/td[3]").click()

            # 予約対象区分選択（日付選択後）
            inner_html = driver.find_element_by_xpath(
                "//div[@id='mmaincolumn']/div[@class='tablebox']").get_attribute('innerHTML')
            weekly_htmls.append(inner_html)

            # ------------------------
            # 翌月の月初の翌週（第4週）
            # ------------------------
            # 予約対象区分選択
            fourth_week = third_week + relativedelta(weeks=+1)
            select_date(driver, fourth_week.year, fourth_week.month, fourth_week.day)

            # 表示ボタン
            driver.find_element_by_xpath(
                "//table[@class='none_style']/tbody/tr/td[3]").click()

            # 予約対象区分選択（日付選択後）
            inner_html = driver.find_element_by_xpath(
                "//div[@id='mmaincolumn']/div[@class='tablebox']").get_attribute('innerHTML')
            weekly_htmls.append(inner_html)

            # ------------------------
            # 翌月の月初の翌週（第5週）
            # ------------------------
            # 予約対象区分選択
            fifth_week = fourth_week + relativedelta(weeks=+1)
            select_date(driver, fifth_week.year, fifth_week.month, fifth_week.day)

            # 表示ボタン
            driver.find_element_by_xpath(
                "//table[@class='none_style']/tbody/tr/td[3]").click()

            # 予約対象区分選択（日付選択後）
            inner_html = driver.find_element_by_xpath(
                "//div[@id='mmaincolumn']/div[@class='tablebox']").get_attribute('innerHTML')
            weekly_htmls.append(inner_html)

            inner_html = ''.join(weekly_htmls)
        else:
            # open local file instead of using Selenium
            with open('./inner.html', 'r', encoding='utf-8') as f:
                inner_html = f.read()

        soup = BeautifulSoup(inner_html, "html.parser")
        facilities_boxes = soup.find_all(class_='facilitiesbox')

        nothing = True
        print('【18:00～21:00】')
        for facilities_box in facilities_boxes: # at most 5
            trs = facilities_box.tbody.find_all("tr", recursive=False)
            for tr in trs: # at most 28
                gym_name = tr.td.find(style="float:left")
                gym = Gym()
                gym.setName(gym_name.text)
                court_names = tr.td.find_all(style="float:left; font-weight:bold;")
                for court_name in court_names: # at most 2
                    court = Court()
                    court.setName(court_name.text)
                    gym_dates = tr.td.table.tbody.select("tr:nth-of-type(2) > th > p.day")
                    date_list = []
                    for gym_date in gym_dates: # at most 7
                        # booking = Booking()
                        month_and_day = gym_date.text.replace('\n', '').replace('日', '').split('月')
                        # booking.setDate(year, month_and_day[0], "{:02d}".format(int(month_and_day[1])))
                        date_list.append(month_and_day[0] + "/" + "{:02d}".format(int(month_and_day[1])))
                    # mornings = tr.td.table.tbody.select("tr:nth-of-type(3) > td")
                    # afternoons = tr.td.table.tbody.select("tr:nth-of-type(4) > td")
                    # evenings = tr.td.table.tbody.select("tr:nth-of-type(5) > td")
                    nights = tr.td.table.tbody.select("tr:nth-of-type(6) > td")
                    for i, night in enumerate(nights): # at most 7
                        if "facmdstime" not in night.get("class") and 'maru' in night.find("img").get("src"):
                            print('[空]' + ' ' + date_list[i] + ' ' + gym.getName() + '-' + court.getName())
                            noting = False
                    date_list.clear()
                    # logging.warning('debug: {}'.format(mornings[1].find("img").get("src")))

            # time.sleep(5)

    finally:
        if using_selenium:
            driver.quit()
        if nothing:
            print("空きはありませんでした")

"""
Use the Chrome DriverService.
https://chromedriver.chromium.org/getting-started
"""
# s = Service(executable_path=chromedriver_path)
# s.start()
# second_week = webdriver.Remote(
#     s.service_url,
#     desired_capabilities=options.to_capabilities()
# )
# second_week.get('https://www.google.com')
# print(second_week.title)
# second_week.quit()

@api.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

if __name__ == '__main__':
    # WARNING レベル以上のログを出力する
    # (low)DEBUG, INFO, WARNING, ERROR, CRITICAL(high)
    logging.basicConfig(level=logging.WARNING,
                        format='%(levelname)s: %(message)s')
    # CRITICAL レベル以下のログを出力しない（＝実質なし）
    # logging.disable(logging.CRITICAL)

    # debug=True にするとホットリロード
    # api.run(debug=True, host='0.0.0.0', port=3000)

    # True: Selenium, False: Local file(debug)
    book_gym(True)

