@api.route('/reserve', methods=['GET'])
def reserve():
    """予約する"""
    opas = Opas()
    opas.init_driver()
    opas.login(OPAS_ID, OPAS_PASSWORD)
    opas.select_category(is_login=True)
    opas.select_gym(is_all=False)

    # 日付選択
    # TODO 希望の年月日を選択する
    opas.select_date(2020, 12, 9)
    x_btn_display = "//table[@class='none_style']/tbody/tr/td[3]"
    driver.find_element_by_xpath(x_btn_display).click()

    # ポップアップ OK
    x_popup_ok = "//input[@id='popup_ok']"
    driver.find_element_by_xpath(x_popup_ok).click()

    # 予約対象区分選択（日付選択後）
    # テキトーに最初のやつ選択
    # TODO 希望の日時を指定する
    driver.find_element_by_id("i_record1").click()

    # 次に進む
    driver.find_element_by_xpath("//div[@id='pagerbox']/a[2]").click()

    # 申込内容入力
    driver.find_element_by_id("numberOfRiyosha").send_keys('22')

    # 次に進む
    driver.find_element_by_xpath("//div[@id='pagerbox']/a[2]").click()

    # 利用規約
    driver.find_element_by_id("img_chkRiyoKiyaku").click()

    # kaptcha 取得
    x_kaptcha_img = "//div[@class='sub_box']/div[2]/p/img[1]"
    kaptcha = driver.find_element_by_xpath(
        x_kaptcha_img).screenshot_as_png
    with open('./kaptcha.png', 'wb') as f:
        f.write(kaptcha)

    url = "http://2captcha.com/in.php"
    req_data = {
        'key': CAPTCHA_KEY,
        'method': 'base64',
        'body': base64.b64encode(kaptcha),
        'lang': 'ja',
        'numeric': 4,
        'min_len': 5,
        'max_len': 5,
        'language': 2,
    }
    res = requests.post(url, req_data)
    if res.text[0:2] != 'OK':
        quit('Service error. Error code:' + res.text)
    captcha_id = res.text[3:]
    time.sleep(3)  # 解析が終わるまで待つ
    res_url = "https://2captcha.com/res.php?key=" + \
        CAPTCHA_KEY + "&action=get&id=" + captcha_id
    res = requests.get(res_url)
    if res.status_code == 200 and res.text[0:2] == 'OK':
        kaptcha_txt = res.text[3:]
        driver.find_element_by_name("txtKaptcha").send_keys(kaptcha_txt)
        # 確定
        x_fix_btn = "//div[@class='centered-paranemic-ul-div']/ul/li/a"
        driver.find_element_by_xpath(x_fix_btn).click()
        # OK
        driver.find_element_by_xpath(x_popup_ok).click()
        time.sleep(5)  # 余韻に浸る
    return ''


@api.errorhandler(404)
def not_found(error):
    """404の時のページ"""
    return make_response(jsonify({'error': 'Not found'}), 404)

