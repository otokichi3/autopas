import sys
import os
import io
import csv
import json
import logging
import base64
import datetime
import locale
from dateutil.relativedelta import relativedelta
from typing import List, Dict

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
# CAPTCHA_KEY = os.environ['captcha_key']
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

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


class Opas:
    timeframes = []

    login_url = 'https://reserve.opas.jp/osakashi/menu/Login.cgi'

    chrome_path = '/usr/bin/chromium-browser'
    chromedriver_path = '/usr/lib/chromium/chromedriver'
    # chromedriver_path = 'C:\\bin\\chromedriver.exe'

    options = Options()
    # for linux
    options.binary_location = '/usr/bin/chromium-browser'
    # for windows
    # options.binary_location = 'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe'
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    # options.add_argument('--window-size=1200x600')

    # cookie_name = 'JSESSIONID'
    # cookie_value = ''
    # cookie_domain = 'reserve.opas.jp'

    def init_driver(self):
        """Seleniumドライバを初期化する"""
        self.__driver = webdriver.Chrome(self.chromedriver_path, options=self.options)
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

    def login(self, id: str, password: str):
        """OPASにログインする"""
        self.__driver.find_element_by_name("txtRiyoshaCode").send_keys(id)
        self.__driver.find_element_by_name("txtPassWord").send_keys(password)
        x_login_btn = "//p[@class='login_btn']/img"
        self.__driver.find_element_by_xpath(x_login_btn).click()

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

    def select_gym(self, is_all: bool = False, rec_nums: List[str] = []):
        """ジムを選択する"""
        if is_all:
            for i in range(COURT_COUNT):
                self.__driver.find_element_by_id(
                    "i_record{}".format(i)).click()
            x_next = "//div[@id='fmaincolumn']/div[@id='pagerbox']/a[2]"
            self.__driver.find_element_by_xpath(x_next).click()
            return

        # TODO 体育館を複数選択する
        if len(rec_nums) == 0:
            for rec_num in rec_nums:
                print(rec_num)

    def get_month_html(self) -> str:
        """一月分のHTMLを取得する"""
        # 翌月の週ごとに HTML を取得する
        weekly_htmls = []
        x_btn_display = "//table[@class='none_style']/tbody/tr/td[3]"
        x_category_select = "//div[@id='mmaincolumn']/div[@class='tablebox']"
        today = datetime.date.today()
        first_week = today + relativedelta(months=1)
        first_week = first_week.replace(day=1)
        self.year = first_week.year
        self.month = first_week.month
        self.day = first_week.day
        for i in range(5):
            target_week = first_week + relativedelta(weeks=+i)
            self.select_date(target_week.year, target_week.month, target_week.day)
            self.__driver.find_element_by_xpath(x_btn_display).click()
            inner_html = self.__driver.find_element_by_xpath(
                x_category_select).get_attribute('innerHTML')
            weekly_htmls.append(inner_html)

        # 5週分の HTML を結合して返す
        joined = ''.join(weekly_htmls)
        # with open('./output.html', 'w') as f:
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

    def get_vacant_list(self, html):
        """空きリストを取得する"""
        soup = BeautifulSoup(html, "html.parser")
        trs = soup.select('table.facilitiesbox > tbody > tr')
        morning_row = 'tr:nth-of-type(3) > td'
        afternoon_row = 'tr:nth-of-type(4) > td'
        evening_row = 'tr:nth-of-type(5) > td'
        night_row = 'tr:nth-of-type(6) > td'
        morning2_row = 'tr:nth-of-type(10) > td'
        afternoon2_row = 'tr:nth-of-type(11) > td'
        evening2_row = 'tr:nth-of-type(12) > td'
        night2_row = 'tr:nth-of-type(13) > td'

        # TODO class に置き換える
        gym_dict = {}
        """
        [ジム: [コート: [時間帯: [[日時: 空き状態]]]]
        [string: [string: [int: [[string: bool]]]]
        four-nested dictionary -> to be classed?
        """
        """
        TODO
        - Cognitive Complexity
            https://qiita.com/suzuki_sh/items/824c36b8d53dd2f1efcb
        - Database
        - Memory footprint
            https://tech.curama.jp/entry/2018/06/22/120000
        """
        for i, tr in enumerate(trs):  # 140
            base_date = datetime.date(self.year, self.month, self.day)
            # base_date = datetime.date(2021, 1, 1)
            week_index = int(i/GYM_COUNT)
            day_index = 0
            base_date += relativedelta(weeks=week_index)
            gym_name = tr.select_one(".kaikan_title").text.replace(' ', '')
            shisetu = tr.select(".shisetu_name")  # 配列
            if i < GYM_COUNT:
                # 最初(MM/01)は辞書を作成する
                if len(shisetu) == 1:
                    shisetu_name = shisetu[0].text
                    """
                    TODO
                    時間帯別の値を配列ではなく辞書にし、日付をキー、
                    状態(0:予約不可、1:予約可、2:空く予定)を値にする。
                    """
                    gym_dict[gym_name] = {}
                    gym_dict[gym_name][shisetu_name] = {
                        TIME_MORNING: {},
                        TIME_AFTERNOON1: {},
                        TIME_AFTERNOON2: {},
                        TIME_EVENING: {},
                        TIME_NIGHT1: {},
                        TIME_NIGHT2: {}
                    }
                    # コート名と日付部分とページ移動部分を除く(-3)
                    timeframe_count = len(
                        tr.select("td > table > tbody > tr")) - 3
                    if timeframe_count == 3:
                        mornings = tr.td.table.tbody.select(morning_row)
                        afternoons = tr.td.table.tbody.select(afternoon_row)
                        # 時間帯が３つの場合は３つ目が夜
                        nights = tr.td.table.tbody.select(evening_row)
                        for m, a, n in zip(mornings, afternoons, nights):
                            if "facmdstime" in m.get('class'):
                                continue
                            else:
                                target_date = base_date + \
                                    relativedelta(days=day_index)
                                date_str = target_date.strftime('%Y-%m-%d')
                                m_status = self.get_vacant_status(m.find("img").get("src") + m.text)
                                gym_dict[gym_name][shisetu_name][TIME_MORNING][date_str] = m_status
                                a_status = self.get_vacant_status(a.find("img").get("src") + a.text)
                                gym_dict[gym_name][shisetu_name][TIME_AFTERNOON2][date_str] = a_status
                                n_status = self.get_vacant_status(n.find("img").get("src") + n.text)
                                gym_dict[gym_name][shisetu_name][TIME_NIGHT1][date_str] = n_status
                                day_index += 1
                    else:
                        mornings = tr.td.table.tbody.select(morning_row)
                        afternoons = tr.td.table.tbody.select(afternoon_row)
                        evenings = tr.td.table.tbody.select(evening_row)
                        nights = tr.td.table.tbody.select(night_row)
                        for m, a, e, n in zip(mornings, afternoons, evenings, nights):
                            if "facmdstime" in m.get('class'):
                                continue
                            else:
                                target_date = base_date + \
                                    relativedelta(days=day_index)
                                date_str = target_date.strftime('%Y-%m-%d')

                                m_status = self.get_vacant_status(m.find("img").get("src") + m.text)
                                gym_dict[gym_name][shisetu_name][TIME_MORNING][date_str] = m_status
                                a_status = self.get_vacant_status(a.find("img").get("src") + a.text)
                                gym_dict[gym_name][shisetu_name][TIME_AFTERNOON1][date_str] = a_status
                                e_status = self.get_vacant_status(e.find("img").get("src") + e.text)
                                gym_dict[gym_name][shisetu_name][TIME_EVENING][date_str] = e_status
                                n_status = self.get_vacant_status(n.find("img").get("src") + n.text)
                                gym_dict[gym_name][shisetu_name][TIME_NIGHT2][date_str] = n_status
                                day_index += 1
                else:
                    shisetu1_name = shisetu[0].text
                    shisetu2_name = shisetu[1].text
                    gym_dict[gym_name] = {}
                    gym_dict[gym_name][shisetu1_name] = {
                        TIME_MORNING: {},
                        TIME_AFTERNOON1: {},
                        TIME_AFTERNOON2: {},
                        TIME_EVENING: {},
                        TIME_NIGHT1: {},
                        TIME_NIGHT2: {}
                    }
                    gym_dict[gym_name][shisetu2_name] = {
                        TIME_MORNING: {},
                        TIME_AFTERNOON1: {},
                        TIME_AFTERNOON2: {},
                        TIME_EVENING: {},
                        TIME_NIGHT1: {},
                        TIME_NIGHT2: {}
                    }

                    mornings1 = tr.td.table.tbody.select(morning_row)
                    afternoons1 = tr.td.table.tbody.select(afternoon_row)
                    evenings1 = tr.td.table.tbody.select(evening_row)
                    nights1 = tr.td.table.tbody.select(night_row)
                    for m, a, e, n in zip(mornings1, afternoons1, evenings1, nights1):
                        if "facmdstime" in m.get('class'):
                            continue
                        else:
                            target_date = base_date + \
                                relativedelta(days=day_index)
                            date_str = target_date.strftime('%Y-%m-%d')
                            m_status = self.get_vacant_status(m.find("img").get("src") + m.text)
                            gym_dict[gym_name][shisetu1_name][TIME_MORNING][date_str] = m_status
                            a_status = self.get_vacant_status(a.find("img").get("src") + a.text)
                            gym_dict[gym_name][shisetu1_name][TIME_AFTERNOON1][date_str] = a_status
                            e_status = self.get_vacant_status(e.find("img").get("src") + e.text)
                            gym_dict[gym_name][shisetu1_name][TIME_EVENING][date_str] = e_status
                            n_status = self.get_vacant_status(n.find("img").get("src") + n.text)
                            gym_dict[gym_name][shisetu1_name][TIME_NIGHT2][date_str] = n_status
                            day_index += 1

                    day_index = 0

                    mornings2 = tr.td.table.tbody.select(morning2_row)
                    afternoons2 = tr.td.table.tbody.select(afternoon2_row)
                    evenings2 = tr.td.table.tbody.select(evening2_row)
                    nights2 = tr.td.table.tbody.select(night2_row)
                    for m, a, e, n in zip(mornings2, afternoons2, evenings2, nights2):
                        if "facmdstime" in m.get('class'):
                            continue
                        else:
                            target_date = base_date + \
                                relativedelta(days=day_index)
                            date_str = target_date.strftime('%Y-%m-%d')
                            m_status = self.get_vacant_status(m.find("img").get("src") + m.text)
                            gym_dict[gym_name][shisetu2_name][TIME_MORNING][date_str] = m_status
                            a_status = self.get_vacant_status(a.find("img").get("src") + a.text)
                            gym_dict[gym_name][shisetu2_name][TIME_AFTERNOON1][date_str] = a_status
                            e_status = self.get_vacant_status(e.find("img").get("src") + e.text)
                            gym_dict[gym_name][shisetu2_name][TIME_EVENING][date_str] = e_status
                            n_status = self.get_vacant_status(n.find("img").get("src") + n.text)
                            gym_dict[gym_name][shisetu2_name][TIME_NIGHT2][date_str] = n_status
                            day_index += 1
            else:
                # 二週目(MM/08)以降は追加する
                if len(shisetu) == 1:
                    shisetu_name = shisetu[0].text
                    # コート名と日付部分とページ移動部分を除く(-3)
                    timeframe_count = len(
                        tr.select("td > table > tbody > tr")) - 3
                    # TODO 時間帯が3つしかない体育館は上から3つのみのため、
                    #      その前提でコードを書いて良いかもしれない。
                    #      →switch 文を使い体育館ごとに処理を分ける。
                    if timeframe_count == 3:
                        mornings = tr.td.table.tbody.select(morning_row)
                        afternoons = tr.td.table.tbody.select(afternoon_row)
                        nights = tr.td.table.tbody.select(evening_row)
                        for m, a, n in zip(mornings, afternoons, nights):
                            if "facmdstime" in m.get('class'):
                                continue
                            else:
                                target_date = base_date + \
                                    relativedelta(days=day_index)
                                date_str = target_date.strftime('%Y-%m-%d')
                                m_status = self.get_vacant_status(m.find("img").get("src") + m.text)
                                gym_dict[gym_name][shisetu_name][TIME_MORNING][date_str] = m_status
                                a_status = self.get_vacant_status(a.find("img").get("src") + a.text)
                                gym_dict[gym_name][shisetu_name][TIME_AFTERNOON2][date_str] = a_status
                                n_status = self.get_vacant_status(n.find("img").get("src") + n.text)
                                gym_dict[gym_name][shisetu_name][TIME_NIGHT1][date_str] = n_status
                                day_index += 1
                    else:
                        mornings = tr.td.table.tbody.select(morning_row)
                        afternoons = tr.td.table.tbody.select(afternoon_row)
                        evenings = tr.td.table.tbody.select(evening_row)
                        nights = tr.td.table.tbody.select(night_row)
                        for m, a, e, n in zip(mornings, afternoons, evenings, nights):
                            if "facmdstime" in m.get('class'):
                                continue
                            else:
                                target_date = base_date + \
                                    relativedelta(days=day_index)
                                date_str = target_date.strftime('%Y-%m-%d')
                                m_status = self.get_vacant_status(m.find("img").get("src") + m.text)
                                gym_dict[gym_name][shisetu_name][TIME_MORNING][date_str] = m_status
                                a_status = self.get_vacant_status(a.find("img").get("src") + a.text)
                                gym_dict[gym_name][shisetu_name][TIME_AFTERNOON1][date_str] = a_status
                                e_status = self.get_vacant_status(e.find("img").get("src") + e.text)
                                gym_dict[gym_name][shisetu_name][TIME_EVENING][date_str] = e_status
                                n_status = self.get_vacant_status(n.find("img").get("src") + n.text)
                                gym_dict[gym_name][shisetu_name][TIME_NIGHT2][date_str] = n_status
                                day_index += 1
                else:
                    shisetu1_name = shisetu[0].text
                    shisetu2_name = shisetu[1].text

                    # 施設が2つある場合は必ず時間帯がそれぞれ4つある
                    mornings1 = tr.td.table.tbody.select(morning_row)
                    afternoons1 = tr.td.table.tbody.select(afternoon_row)
                    evenings1 = tr.td.table.tbody.select(evening_row)
                    nights1 = tr.td.table.tbody.select(night_row)
                    for m, a, e, n in zip(mornings1, afternoons1, evenings1, nights1):
                        if "facmdstime" in m.get('class'):
                            continue
                        else:
                            target_date = base_date + \
                                relativedelta(days=day_index)
                            date_str = target_date.strftime('%Y-%m-%d')
                            m_status = self.get_vacant_status(m.find("img").get("src") + m.text)
                            gym_dict[gym_name][shisetu1_name][TIME_MORNING][date_str] = m_status
                            a_status = self.get_vacant_status(a.find("img").get("src") + a.text)
                            gym_dict[gym_name][shisetu1_name][TIME_AFTERNOON1][date_str] = a_status
                            e_status = self.get_vacant_status(e.find("img").get("src") + e.text)
                            gym_dict[gym_name][shisetu1_name][TIME_EVENING][date_str] = e_status
                            n_status = self.get_vacant_status(n.find("img").get("src") + n.text)
                            gym_dict[gym_name][shisetu1_name][TIME_NIGHT2][date_str] = n_status
                            day_index += 1

                    day_index = 0

                    mornings2 = tr.td.table.tbody.select(morning2_row)
                    afternoons2 = tr.td.table.tbody.select(afternoon2_row)
                    evenings2 = tr.td.table.tbody.select(evening2_row)
                    nights2 = tr.td.table.tbody.select(night2_row)
                    for m, a, e, n in zip(mornings2, afternoons2, evenings2, nights2):
                        if "facmdstime" in m.get('class'):
                            continue
                        else:
                            target_date = base_date + \
                                relativedelta(days=day_index)
                            date_str = target_date.strftime('%Y-%m-%d')
                            m_status = self.get_vacant_status(m.find("img").get("src") + m.text)
                            gym_dict[gym_name][shisetu2_name][TIME_MORNING][date_str] = m_status
                            a_status = self.get_vacant_status(a.find("img").get("src") + a.text)
                            gym_dict[gym_name][shisetu2_name][TIME_AFTERNOON1][date_str] = a_status
                            e_status = self.get_vacant_status(e.find("img").get("src") + e.text)
                            gym_dict[gym_name][shisetu2_name][TIME_EVENING][date_str] = e_status
                            n_status = self.get_vacant_status(n.find("img").get("src") + n.text)
                            gym_dict[gym_name][shisetu2_name][TIME_NIGHT2][date_str] = n_status
                            day_index += 1

        # jsonに吐き出してデバッグする処理
        # d = json.dumps(gym_dict,ensure_ascii=False, indent=4)
        # with open('./output.json', 'w') as f:
        #     f.write(d)

        return gym_dict

    def get_vacant_status(self, img_src) -> int:
        STATUS_RESERVED = 0
        STATUS_VACANT = 1
        STATUS_TO_BE_VACANT = 2
        if 'maru.png' in img_src:
            return STATUS_VACANT
        elif 'yo.png' in img_src or '予' in img_src:
            return STATUS_TO_BE_VACANT
        else:
            return STATUS_RESERVED

    """
    TODO
    - Cognitive Complexity
    """
    def create_message_from_list(self, gym_dict) -> str:
        """空きリストからLINEメッセージを作成する"""
        message = ''
        str_to_append = ''
        for gym_name, court in gym_dict.items():
            gym_name = gym_name.replace(' ', '')
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
                    if timeframe_num in [TIME_AFTERNOON2, TIME_EVENING, TIME_NIGHT1, TIME_NIGHT2]:
                        if len(vacant_status) > 0 and any(vacant_status.values()):
                            str_to_append = ''
                            if i == 0:
                                str_to_append += '\n'
                                str_to_append += '['+gym_name + ' ' + court_name + ']'
                                str_to_append += '\n'
                            str_to_append += timeframe_list[int(timeframe_num)]
                            str_to_append += '\n'
                            for date, status in vacant_status.items():
                                if status:
                                    str_to_append += ' '
                                    date_dt = datetime.datetime.strptime(date, '%Y-%m-%d')
                                    if timeframe_num in [TIME_AFTERNOON2, TIME_EVENING]:
                                        if date_dt.strftime('%a') in ['土', '日'] or date_dt.strftime('%a') in ['Sat', 'Sun']:
                                            str_to_append += date_dt.strftime('%m-%d(%a)')
                                            if status == 2:
                                                str_to_append += '(予)'
                                            str_to_append += '\n'
                                        else:
                                            str_to_append = ''
                                    else:
                                        str_to_append += date_dt.strftime('%m-%d(%a)')
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
        bot = LINENotifyBot(access_token=LINE_TOKEN)
        bot.send(message=message)


api = Flask(__name__)
CORS(api)


@api.route('/vacants', methods=['GET'])
def get_vacant(debug=False):
    """空きを取得する"""
    # TODO https://reserve.opas.jp/osakashi/yoyaku/CalendarStatusSelect.cgi を始点に
    # debug: 1=debug, 0=no debug
    debug = int(request.args.get('debug', 0))

    if debug == 1:
        """空き取得をデバッグする"""
        """Seleniumを使う代わりにローカルのHTMLファイルから読み込む"""
        # opas = Opas()
        # path = './output.html'
        # with open(path) as f:
        #     html = f.read()
        # vacant_list = opas.get_vacant_list(html)
        # with open('./output.json') as f:
        #     gym_json = f.read()
        # vacant_list = json.loads(gym_json)
        # message = opas.create_message_from_list(vacant_list)

        # return message
    else:
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
    
    return ''


if __name__ == '__main__':
    # (low)DEBUG, INFO, WARNING, ERROR, CRITICAL(high)
    # logging.basicConfig(level=logging.INFO,
    #                     format='%(levelname)s: %(message)s')
    # CRITICAL レベル以下のログを出力しない（＝実質なし）
    # logging.disable(logging.CRITICAL)
    # logging.info('debug: {}'.format())
    api.run(debug=True, host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
