redundunts = {
    'スポーツセンター': 'SC',
    '体育場': '',
    '１／２面': '',
    'ゼット': '',
    'プール': '',
    'サンエイワーク': '',
    'フィットネス２１': '',
    'ＨＳＴ': '',
    '丸善インテックアリーナ大阪（中央体育館）  サブアリーナ': '中央体育館',
}

def remove_redundunt(message: str) -> str:
    if len(redundunts) == 0:
        return message
        
    for k, v in redundunts.items():
        message = message.replace(k, v)
    
    return message
