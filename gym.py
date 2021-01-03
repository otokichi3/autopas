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
timeframe_list = {
    TIME_MORNING: '09:00-12:00',
    TIME_AFTERNOON1: '12:00-15:00',
    TIME_AFTERNOON2: '13:00-16:30',
    TIME_EVENING: '15:00-18:00',
    TIME_NIGHT1: '17:30-21:00',
    TIME_NIGHT2: '18:00-21:00',
}

shisetu_shortener = {
    '体育場': '',
    '１／２面': '',
    '体育館': '',
    'フットサルの利用は、「その他（種目番号：９８８）」から申し込みください': '',
    '現在、多目的室のエアコン（空調設備）故障中です。': '',
    '１': '1',
    '２': '2',
}

# TODO これらのクラスを opas.py で使用する
@dataclasses.dataclass
class Shisetu:
    """施設"""
    name: str = 'undefined'
    vacant_table: dict[dict[int]] = dataclasses.field(default_factory=dict)

    @classmethod
    def shorten(cls, name) -> str:
        for k, v in shisetu_shortener.items():
            name = name.replace(k, v)
        
        return name

    def set_vacant(self, date, timeframe, status):
        if status == 0:
            return

        if date in self.vacant_table:
            self.vacant_table[date][timeframe] = status
        else:
            self.vacant_table[date] = {}
            self.vacant_table[date][timeframe] = status
    
    def vacant_filter(self):
        # dayoff 土日だけ
        dayoff_vacant = dict(filter(lambda item: '土' in item[0] or '日' in item[0], self.vacant_table.items()))
        # dayoff-time 土日の12時以降
        # TODO 時間帯で絞る処理
        dayoff_time_vacant = dict(filter(lambda item: item[1] in [1,2,3,4,5], dayoff_vacant.items()))
        # weekday-time 平日だけ
        weekday_vacant = dict(filter(lambda item: '土' not in item[0] or '日' not in item[0], self.vacant_table.items()))
        # weekday-time 平日の17時以降
        weekday_time_vacant = dict(filter(lambda item: item[0] in [4, 5], weekday_vacant.items()))

        return dayoff_time_vacant.update(weekday_time_vacant)
        
    def get_vacant_days(self) -> str:
        # filtered_vacant_table = self.vacant_filter()
        filtered_vacant_table = self.vacant_table
        res = ''
        for date, tf_list in filtered_vacant_table.items():
            date_dt = datetime.datetime.strptime(date, DATE_FORMAT)
            res += ' ' + date_dt.strftime(DISPLAY_DATE_FORMAT)
            for tf, status in tf_list.items():
                if status == 1:
                    res += ' ' + timeframe_list[tf]
                elif status == 2:
                    res += ' ' + timeframe_list[tf] + '(予)'
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
    '丸善インテックアリーナ大阪（中央体育館）': '中央体育館',
    '体育館': '',
    '明治スポーツプラザ浪速': '浪速',
    '１': '1',
    '２': '2',
    '明治スポーツプラザ': '',
}

@dataclasses.dataclass
class Gym:
    """体育館"""
    name: str = 'undefined'
    shisetu_list: list[Shisetu] = dataclasses.field(default_factory=list)

    def __post_init__(self):
        self.name = self.shorten(self.name)
    
    @classmethod
    def shorten(cls, name) -> str:
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
                res += '[' + self.name + ' ' + s.name + ']\n' + vacant_days + '\n'
        return res
