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
