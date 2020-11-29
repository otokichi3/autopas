redundunts = {
    'スポーツセンター': '',
    '体育場': '',
    '１／２面': '',
    'ゼット': '',
    'プール': '',
    'サンエイワーク': '',
    'フィットネス２１': '',
    'ＨＳＴ': '',
    '丸善インテックアリーナ大阪（中央体育館）': '中央体育館',
    '体育館': '',
    'フットサルの利用は、「その他（種目番号：９８８）」から申し込みください。': '',
    '第１フットサルの利用は、「その他（種目番号：９８８）」から申し込みください。': '',
    '明治スポーツプラザ浪速': '浪速',
    '１': '1',
    '２': '2'
}

days = {
    'Mon': '月',
    'Tue': '火',
    'Wed': '水',
    'Thu': '木',
    'Fri': '金',
    'Sat': '土',
    'Sun': '日',
}

def remove_redundunt(message: str) -> str:
    if len(redundunts) == 0:
        return message
        
    for k, v in redundunts.items():
        message = message.replace(k, v)
    
    return message

def to_japanese_day(message: str) -> str:
    if len(days) == 0:
        return message
        
    for k, v in days.items():
        message = message.replace(k, v)
    
    return message
