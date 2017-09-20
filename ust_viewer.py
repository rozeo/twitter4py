# coding: utf-8

import json
import time
import sys
import my_key
from twitter4py import twitter4py
from twitter4py import ConvUTC2JST
import re

STREAM_GET_INTERVAL = 3


class gekitotsuChecker:

    def __init__(self, t4p):
        self.gekitotsu = r"仕事が終わった疲れからか"
        self.shigoowa  = r"しごおわ"
        self.t4p = t4p

        self.tid = ""
        self.ts_ms = 0

    def CheckGekitotsu(self, jq):

        # 追突を検知しており、すでにしごおわを検出済みなら反応する
        if re.search(self.gekitotsu, jq['text']) and self.ts_ms > 0:
            gmst = int(jq['timestamp_ms'])

            # 反応リプライ先が検出したしごおわのツイートじゃない場合は無視
            if not jq['in_reply_to_status_id_str'] == self.tid:
                return

            tm = (gmst - self.ts_ms) / 1000.0
            message = "@%s 追突するまでに %.4f秒 かかりました" % (jq['user']['screen_name'], tm)

            t4p.request("POST", "statuses/update",
                        {"status": message, "in_reply_to_status_id": jq['id']})
            print("detected gekitotsu[id:%d]" % (jq['id']))

        # @rozeo_s のツイートのみ対象
        # しごおわを検出したら時刻とツイートidを記録しておく
        elif re.search(self.shigoowa, jq['text']) and re.search(r"rozeo_s", jq['user']['screen_name']):

            self.tid   = jq['id_str']
            self.ts_ms = int(jq['timestamp_ms'])
            print("detected shigoowa[id:%s]" % (jq['id_str']))


if __name__ == '__main__':
    t4p = twitter4py(my_key.CONS_KEY, my_key.CONS_KEY_SEC, my_key.ACC_TOK, my_key.ACC_TOK_SEC)
    j = t4p.CreateUserStreaming({"with": "followings", "replies": "all"})
    checker = gekitotsuChecker(t4p)
    print("---------------------------------------------------------")

    while True:
        js = t4p.StreamNewResponse()
        if js:
            for j in js:
                try:
                    print("[%s] %s (%s)\n%s\n" %
                          (ConvUTC2JST(j['created_at']), j["user"]["name"], j["user"]["screen_name"], j['text']))
                    checker.CheckGekitotsu(j)
                    print("---------------------------------------------------------")

                except KeyError:
                    print(sys.exc_info())
                    er_log = open("log/error_query[%s].log" % (j['id']), "w")
                    er_log.write(json.dumps(j, indent=4, separators=(",", ':')))
                    er_log.close()

        time.sleep(STREAM_GET_INTERVAL)
    t4p.kill()
