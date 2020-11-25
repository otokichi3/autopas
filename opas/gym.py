timeframe_list = {
    '09:00 ～ 12:00(午前)': 1, '09:00 ～ 12:00': 1,
    '13:00 ～ 16:30(午後)': 2, '12:00 ～ 15:00': 2,
    '15:00 ～ 18:00': 3,
    '17:30 ～ 21:00(夜間)': 4, '18:00 ～ 21:00': 4,
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
