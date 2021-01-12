autopas
====

OPAS 上の作業を自動化する

## Cloud Scheduler を作成

### 例1（空き照会）

19時に実行する

#### Windows

```
gcloud beta scheduler jobs create http opas-aki-shokai `
--time-zone "Asia/Tokyo" `
--schedule="0 19 * * *" `
--uri="https://opas-ywsyyp4wlq-uc.a.run.app/vacants" `
--oidc-service-account-email="opas-cloud-run-scheduled-invok@opas-badminton-dev.iam.gserviceaccount.com" `
--http-method="GET" `
```

#### 例2（予約）

パスパラメータに必要な情報を詰め込む

#### Windows

```
gcloud beta scheduler jobs create http opas-reserve-nishinari-2021-2-4 `
--time-zone "Asia/Tokyo" `
--schedule="0 7 * * *" `
--uri="https://opas-ywsyyp4wlq-uc.a.run.app/reserve/34/2021/2/4" `
--oidc-service-account-email="opas-cloud-run-scheduled-invok@opas-badminton-dev.iam.gserviceaccount.com" `
--http-method="GET" 
```

#### Unix

```
gcloud beta scheduler jobs create http opas-reserve-test2 \
--time-zone "Asia/Tokyo" \
--schedule="0 7 * * *" \
--uri="https://opas-ywsyyp4wlq-uc.a.run.app/reserve/35/2021/2/18" \
--oidc-service-account-email="opas-cloud-run-scheduled-invok@opas-badminton-dev.iam.gserviceaccount.com" \
--http-method="GET" \
```

* いつか使えるようになりたい JSON 送る方式

```
gcloud beta scheduler jobs create http opas-reserve-test \
--time-zone "Asia/Tokyo" \
--schedule="0 0 * * *" \
--uri="https://opas-ywsyyp4wlq-uc.a.run.app/reserve" \
--oidc-service-account-email="opas-cloud-run-scheduled-invok@opas-badminton-dev.iam.gserviceaccount.com" \
--headers="Content-Type=application/json" \
--http-method="POST" \
--message-body='{"gym":"35", "year":"2021", "month":"2", "day":"18"}'
```

## 付録

### cron の書き方

| 「*」の位置（左端から） | 頻度 | 指定できる数字     | 備考         | 
| ----------------------- | ---- | ------------------ | ------------ | 
| 1番目                   | 分   | 0-59               |              | 
| 2番目                   | 時   | 0-23               |              | 
| 3番目                   | 日   | 1-31               |              | 
| 4番目                   | 月   | 1-12               |              | 
| 5番目                   | 曜日 | 0-7                | 0と7は日曜日 | 