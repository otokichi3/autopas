import sys
import os
import io
import csv
import json
import base64
import datetime
import locale
import time
import dataclasses
from dateutil.relativedelta import relativedelta
from typing import List, Dict
from itertools import zip_longest

import schedule
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.select import Select
from flask import Flask, jsonify, abort, make_response, request
from flask_cors import CORS
from bs4 import BeautifulSoup

from line_notify_bot import LINENotifyBot
from gym import Shisetu, Gym
import common
from xpath import xpath

app = Flask(__name__)
CORS(app)

locale.setlocale(locale.LC_TIME, 'ja_JP.UTF-8')

OPAS_ID = os.environ['opas_id']
OPAS_PASSWORD = os.environ['opas_password']
LINE_TOKEN = os.environ['line_token']
# LINE_TOKEN = os.environ['line_token_test']
CAPTCHA_KEY = os.environ['captcha_key']

GYM_COUNT = 28
COURT_COUNT = 37

TIME_MORNING = 0
TIME_AFTERNOON1 = 1
TIME_AFTERNOON2 = 2
TIME_EVENING = 3
TIME_NIGHT1 = 4
TIME_NIGHT2 = 5

DATE_FORMAT = '%Y-%m-%d'
DISPLAY_DATE_FORMAT = '%m-%d(%a)'
OUTPUT_HTML = './output.html'

# 変数定義部
# Windows
if os.name == "nt":
    chromedriver_path = 'C:\\bin\\chromedriver.exe'
    binary_location = 'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe'
# Mac: Darwin, Linux: Linux
else:
    chromedriver_path = '/usr/lib/chromium/chromedriver'
    binary_location = '/usr/bin/chromium-browser'

STATUS_RESERVED = 0
STATUS_VACANT = 1
STATUS_TO_BE_VACANT = 2
# END

class Opas:
    timeframes = []
    gyms = {}
    cgyms = []
    cgym = None
    gym_name = ''
    shisetu = None
    base_date = None

    # TODO 定数を外だしする
    login_url = 'https://reserve.opas.jp/osakashi/menu/Login.cgi'

    options = Options()
    options.binary_location = binary_location
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')

    # TODO Cookie を取得しておいてログイン状態で開始?
    # cookie_name = 'JSESSIONID'
    # cookie_value = ''
    # cookie_domain = 'reserve.opas.jp'

    def init_driver(self):
        """Seleniumドライバを初期化する"""
        self.__driver = webdriver.Chrome(chromedriver_path, options=self.options)
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
        self.__driver.find_element_by_xpath(xpath['loginbtn']).click()

    # ログインしている場合はログイン空き照会、そうでない場合はトップの空き照会
    def inquire(self, is_login: bool):
        if is_login:
            self.__driver.find_element_by_xpath(xpath['aki_syoukai_yoyaku_btn']).click()
        else:
            self.__driver.find_element_by_xpath(xpath['aki_jyoukyou_syoukai_btn']).click()

    def select_category(self, is_login: bool):
        """カテゴリーを選択する"""
        # 空き照会・予約
        self.inquire(is_login)
        self.__driver.find_element_by_xpath(xpath['shiborikomu']).click()
        self.__driver.find_element_by_xpath(xpath['daibunrui_badminton']).click()
        self.__driver.find_element_by_xpath(xpath['shobunrui_badminton']).click()

    def select_gym(self, is_all: bool = False, rec_nums: List[str] = []):
        """ジムを選択する"""
        if is_all:
            for i in range(COURT_COUNT):
                self.__driver.find_element_by_id("i_record{}".format(i)).click()
            self.__driver.find_element_by_xpath(xpath['next']).click()

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
        # 日数が短い月は4週、とか。
        week_count = 5 if self.month != 2 else 4
        for i in range(week_count):
            target = self.first_week + relativedelta(weeks=+i)
            self.select_date(target.year, target.month, target.day)
            self.__driver.find_element_by_xpath(xpath['display']).click()
            inner_html = self.__driver.find_element_by_xpath(xpath['tablebox']).get_attribute('innerHTML')
            weekly_htmls.append(inner_html)

        # 5週分の HTML を結合して返す
        joined = ''.join(weekly_htmls)
        # デバッグ用
        # with open(OUTPUT_HTML, 'w') as f:
        #     f.write(joined)

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

    def get_vacant_rows(self, tr, timeframe_count, shisetu_name):
        start_num = 3 if '第２' not in shisetu_name else 10
        time_rows = []
        for count in range(4):
            ele = 'tr:nth-of-type({}) > td'
            row = tr.td.table.tbody.select(ele.format(start_num + count))
            # 時間帯が３つかつ夕方の場合
            if timeframe_count == 3 and count == 2:
                time_rows.append([])
                time_rows.append(row)
                break
            else:
                time_rows.append(row)
        return time_rows

    def set_status(self, tr, shisetu_name):
        # コート名と日付部分とページ移動部分を除く(-3)
        timeframe_count = len(tr.select("td > table > tbody > tr")) - 3
        day_index = 0

        existed = self.cgym.has(shisetu_name)
        if existed:
            self.shisetu = self.cgym.get_shisetu(shisetu_name)
        else:
            self.shisetu = Shisetu(shisetu_name)

        mornings, afternoons, evenings, nights = self.get_vacant_rows(tr, timeframe_count, shisetu_name)
        
        for m, a, e, n in zip_longest(mornings, afternoons, evenings, nights):
            if "facmdstime" in m.get('class'):
                continue
            else:
                target_date = self.base_date + relativedelta(days=day_index)
                date_str = target_date.strftime(DATE_FORMAT)
                m_status = self.get_vacant_status(m.find("img").get("src") + m.text)
                a_status = self.get_vacant_status(a.find("img").get("src") + a.text)
                n_status = self.get_vacant_status(n.find("img").get("src") + n.text)
                if e is not None:
                    e_status = self.get_vacant_status(e.find("img").get("src") + e.text)
                if timeframe_count == 3:
                    self.shisetu.set_vacant(date_str, TIME_MORNING, m_status)
                    self.shisetu.set_vacant(date_str, TIME_AFTERNOON2, a_status)
                    self.shisetu.set_vacant(date_str, TIME_NIGHT1, n_status)
                else:
                    self.shisetu.set_vacant(date_str, TIME_MORNING, m_status)
                    self.shisetu.set_vacant(date_str, TIME_AFTERNOON1, a_status)
                    self.shisetu.set_vacant(date_str, TIME_EVENING, e_status)
                    self.shisetu.set_vacant(date_str, TIME_NIGHT2, n_status)
                day_index += 1
                            
        day_index = 0

    def get_shisetu_name(self, shisetu_obj):
        return shisetu_obj.select_one('.clearfix').text

    def set_weekly_vacant(self, tr, shisetu):
        for s in shisetu:
            shisetu_name = self.get_shisetu_name(s)
            self.set_status(tr, shisetu_name)
            if not self.cgym.has(self.shisetu.name):
                self.cgym.shisetu_list.append(self.shisetu)

    def cgym_duplicated(self, cgym) -> bool:
        for c in self.cgyms:
            if c.name == cgym.name:
                return True
        return False

    def get_vacant_list(self, html):
        """空きリストを取得する"""
        soup = BeautifulSoup(html, "html.parser")
        tr_list = soup.select('table.facilitiesbox > tbody > tr')
        for i, tr in enumerate(tr_list):  # 140
            shisetu = tr.select(".shisetu_name")
            if len(shisetu) == 0:
                # 関係のない行はスキップ
                continue
            self.base_date = datetime.date(self.year, self.month, self.day) + relativedelta(weeks=int(i/GYM_COUNT))
            self.gym_name = tr.select_one(".kaikan_title").text.replace(' ', '')

            existed = None
            for cgym in self.cgyms:
                if cgym.name == self.gym_name:
                    existed = cgym
                
            if existed is not None:
                cgym = existed
            else:
                cgym = Gym(self.gym_name)

            self.cgym = cgym
            self.set_weekly_vacant(tr, shisetu)

            if not self.cgym_duplicated(cgym):
                self.cgyms.append(cgym)

    def get_vacant_status(self, img_src) -> int:
        if 'maru.png' in img_src:
            return STATUS_VACANT
        elif ('yo.png' in img_src) or ('予' in img_src):
            return STATUS_TO_BE_VACANT
        else:
            return STATUS_RESERVED

    def create_message(self) -> str:
        """空きリストからLINEメッセージを作成する"""
        msg = ''
        for cgym in self.cgyms:
            msg += cgym.to_msg()
        return '\n' + msg

    def send_line(self, msg: str):
        """LINEを送る"""
        bot = LINENotifyBot(access_token=LINE_TOKEN)
        bot.send(message=msg)

    def get_vacant(self):
        """空きを取得する"""
        # TODO https://reserve.opas.jp/osakashi/yoyaku/CalendarStatusSelect.cgi を始点に
        self.init_driver()
        self.select_category(is_login=False)
        self.select_gym(is_all=True)
        self.set_date()
        html = self.get_month_html()
        self.get_vacant_list(html)
        message = self.create_message()
        # 最後の2文字(\n)を削除
        message = message[0:len(message)-2]
        if len(message) == 0:
            message = 'なし'
        self.send_line(message)

        return jsonify({
            'status': 'OK',
            'data': message
        })

@app.route('/vacants', methods=['GET'])
def get_vacant():
    # app.logger.info('path: {}'.format(request.path))
    # app.logger.info('method: {}'.format(request.method))
    opas = Opas()
    msg = opas.get_vacant()
    return msg

# DEBUG
@app.route('/debug/vacants', methods=['GET'])
def debug_get_vacant():
    """Seleniumを使う代わりにローカルのHTMLファイルから読み込む"""
    opas = Opas()
    with open(OUTPUT_HTML) as f:
        html = f.read()
    opas.set_date()
    opas.get_vacant_list(html)
    message = opas.create_message()
    opas.send_line(message)
    return jsonify({
        'status': 'OK',
        'data': message
    })

def wait():
    pass

# 予約する
@app.route('/reserve/<gym>/<int:year>/<int:month>/<int:day>/<int:hour>', methods=['GET'])
def reserve(gym, year, month, day, hour):
    """予約する"""
    if request.method != 'GET':
        return make_response('Bad Request', 404)

    opas = Opas()
    driver = opas.init_driver()
    opas.login(OPAS_ID, OPAS_PASSWORD)
    opas.select_category(is_login=True)
    # 体育館・コートを選択
    gym_rec = "i_record{}".format(gym)
    driver.find_element_by_id(gym_rec).click()
    driver.find_element_by_xpath(xpath['next']).click()

    # 日付選択
    opas.select_date(year, month, day)
    driver.find_element_by_xpath(xpath['display']).click()

    # ポップアップ OK
    driver.find_element_by_xpath(xpath['popup_ok']).click()

    # 7:00 or 12:00 になるまで1秒間隔で待機
    schedule.every().second.do(wait)
    while True:
        now = datetime.datetime.now()
        if now.hour == hour:
            break
        schedule.run_pending()
        time.sleep(1)

    # 予約対象区分選択（日付選択後）
    driver.find_element_by_id("i_record0").click()

    # 次に進む
    driver.find_element_by_xpath(xpath['next']).click()

    # 申込内容入力
    driver.find_element_by_id("numberOfRiyosha").send_keys('22')

    # 次に進む
    driver.find_element_by_xpath(xpath['next']).click()

    # 利用規約
    driver.find_element_by_id("img_chkRiyoKiyaku").click()

    # kaptcha 取得
    kaptcha = driver.find_element_by_xpath(xpath['kaptcha']).screenshot_as_png

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
    msg = requests.post(url, req_data)
    if msg.text[0:2] != 'OK':
        return make_response(('Service error. Error code:' + msg.text, 500))
    captcha_id = msg.text[3:]
    time.sleep(3)  # 解析が終わるまで待つ
    res_url = "https://2captcha.com/res.php?key=" + CAPTCHA_KEY + "&action=get&id=" + captcha_id
    msg = requests.get(res_url)
    if msg.status_code == 200 and msg.text[0:2] == 'OK':
        kaptcha_txt = msg.text[3:]
        driver.find_element_by_name("txtKaptcha").send_keys(kaptcha_txt)
        # 確定
        driver.find_element_by_xpath(xpath['fix']).click()
        # OK
        driver.find_element_by_xpath(xpath['popup_ok']).click()
    else:
        return make_response(('captcha analysis failed', 500))
        
    return make_response(('OK', 200))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

