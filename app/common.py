redundunts = {
    'スポーツセンター': 'SC',
    '体育場': '',
    '１／２面': '',
    'ゼット': '',
    'プール': '',
    'サンエイワーク': '',
    'フィットネス２１': '',
    'ＨＳＴ': '',
}

def remove_redundunt(message: str) -> str:
    if len(redundunts) == 0:
        return message
        
    for k, v in redundunts.items():
        message = message.replace(k, v)
    
    return message
