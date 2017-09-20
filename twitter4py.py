# coding: utf-8

# branch分けしました

import json
import requests
import time
import threading
import re
import collections
from requests_oauthlib import OAuth1
import calendar

URL_BASE = "https://api.twitter.com/1.1/"
USER_STREAM_ENDPOINT = "https://userstream.twitter.com/1.1/user.json"
FOLLOW_DEFAULT = -1
CONNECTION_RETRY_INTERVAL = 3


# created_at が +0000(UTC)なのを +0900(JST)に治す
def ConvUTC2JST(created_at):
    time_utc = time.strptime(created_at, '%a %b %d %H:%M:%S +0000 %Y')
    unix_time = calendar.timegm(time_utc)
    time_jst = time.localtime(unix_time)
    return time.strftime("%Y/%m/%d %H:%M:%S", time_jst)


class twitter4py:

    # OAuthトークン生成と基本情報をとってくる
    def __init__(self, CONS_KEY, CONS_KEY_SEC, ACC_TOK, ACC_TOK_SEC):

        self.created_stream = False
        self.auth_info = OAuth1(CONS_KEY, CONS_KEY_SEC, ACC_TOK, ACC_TOK_SEC)
        req = requests.get(URL_BASE + "account/verify_credentials.json",
                           auth=self.auth_info).json()
        self.id = req['id']
        self.scr_name = req['screen_name']
        print("user id: %d\nscreen_name: %s\n" % (self.id, self.scr_name))

    # acount/verify_credentials でとったuser_idだけ取得する 正直いらない
    def userid(self):
        return self.user_id

    #
    # method   => "GET" か "POST"
    # endpoint => ex. statuses/update 末尾.jsonはあってもなくても可
    # data     => GETの場合のクエリ文字列、POSTの場合のPOSTデータ dict型

    def request(self, method, endpoint, data):
        url = URL_BASE + endpoint
        if not re.match(".json", url):
            url += ".json"
        if method == 'GET':
            return requests.get(url, auth=self.auth_info, params=data).json()
        if method == 'POST':
            return requests.post(url, auth=self.auth_info, data=data).json()
        else:
            return ""

    #
    # qs => "follow":"@~~" とか "track":"~~~" とか dict型
    #

    def CreateUserStreaming(self, qs):
        if not self.created_stream:
            self.created_stream = True
        else:
            return -1

        self.qs = qs

        self.kill_thread = threading.Event()
        self.stream = threading.Thread(target=self.__get_tweet)
        self.stream.setDaemon(True)

        # レスポンス保存用キュー
        self.queue = collections.deque()

        self.stream.start()

    # user streaming 取得スレッド関数
    def __get_tweet(self):
        while not self.kill_thread.is_set():
            try:
                req = requests.get(USER_STREAM_ENDPOINT, auth=self.auth_info,
                                   stream=True, params=self.qs)
                print("Connecting User Stream")

                for d in req.iter_lines():
                    if not d:
                        continue
                    if self.kill_thread.is_set():
                        return
                    d = d.decode("utf-8")
                    if re.match("friends", d):
                        continue
                    self.queue.append(d)

            # 通信の確立失敗
            except requests.exceptions.ConnectionError:
                print("connection lost streaming api, Retry after 10 sec")
                time.sleep(CONNECTION_RETRY_INTERVAL)
            except requests.exceptions.Timeout:
                print("Connection Timeout, Retry after 10 sec")
                time.sleep(CONNECTION_RETRY_INTERVAL)

    # メインからはこの関数を介してレスポンスを取得する
    def StreamNewResponse(self):
        jlist = []
        for i in range(len(self.queue)):
            j = json.loads(self.queue.popleft())

            # 最初に飛んでくるfriendsリストとdeleteクエリは読まない
            if ("friends" in j) is False:
                if ("delete" in j) is False:
                    jlist.append(j)
        return jlist

    # スレッドキル用、ただしむりやりバツで閉じたほうが早い(req.iter_linesの関係上)
    def kill(self):
        self.kill_thread.set()
        self.stream.join()
