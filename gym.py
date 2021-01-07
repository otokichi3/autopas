import datetime
import dataclasses
from typing import List, Dict

DATE_FORMAT = '%Y-%m-%d'
DISPLAY_DATE_FORMAT = '%m-%d(%a)'

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
timeframe_list_org = {
    TIME_MORNING: '09:00-12:00',
    TIME_AFTERNOON1: '12:00-15:00',
    TIME_AFTERNOON2: '13:00-16:30',
    TIME_EVENING: '15:00-18:00',
    TIME_NIGHT1: '17:30-21:00',
    TIME_NIGHT2: '18:00-21:00',
}
timeframe_list = {
    TIME_MORNING: '9-12',
    TIME_AFTERNOON1: '12-15',
    TIME_AFTERNOON2: '13-16.5',
    TIME_EVENING: '15-18',
    TIME_NIGHT1: '17.5-21',
    TIME_NIGHT2: '18-21',
}

# 浪速は末尾に句点なし、西淀川はあり。
shisetu_shortener = {
    'サブアリーナ': '',
    '体育場': '',
    '１／２面': '',
    '体育館': '',
    '１': '1',
    '２': '2',
}

# @dataclasses.dataclass
class Shisetu:
    """施設"""
    def __init__(self, name):
        self.name = name
        self.vacant_table = {}
        
    def shorten(self, name) -> str:
        for k, v in shisetu_shortener.items():
            name = name.replace(k, v)
        
        # TODO いけてない
        if len(name) == 0:
            return ''
        else:
            return ' ' + name

    def set_vacant(self, date, timeframe, status):
        if status == 0:
            return

        if date in self.vacant_table:
            self.vacant_table[date][timeframe] = status
        else:
            self.vacant_table[date] = {}
            self.vacant_table[date][timeframe] = status
    
    def vacant_filter(self, only_holiday=None):
        # 反復中の辞書は変更出来ないため、一時辞書を用意
        temp_table = self.vacant_table
        weekday = ['月', '火', '水', '木', '金']
        weekend = ['土', '日']
        # 削除条件１：平日かつ朝～夕の枠
        # 削除条件２：休日かつ朝の枠
        for date, tf_list in temp_table.items():
            youbi = datetime.datetime.strptime(date, DATE_FORMAT).strftime('%a')
            for tf in list(tf_list.keys()):
                cond1 = youbi in weekday and tf < TIME_NIGHT1
                cond2 = youbi in weekend and tf == TIME_MORNING
                if cond1 or cond2:
                    del self.vacant_table[date][tf]
        
        # 空になった日付の後始末
        for date in list(self.vacant_table.keys()):
            if len(self.vacant_table[date]) == 0:
                del self.vacant_table[date]
                
    def get_vacant_days(self) -> str:
        self.vacant_filter()
        res = ''
        for date, tf_list in self.vacant_table.items():
            date_dt = datetime.datetime.strptime(date, DATE_FORMAT)
            res += ' ' + date_dt.strftime(DISPLAY_DATE_FORMAT)
            for tf, status in tf_list.items():
                if status == 1:
                    res += ' ' + timeframe_list[tf]
                elif status == 2:
                    res += ' ' + timeframe_list[tf] + '予'
                else:
                    continue
            res += '\n'
        return res

gym_shortener = {
    'スポーツセンター': '',
    'ゼット': '',
    'プール': '',
    'サンエイワーク': '',
    'フィットネス２１': '',
    'ＨＳＴ': '',
    '丸善インテックアリーナ大阪（中央体育館）': '丸善インテックアリーナ',
    '体育館': '',
    '明治スポーツプラザ浪速': '浪速',
    '１': '1',
    '２': '2',
    '明治スポーツプラザ': '',
}

# @dataclasses.dataclass
class Gym:
    """体育館"""
    # name: str = 'undefined'
    # shisetu_list: list[Shisetu] = dataclasses.field(default_factory=list)

    def __init__(self, name):
        self.name = name
        self.shisetu_list = []

    def shorten(self, name) -> str:
        for k, v in gym_shortener.items():
            name = name.replace(k, v)
        
        return name

    # すべての施設名を返す
    def get_shisetu_names(self) -> str:
        if len(self.shisetu_list) == 1:
            return self.shisetu_list[0].name
        elif len(self.shisetu_list) == 2:
            return self.shisetu_list[0].name + ' ' + self.shisetu_list[1].name
        else:
            return ''
    
    # 施設名があるかどうかを返す
    def has(self, name: str) -> bool:
        if len(self.shisetu_list) == 0:
            return False
        else:
            for shisetu in self.shisetu_list:
                if shisetu.name == name:
                    return True
            return False
    
    # 該当の名前の施設インスタンスを返す
    def get_shisetu(self, name: str):
        if len(self.shisetu_list) == 0:
            return None
        else:
            for shisetu in self.shisetu_list:
                if shisetu.name == name:
                    return shisetu
            return None

    # LINE 送信用にフォーマットした文字列を返す
    def to_msg(self) -> str:
        res = ''
        if len(self.shisetu_list) > 0:
            for s in self.shisetu_list:
                vacant_days = s.get_vacant_days()
                if len(vacant_days) == 0:
                    continue
                gym_name = self.shorten(self.name)
                shisetu_name = s.shorten(s.name)
                res += '[' + gym_name + shisetu_name + ']\n' + vacant_days + '\n'
        return res
