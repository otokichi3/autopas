timeframe_list = {
    '09:00 ～ 12:00(午前)': 0, '09:00 ～ 12:00': 0,
    '13:00 ～ 16:30(午後)': 1, '12:00 ～ 15:00': 1,
    '15:00 ～ 18:00': 2,
    '17:30 ～ 21:00(夜間)': 3, '18:00 ～ 21:00': 3,
}


# コート
class Court:
    timeframes = []

    def __init__(self, name: str):
        self.name = name

    def set_html(self, html: str):
        self.html = html

    def add_timeframe(self, timeframe):
        self.timeframes.append(timeframe)


# ジム
class Gym:
    courts = []

    def __init__(self, name: str):
        self.name = name

    def add_court(self, court: Court):
        self.courts.append(court)
