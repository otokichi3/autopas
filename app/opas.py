import sys
import os
import io
import csv
import logging
import base64
import datetime
import locale
from dateutil.relativedelta import relativedelta
from typing import List

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.select import Select
from flask import Flask, jsonify, abort, make_response, request
from flask_cors import CORS
from bs4 import BeautifulSoup

from line_notify_bot import LINENotifyBot
from gym import Court, Gym
import decorator
import common

locale.setlocale(locale.LC_TIME, 'Japanese_Japan.932')

OPAS_ID = os.environ['opas_id']
OPAS_PASSWORD = os.environ['opas_password']
LINE_TOKEN = os.environ['line_token']
CAPTCHA_KEY = os.environ['captcha_key']
COURT_NUM = 37

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


class Opas:
    timeframes = []

    login_url = 'https://reserve.opas.jp/osakashi/menu/Login.cgi'

    chrome_path = '/usr/bin/chromium-browser'
    chromedriver_path = '/usr/lib/chromium/chromedriver'
    options = Options()
    # options.binary_location = '/usr/bin/chromium-browser'
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--window-size=1200x600')
    # options.add_argument("user-data-dir=/Users/<ユーザー名>/Library/Application Support/Google/Chrome")

    cookie_name = 'JSESSIONID'
    cookie_value = ''
    cookie_domain = 'reserve.opas.jp'

    @decorator.timer
    def init_driver(self):
        """Seleniumドライバを初期化する"""
        # driver = webdriver.Chrome(chromedriver_path, options=options)
        self.__driver = webdriver.Chrome(options=self.options)
        self.__driver.get(self.login_url)

        """
        TODO
        session を requests で取得してから Selenium を使えば
        ログイン以降の画面（例えばカテゴリ選択後の画面）にいきなり遷移出来るかも
        self.__driver.add_cookie(
            {
                'name': self.cookie_name,
                'value': self.cookie_value,
                'domain': 'example.com'
            }
        )
        """

    @decorator.timer
    def login(self, id: str, password: str):
        """OPASにログインする"""
        self.__driver.find_element_by_name("txtRiyoshaCode").send_keys(id)
        self.__driver.find_element_by_name("txtPassWord").send_keys(password)
        x_login_btn = "//p[@class='login_btn']/img"
        self.__driver.find_element_by_xpath(x_login_btn).click()

    @decorator.timer
    def select_category(self, is_login: bool):
        """カテゴリーを選択する"""
        if is_login:
            # 空き照会・予約
            x_inquire_btn_login = "//ul[@class='menu_buttons'][1]/li[1]/a[@class='bgpng']"
            self.__driver.find_element_by_xpath(x_inquire_btn_login).click()
        else:
            x_inquire_btn = "//p[@class='menu_button'][1]/a/img"
            self.__driver.find_element_by_xpath(x_inquire_btn).click()

        # 1. 利用目的から絞り込む
        # 2. 利用目的選択（大分類選択）：バドミントン
        # 3. 利用目的選択（小分類選択）：バドミントン
        xpaths = [
            "//div[@id='mmaincolumn']/div/table/tbody/tr[2]",
            "//div[@id='mmaincolumn']/div/table/tbody/tr[4]",
            "//div[@id='mmaincolumn']/div/table/tbody/tr[2]",
        ]
        for xpath in xpaths:
            self.__driver.find_element_by_xpath(xpath).click()

    @decorator.timer
    def select_gym(self, is_all: bool = False, rec_nums: List[str] = []):
        """ジムを選択する"""
        if is_all:
            for i in range(COURT_NUM):
                self.__driver.find_element_by_id("i_record{}".format(i)).click()
            x_next = "//div[@id='fmaincolumn']/div[@id='pagerbox']/a[2]"
            self.__driver.find_element_by_xpath(x_next).click()
            return

        if len(rec_nums) == 0:
            for rec_num in rec_nums:
                print(rec_num)

    @decorator.timer
    def get_month_html(self) -> str:
        """一月分のHTMLを取得する"""
        # 翌月の週ごとに HTML を取得する
        weekly_htmls = []
        x_btn_display = "//table[@class='none_style']/tbody/tr/td[3]"
        x_category_select = "//div[@id='mmaincolumn']/div[@class='tablebox']"
        today = datetime.date.today()
        first_week = today + relativedelta(months=2)
        first_week = first_week.replace(day=1)
        for i in range(5):
            target_week = first_week + relativedelta(weeks=+i)
            self.select_date(target_week.year, target_week.month, target_week.day)
            self.__driver.find_element_by_xpath(x_btn_display).click()
            inner_html = self.__driver.find_element_by_xpath(x_category_select).get_attribute('innerHTML')
            weekly_htmls.append(inner_html)

        # 5週分の HTML を結合して返す
        joined = ''.join(weekly_htmls)
        self.__driver.quit()

        return joined

    @decorator.timer
    def select_date(self, y, m, d):
        """年月日を選択する"""
        year = self.__driver.find_element_by_id("optYear")
        month = self.__driver.find_element_by_id("optMonth")
        day = self.__driver.find_element_by_id("optDay")
        Select(year).select_by_value("{}".format(y))
        Select(month).select_by_value("{:02d}".format(m))
        Select(day).select_by_value("{:02d}".format(d))
        self.year = y
        self.month = m
        self.day = d

    @decorator.timer
    def get_vacant_list(self, html) -> List[List[str]]:
        """空きリストを取得する"""
        all_vacants = []
        # morning_vacants = []
        afternoon_vacants = []
        evening_vacants = []
        night_vacants = []
        soup = BeautifulSoup(html, "html.parser")
        trs = soup.select('table.facilitiesbox > tbody > tr')

        for tr in trs:  # at most 28
            gym_name = tr.td.find(style="float:left")
            court_names = tr.td.find_all(style="float:left; font-weight:bold;")
            for court_name in court_names:  # at most 2
                gym_dates = tr.td.table.tbody.select("tr:nth-of-type(2) > th > p.day")
                date_list = []
                for gym_date in gym_dates:  # at most 7
                    month_and_day = gym_date.text.replace('\n', '').replace('日', '').split('月')
                    date = datetime.date(2020, int(month_and_day[0]), int(month_and_day[1]))
                    date_list.append(date)
                # 3:朝、4:昼、5:夕方、6:夜
                # mornings = tr.td.table.tbody.select("tr:nth-of-type(3) > td")
                # for i, morning in enumerate(mornings):  # at most 7
                #     night_class = morning.get("class")
                #     if "facmdstime" in night_class:
                #         timeframe = morning.text
                #         self.timeframes.append(timeframe)
                #     else:
                #         is_maru_in = 'maru' in morning.find("img").get("src")
                #         is_yoyaku_mark = '予' in morning.text or 'yo.png' in morning.find("img").get("src")
                #         if is_maru_in or is_yoyaku_mark:
                #             vacant = [date_list[i-1].strftime('%m/%d(%a)'), gym_name.text, court_name.text, is_yoyaku_mark]
                #             morning_vacants.append(vacant)
                afternoons = tr.td.table.tbody.select("tr:nth-of-type(4) > td")
                for i, afternoon in enumerate(afternoons):  # at most 7
                    night_class = afternoon.get("class")
                    if "facmdstime" in night_class:
                        timeframe = afternoon.text
                        self.timeframes.append(timeframe)
                    else:
                        is_maru_in = 'maru' in afternoon.find("img").get("src")
                        is_yoyaku_mark = '予' in afternoon.text or 'yo.png' in afternoon.find("img").get("src")
                        if is_maru_in or is_yoyaku_mark:
                            vacant = [date_list[i-1].strftime('%m/%d(%a)'), gym_name.text, court_name.text, is_yoyaku_mark]
                            afternoon_vacants.append(vacant)
                evenings = tr.td.table.tbody.select("tr:nth-of-type(5) > td")
                for i, evening in enumerate(evenings):  # at most 7
                    night_class = evening.get("class")
                    if "facmdstime" in night_class:
                        timeframe = evening.text
                        self.timeframes.append(timeframe)
                    else:
                        is_maru_in = 'maru' in evening.find("img").get("src")
                        is_yoyaku_mark = '予' in evening.text or 'yo.png' in evening.find("img").get("src")
                        if is_maru_in or is_yoyaku_mark:
                            vacant = [date_list[i-1].strftime('%m/%d(%a)'), gym_name.text, court_name.text, is_yoyaku_mark]
                            evening_vacants.append(vacant)
                nights = tr.td.table.tbody.select("tr:nth-of-type(6) > td")
                for i, night in enumerate(nights):  # at most 7
                    night_class = night.get("class")
                    if "facmdstime" in night_class:
                        timeframe = night.text
                        self.timeframes.append(timeframe)
                    else:
                        is_maru_in = 'maru' in night.find("img").get("src")
                        is_yoyaku_mark = '予' in night.text or 'yo.png' in night.find("img").get("src")
                        if is_maru_in or is_yoyaku_mark:
                            vacant = [date_list[i-1].strftime('%m/%d(%a)'), gym_name.text, court_name.text, is_yoyaku_mark]
                            night_vacants.append(vacant)
                date_list.clear()

        # all_vacants.append(morning_vacants)
        all_vacants.append(afternoon_vacants)
        all_vacants.append(evening_vacants)
        all_vacants.append(night_vacants)

        return all_vacants

    @decorator.timer
    def create_message_from_list(self, all_vacants: List[List[List[str]]]) -> str:
        """空きリストからLINEメッセージを作成する"""
        message = ""
        for i, vacant_list in enumerate(all_vacants):
            message += "時間帯{}\n".format(i+1)
            if len(vacant_list) > 0:
                for vacant in vacant_list:
                    if vacant.pop(3):
                        vacant.append(" (予)")
                    message += '  ' + ' '.join(vacant) + '\n'
                message = common.remove_redundunt(message)
                message_len = len(message)
                message = message[0:message_len]
            else:
                message += '  なし\n'

        return message

    @decorator.timer
    def send_line(self, message: str):
        """LINEを送る"""
        bot = LINENotifyBot(access_token=LINE_TOKEN)
        bot.send(message=message)


api = Flask(__name__)
CORS(api)


@api.route('/vacants', methods=['GET'])
def get_vacant():
    """空きを取得する"""
    opas = Opas()
    opas.init_driver()
    opas.select_category(is_login=False)
    opas.select_gym(is_all=True)
    html = opas.get_month_html()
    vacant_list = opas.get_vacant_list(html)

    message = opas.create_message_from_list(vacant_list)
    opas.send_line(message)
    return jsonify({
        'status': 'OK',
        'data': message
    })


@api.route('/reserve', methods=['GET'])
def reserve():
    """予約する"""
    opas = Opas()
    opas.init_driver()
    opas.login(OPAS_ID, OPAS_PASSWORD)
    opas.select_category(is_login=True)
    opas.select_gym(is_all=False)

    # 日付選択
    # TODO 希望の年月日を選択する
    opas.select_date(2020, 12, 9)
    x_btn_display = "//table[@class='none_style']/tbody/tr/td[3]"
    driver.find_element_by_xpath(x_btn_display).click()

    # ポップアップ OK
    x_popup_ok = "//input[@id='popup_ok']"
    driver.find_element_by_xpath(x_popup_ok).click()

    # 予約対象区分選択（日付選択後）
    # テキトーに最初のやつ選択
    # TODO 希望の日時を指定する
    driver.find_element_by_id("i_record1").click()

    # 次に進む
    driver.find_element_by_xpath("//div[@id='pagerbox']/a[2]").click()

    # 申込内容入力
    driver.find_element_by_id("numberOfRiyosha").send_keys('22')

    # 次に進む
    driver.find_element_by_xpath("//div[@id='pagerbox']/a[2]").click()

    # 利用規約
    driver.find_element_by_id("img_chkRiyoKiyaku").click()

    # kaptcha 取得
    x_kaptcha_img = "//div[@class='sub_box']/div[2]/p/img[1]"
    kaptcha = driver.find_element_by_xpath(
        x_kaptcha_img).screenshot_as_png
    with open('./kaptcha.png', 'wb') as f:
        f.write(kaptcha)

    url = "http://2captcha.com/in.php"
    req_data = {
        'key': CAPTCHA_KEY,
        'method': 'base64',
        'body': base64.b64encode(kaptcha),
        'lang': 'ja',
        'numeric': 4,
        'min_len': 5,
        'max_len': 5,
        'language': 2,
    }
    res = requests.post(url, req_data)
    if res.text[0:2] != 'OK':
        quit('Service error. Error code:' + res.text)
    captcha_id = res.text[3:]
    time.sleep(3)  # 解析が終わるまで待つ
    res_url = "https://2captcha.com/res.php?key=" + \
        CAPTCHA_KEY + "&action=get&id=" + captcha_id
    res = requests.get(res_url)
    if res.status_code == 200 and res.text[0:2] == 'OK':
        kaptcha_txt = res.text[3:]
        driver.find_element_by_name("txtKaptcha").send_keys(kaptcha_txt)
        # 確定
        x_fix_btn = "//div[@class='centered-paranemic-ul-div']/ul/li/a"
        driver.find_element_by_xpath(x_fix_btn).click()
        # OK
        driver.find_element_by_xpath(x_popup_ok).click()
        time.sleep(5)  # 余韻に浸る
    return ''


@api.route('/debug', methods=['GET'])
def debug_get_vacant():
    """空き取得をデバッグする"""
    """Seleniumを使う代わりにローカルのHTMLファイルから読み込む"""
    opas = Opas()
    path = './debug.html'
    with open(path) as f:
        html = f.read()
    vacant_list = opas.get_vacant_list(html)
    message = opas.create_message_from_list(vacant_list)
    logging.info('debug: {}'.format(message))

    return message


@api.errorhandler(404)
def not_found(error):
    """404の時のページ"""
    return make_response(jsonify({'error': 'Not found'}), 404)


if __name__ == '__main__':
    # (low)DEBUG, INFO, WARNING, ERROR, CRITICAL(high)
    logging.basicConfig(level=logging.INFO,
                        format='%(levelname)s: %(message)s')
    # CRITICAL レベル以下のログを出力しない（＝実質なし）
    # logging.disable(logging.CRITICAL)
    # logging.info('debug: {}'.format())

    # debug=True にするとホットリロード
    api.run(debug=True, host='0.0.0.0', port=3000)
