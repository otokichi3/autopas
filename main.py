import sys
import os
import io
import csv
import json
import logging
import base64
import datetime
import locale
import time
from dateutil.relativedelta import relativedelta
from typing import List, Dict
from itertools import zip_longest

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.select import Select
from flask import Flask, jsonify, abort, make_response, request
from flask_cors import CORS
from memory_profiler import profile
from bs4 import BeautifulSoup

from line_notify_bot import LINENotifyBot
from gym import Court, Gym
import common

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

api = Flask(__name__)
CORS(api)

locale.setlocale(locale.LC_TIME, 'Japanese_Japan.932')

OPAS_ID = os.environ['opas_id']
OPAS_PASSWORD = os.environ['opas_password']
LINE_TOKEN = os.environ['line_token_test']
CAPTCHA_KEY = os.environ['captcha_key']
GYM_COUNT = 28
COURT_COUNT = 37

TIME_MORNING = 0
TIME_AFTERNOON1 = 1
TIME_AFTERNOON2 = 2
TIME_EVENING = 3
TIME_NIGHT1 = 4
TIME_NIGHT2 = 5

"""
時間帯が３つの場合は、9-12=0, 13-16:30=2, 17:30-21=4
時間帯が４つの場合は、9-12=0, 12-15=1, 15-18=3, 18-21=5
"""
timeframe_list = {
    TIME_MORNING: '09:00 ～ 12:00',
    TIME_AFTERNOON1: '12:00 ～ 15:00',
    TIME_AFTERNOON2: '13:00 ～ 16:30',
    TIME_EVENING: '15:00 ～ 18:00',
    TIME_NIGHT1: '17:30 ～ 21:00',
    TIME_NIGHT2: '18:00 ～ 21:00',
}

DATE_FORMAT = '%Y-%m-%d'
DISPLAY_DATE_FORMAT = '%m-%d(%a)'

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# 変数定義部
# Windows
if os.name == "nt":
    chromedriver_path = 'C:\\bin\\chromedriver.exe'
    binary_location = 'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe'
# Mac: Darwin, Linux: Linux
else:
    chromedriver_path = '/usr/lib/chromium/chromedriver'
    binary_location = '/usr/bin/chromium-browser'

morning_row = 'tr:nth-of-type(3) > td'
afternoon_row = 'tr:nth-of-type(4) > td'
evening_row = 'tr:nth-of-type(5) > td'
night_row = 'tr:nth-of-type(6) > td'
morning2_row = 'tr:nth-of-type(10) > td'
afternoon2_row = 'tr:nth-of-type(11) > td'
evening2_row = 'tr:nth-of-type(12) > td'
night2_row = 'tr:nth-of-type(13) > td'

STATUS_RESERVED = 0
STATUS_VACANT = 1
STATUS_TO_BE_VACANT = 2
# END

# TODO Opas クラスが役割多すぎるしコードも多すぎるため簡素化する
# TODO 予約メソッドを作成する
class Opas:
    timeframes = []
    gyms = {}
    gym_name = ''
    day_index = 0

    # TODO 定数を外だしする
    login_url = 'https://reserve.opas.jp/osakashi/menu/Login.cgi'

    options = Options()
    options.binary_location = binary_location
    # options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    # options.add_argument('--window-size=1200x600')

    # TODO Cookie を取得しておいてログイン状態で開始?
    # cookie_name = 'JSESSIONID'
    # cookie_value = ''
    # cookie_domain = 'reserve.opas.jp'

    def init_driver(self):
        """Seleniumドライバを初期化する"""
        self.__driver = webdriver.Chrome(
            chromedriver_path, options=self.options)
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
        return self.__driver

    def login(self, id: str, password: str):
        """OPASにログインする"""
        self.__driver.find_element_by_name("txtRiyoshaCode").send_keys(id)
        self.__driver.find_element_by_name("txtPassWord").send_keys(password)
        x_login_btn = "//p[@class='loginbtn']/a"
        self.__driver.find_element_by_xpath(x_login_btn).click()

    # ログインしている場合はログイン空き照会、そうでない場合はトップの空き照会
    def inquire(self, is_login: bool):
        if is_login:
            x_inquire_btn_login = "//ul[@class='menu_buttons'][1]/li[1]/a[@class='bgpng']"
            self.__driver.find_element_by_xpath(x_inquire_btn_login).click()
        else:
            x_inquire_btn = "//p[@class='menu_button'][1]/a/img"
            self.__driver.find_element_by_xpath(x_inquire_btn).click()

    def select_category(self, is_login: bool):
        """カテゴリーを選択する"""

        # 空き照会・予約
        self.inquire(is_login)

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

    def select_gym(self, is_all: bool = False, rec_nums: List[str] = []):
        """ジムを選択する"""
        if is_all:
            for i in range(COURT_COUNT):
                self.__driver.find_element_by_id("i_record{}".format(i)).click()
            x_next = "//div[@id='fmaincolumn']/div[@id='pagerbox']/a[2]"
            self.__driver.find_element_by_xpath(x_next).click()
            return

        # TODO 体育館を複数選択する
        if len(rec_nums) == 0:
            for rec_num in rec_nums:
                print(rec_num)

    def set_date(self):
        today = datetime.date.today()
        self.first_week = today + relativedelta(months=1)
        self.first_week = self.first_week.replace(day=1)
        self.year = self.first_week.year
        self.month = self.first_week.month
        self.day = self.first_week.day
        
    def get_month_html(self) -> str:
        """一ヶ月分をまとめたHTMLを取得する"""
        # 翌月の週ごとに HTML を取得する
        weekly_htmls = []
        x_btn_display = "//table[@class='none_style']/tbody/tr/td[3]"
        x_category_select = "//div[@id='mmaincolumn']/div[@class='tablebox']"
        # 日数が短い月は4週、とか。
        month_count = 5 if self.month != 2 else 4
        for i in range(month_count):
            target = self.first_week + relativedelta(weeks=+i)
            self.select_date(target.year, target.month, target.day)
            self.__driver.find_element_by_xpath(x_btn_display).click()
            inner_html = self.__driver.find_element_by_xpath(x_category_select).get_attribute('innerHTML')
            weekly_htmls.append(inner_html)

        # 5週分の HTML を結合して返す
        joined = ''.join(weekly_htmls)
        with open('./output.html', 'w') as f:
            f.write(joined)

        self.__driver.quit()

        return joined

    def select_date(self, y, m, d):
        """年月日を選択する"""
        year = self.__driver.find_element_by_id("optYear")
        month = self.__driver.find_element_by_id("optMonth")
        day = self.__driver.find_element_by_id("optDay")
        Select(year).select_by_value("{}".format(y))
        Select(month).select_by_value("{:02d}".format(m))
        Select(day).select_by_value("{:02d}".format(d))

    def set_status(self, tr, base_date, shisetu_name):
        # コート名と日付部分とページ移動部分を除く(-3)
        timeframe_count = len(tr.select("td > table > tbody > tr")) - 3
        mornings = tr.td.table.tbody.select(morning_row)
        afternoons = tr.td.table.tbody.select(afternoon_row)
        if timeframe_count == 3:
            evenings = []
            nights = tr.td.table.tbody.select(evening_row)
            for m, a, n in zip(mornings, afternoons, nights):
                if "facmdstime" in m.get('class'):
                    continue
                else:
                    target_date = base_date + relativedelta(days=self.day_index)
                    date_str = target_date.strftime(DATE_FORMAT)
                    m_status = self.get_vacant_status(m.find("img").get("src") + m.text)
                    a_status = self.get_vacant_status(a.find("img").get("src") + a.text)
                    n_status = self.get_vacant_status(n.find("img").get("src") + n.text)
                    self.gyms[self.gym_name][shisetu_name][TIME_MORNING][date_str] = m_status
                    self.gyms[self.gym_name][shisetu_name][TIME_AFTERNOON2][date_str] = a_status
                    self.gyms[self.gym_name][shisetu_name][TIME_NIGHT1][date_str] = n_status
                    self.day_index += 1
        else:
            evenings = tr.td.table.tbody.select(evening_row)
            nights = tr.td.table.tbody.select(night_row)
            for m, a, e, n in zip(mornings, afternoons, evenings, nights):
                if "facmdstime" in m.get('class'):
                    continue
                else:
                    target_date = base_date + relativedelta(days=self.day_index)
                    date_str = target_date.strftime(DATE_FORMAT)
                    m_status = self.get_vacant_status(m.find("img").get("src") + m.text)
                    a_status = self.get_vacant_status(a.find("img").get("src") + a.text)
                    e_status = self.get_vacant_status(e.find("img").get("src") + e.text)
                    n_status = self.get_vacant_status(n.find("img").get("src") + n.text)
                    self.gyms[self.gym_name][shisetu_name][TIME_MORNING][date_str] = m_status
                    self.gyms[self.gym_name][shisetu_name][TIME_AFTERNOON1][date_str] = a_status
                    self.gyms[self.gym_name][shisetu_name][TIME_EVENING][date_str] = e_status
                    self.gyms[self.gym_name][shisetu_name][TIME_NIGHT2][date_str] = n_status
                    self.day_index += 1

        self.day_index = 0
        
    def set_first_week(self, tr, shisetu, base_date, week_index):
        # 最初(MM/01)は辞書を作成する
        if len(shisetu) == 1:
            shisetu_name = shisetu[0].text
            self.gyms[self.gym_name] = {}
            self.gyms[self.gym_name][shisetu_name] = {
                TIME_MORNING: {},
                TIME_AFTERNOON1: {},
                TIME_AFTERNOON2: {},
                TIME_EVENING: {},
                TIME_NIGHT1: {},
                TIME_NIGHT2: {}
            }
            self.set_status(tr, base_date, shisetu_name)
        else:
            shisetu1_name = shisetu[0].text
            shisetu2_name = shisetu[1].text
            self.gyms[self.gym_name] = {}
            self.gyms[self.gym_name][shisetu1_name] = {
                TIME_MORNING: {},
                TIME_AFTERNOON1: {},
                TIME_AFTERNOON2: {},
                TIME_EVENING: {},
                TIME_NIGHT1: {},
                TIME_NIGHT2: {}
            }
            self.gyms[self.gym_name][shisetu2_name] = {
                TIME_MORNING: {},
                TIME_AFTERNOON1: {},
                TIME_AFTERNOON2: {},
                TIME_EVENING: {},
                TIME_NIGHT1: {},
                TIME_NIGHT2: {}
            }

            self.set_status(tr, base_date, shisetu1_name)
            self.set_status(tr, base_date, shisetu2_name)

    def set_after_first_week(self, tr, shisetu, base_date, week_index):
        if len(shisetu) == 1:
            # TODO 時間帯が3つしかない体育館は上から3つのみのため、
            #      その前提でコードを書いて良いかもしれない。
            #      →switch 文を使い体育館ごとに処理を分ける。
            self.set_status(tr, base_date, shisetu[0].text)
        else:
            self.set_status(tr, base_date, shisetu[0].text)
            self.set_status(tr, base_date, shisetu[1].text)

    def get_vacant_list(self, html):
        """空きリストを取得する"""
        soup = BeautifulSoup(html, "html.parser")
        trs = soup.select('table.facilitiesbox > tbody > tr')

        # TODO class に置き換える
        # TODO 大量の同じコードを一括化する
        self.gyms = {}
        """
        [ジム: [コート: [時間帯: [[日時: 空き状態]]]]
        [string: [string: [int: [[string: bool]]]]
        four-nested dictionary -> to be classed?
        """
        """
        TODO
        - Cognitive Complexity
            https://qiita.com/suzuki_sh/items/824c36b8d53dd2f1efcb
        - Database(Cloud Firestore? Cloud SQL は高い。トランザクションいらんし)
        - Memory footprint
            https://tech.curama.jp/entry/2018/06/22/120000
        """
        for i, tr in enumerate(trs):  # 140
            base_date = datetime.date(self.year, self.month, self.day)
            week_index = int(i/GYM_COUNT)
            base_date += relativedelta(weeks=week_index)
            self.gym_name = tr.select_one(".kaikan_title").text.replace(' ', '')
            shisetu = tr.select(".shisetu_name")  # 配列
            if i < GYM_COUNT:
                self.set_first_week(tr, shisetu, base_date, week_index)
            else:
                # 二週目(MM/08)以降は追加する
                self.set_after_first_week(tr, shisetu, base_date, week_index)

        # jsonに吐き出してデバッグする処理
        d = json.dumps(self.gyms, ensure_ascii=False, indent=4)
        with open('./output.json', 'w') as f:
            f.write(d)

    def get_vacant_status(self, img_src) -> int:
        if 'maru.png' in img_src:
            return STATUS_VACANT
        elif 'yo.png' in img_src or '予' in img_src:
            return STATUS_TO_BE_VACANT
        else:
            return STATUS_RESERVED

    """
    TODO Cognitive Complexity
    """
    def create_message_from_list(self) -> str:
        """空きリストからLINEメッセージを作成する"""
        message = ''
        str_to_append = ''
        for self.gym_name, court in self.gyms.items():
            self.gym_name = self.gym_name.replace(' ', '')
            for court_name, timeframe in court.items():
                i = 0
                for timeframe_num, vacant_status in timeframe.items():
                    if len(str_to_append) == 0:
                        i = 0
                    timeframe_num = int(timeframe_num)
                    # debugのため時間帯が午後２、夕方、夜１、夜２のものだけ表示
                    # TODO 複数時間帯に空きがあり、かつ一つ目の時間帯の空きに土日がない場合、文字列がクリアされる
                    # ゆえに、ジム名とコート名がなくなる。
                    # 暫定対処として追加文字列が空ならインデックスを０にする
                    if timeframe_num in [TIME_AFTERNOON1, TIME_AFTERNOON2, TIME_EVENING, TIME_NIGHT1, TIME_NIGHT2]:
                        if len(vacant_status) > 0 and any(vacant_status.values()):
                            str_to_append = ''
                            if i == 0:
                                str_to_append += '\n'
                                str_to_append += '['+self.gym_name + \
                                    ' ' + court_name + ']'
                                str_to_append += '\n'
                            str_to_append += timeframe_list[int(timeframe_num)]
                            str_to_append += '\n'
                            for date, status in vacant_status.items():
                                if status:
                                    str_to_append += ' '
                                    date_dt = datetime.datetime.strptime(
                                        date, DATE_FORMAT)
                                    if timeframe_num in [TIME_AFTERNOON2, TIME_EVENING]:
                                        if date_dt.strftime('%a') in ['土', '日'] or date_dt.strftime('%a') in ['Sat', 'Sun']:
                                            str_to_append += date_dt.strftime(
                                                DISPLAY_DATE_FORMAT)
                                            if status == 2:
                                                str_to_append += '(予)'
                                            str_to_append += '\n'
                                        else:
                                            str_to_append = ''
                                    else:
                                        str_to_append += date_dt.strftime(
                                            DISPLAY_DATE_FORMAT)
                                        if status == 2:
                                            str_to_append += '(予)'
                                        str_to_append += '\n'
                            message += str_to_append
                            i += 1

        message = common.remove_redundunt(message)
        message = common.to_japanese_day(message)
        if len(message) == 0:
            message = 'なし'
        return message

    def send_line(self, message: str):
        """LINEを送る"""
        # api.logger.info('message: %s', message)
        bot = LINENotifyBot(access_token=LINE_TOKEN)
        bot.send(message=message)

    # TODO なんかいけてない
    def get_vacant(self, debug: int):
        """空きを取得する"""
        # TODO https://reserve.opas.jp/osakashi/yoyaku/CalendarStatusSelect.cgi を始点に
        if debug == 1:
            """Seleniumを使う代わりにローカルのHTMLファイルから読み込む"""
            # TODO テストデータでデバッグする（正しく取れないときのデータを保存しておこう）
            with open('./output.html') as f:
                html = f.read()
            self.set_date()
            self.get_vacant_list(html)
            message = self.create_message_from_list()
            self.send_line(message)
            return jsonify({
                'status': 'OK',
                'data': message
            })
        else:
            self.init_driver()
            self.select_category(is_login=False)
            self.select_gym(is_all=True)
            self.set_date()
            html = self.get_month_html()
            self.get_vacant_list(html)
            message = self.create_message_from_list()
            self.send_line(message)
            return jsonify({
                'status': 'OK',
                'data': message
            })

# TODO メモリ使用量を調べる
@profile
@api.route('/vacants', methods=['GET'])
def get_vacant(debug=False):
    opas = Opas()
    debug = int(request.args.get('debug', 0))
    res = opas.get_vacant(debug)
    # TODO https://reserve.opas.jp/osakashi/yoyaku/CalendarStatusSelect.cgi を始点に
    return res

# DEBUG
@profile
@api.route('/debug/vacants', methods=['GET'])
def debug_get_vacant():
    opas = Opas()
    """Seleniumを使う代わりにローカルのHTMLファイルから読み込む"""
    # TODO テストデータでデバッグする（正しく取れないときのデータを保存しておこう）
    with open('./output.html') as f:
        html = f.read()
    opas.set_date()
    opas.get_vacant_list(html)
    message = opas.create_message_from_list()
    opas.send_line(message)
    return jsonify({
        'status': 'OK',
        'data': message
    })

# 予約する
@api.route('/reserve', methods=['GET'])
def reserve():
    """予約する"""
    opas = Opas()
    driver = opas.init_driver()
    opas.login(OPAS_ID, OPAS_PASSWORD)
    opas.select_category(is_login=True)
    # opas.select_gym(is_all=False)
    # 体育館・コートを選択
    driver.find_element_by_id("i_record16").click() # なにわ第一
    # driver.find_element_by_id("i_record22").click() # 東成第一
    x_next = "//div[@id='fmaincolumn']/div[@id='pagerbox']/a[2]"
    driver.find_element_by_xpath(x_next).click()

    # 日付選択
    # TODO 希望の年月日を選択する
    opas.select_date(2021, 1, 17) # 浪速1/17 12-15
    # opas.select_date(2021, 2, 9) # 東成2/9
    x_btn_display = "//table[@class='none_style']/tbody/tr/td[3]"
    driver.find_element_by_xpath(x_btn_display).click()

    # ポップアップ OK
    x_popup_ok = "//input[@id='popup_ok']"
    driver.find_element_by_xpath(x_popup_ok).click()

    # 予約対象区分選択（日付選択後）
    # テキトーに最初のやつ選択
    # TODO 希望の日時を指定する
    driver.find_element_by_id("i_record0").click()

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
    kaptcha = driver.find_element_by_xpath(x_kaptcha_img).screenshot_as_png
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
    res_url = "https://2captcha.com/res.php?key=" + CAPTCHA_KEY + "&action=get&id=" + captcha_id
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

if __name__ == '__main__':
    # logging.basicConfig(level=logging.INFO,
    #                     format='%(levelname)s: %(message)s')
    # logging.disable(logging.CRITICAL)
    api.run(debug=True, host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))