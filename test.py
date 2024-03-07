import datetime

def get_week_count(month, day):
    """HTMLを取得する週の数を取得する"""
    # 23日～月末までの場合は8週
    if day >= 23:
        return 8
    # 1日～22日までは、2月のときのみ4週、それ以外は5週
    if month == 2:
        return 4
    else:
        return 5

if __name__ == '__main__':
    today = datetime.date.today()
    month = today.month
    day = today.day
    week_count = get_week_count(month, day)
    print(week_count)