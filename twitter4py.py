# coding: utf-8
#!/home/roz-dev/bin/python3.6

# branch分けしました

import json
import requests
import time
from datetime import datetime
import threading
import re
import collections
from requests_oauthlib import OAuth1
import calendar

# endpointのURL
URL_BASE                    = "https://api.twitter.com/1.1/"
USER_STREAM_ENDPOINT = "https://userstream.twitter.com/1.1/user.json"

# リトライするときのインターバル時間を計算するベース秒
# 連続した回数に対して線形に増やしていく、 _MAXで最大待ち時間を指定
CONNECTION_RETRY_INTERVAL       = 10
CONNECTION_RETRY_INTERVAL_MAX = 600

# タイムアウトさせる秒数
TIMEOUT_LIMIT = 300


# created_at が +0000(UTC)なのを +0900(JST)に治す
def ConvUTC2JST(created_at):
	time_utc = time.strptime(created_at, '%a %b %d %H:%M:%S +0000 %Y')
	unix_time = calendar.timegm(time_utc)
	time_jst = time.localtime(unix_time)
	return time.strftime("%Y/%m/%d %H:%M:%S", time_jst)


class twitter4py:

	# OAuthトークン生成と基本情報をとってくる
	def __init__(self, CONS_KEY, CONS_KEY_SEC, ACC_TOK, ACC_TOK_SEC, disp_userinfo = False):

		self.created_stream = False
		self.auth_info = OAuth1(CONS_KEY, CONS_KEY_SEC, ACC_TOK, ACC_TOK_SEC)
		req = requests.get(URL_BASE + "account/verify_credentials.json",
									  auth=self.auth_info).json()
		self.id = req['id']
		self.scr_name = req['screen_name']
		self.name = req["name"]

		if disp_userinfo:
			print("user id: %d\nscreen_name: %s\n" % (self.id, self.scr_name))
		
		# 共通のデバッグ出力用ファイル名
		self.debug_log_name = "debug.log"
		
		# 読み込み済みクエリ数カウンタ
		self.stat_loaded_tweet = 0
		
	def debug_log(self,_str):
		debug = open(self.debug_log_name, "a")
		debug.write(_str)
		debug.close()

	#
	# method    => "GET" か "POST"
	# endpoint => ex. statuses/update 末尾.jsonはあってもなくても可
	# data       => GETの場合のクエリ文字列、POSTの場合のPOSTデータ dict型
	#

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
	# UserStreamをオープンしてサブスレッド上で動かす
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
		return 0

	# user streaming 取得スレッド関数
	def __get_tweet(self):
		timeout_times = 0
		connect_error_times = 0
		while not self.kill_thread.is_set():
			try:
				latest_tweet_ts = time.time()
				
				# keep-aliveすら流れてこない場合があるため一定時間でタイムアウトさせ再接続する
				req = requests.get(USER_STREAM_ENDPOINT, auth=self.auth_info,
											stream=True, params=self.qs, timeout=TIMEOUT_LIMIT)
				# print("Connecting User Stream")
				
				# connection系エラーのカウンタをリセット
				timeout_times           = 0
				connect_error_times = 0

				for d in req.iter_lines():
					# スレッド停止要求がある場合は抜ける
					if self.kill_thread.is_set():
						return
					
					# keep-alive等のnullパケット
					if not d:
						continue
 
					# それ以外の場合最終ツイート取得時間のタイムスタンプを更新してキューにプッシュ
					latest_tweet_ts = time.time()
					self.queue.append(d.decode("utf-8"))
				
					self.stat_loaded_tweet += 1

			# 通信の確立失敗
			except requests.exceptions.ConnectionError:
				nt = datetime.fromtimestamp(time.time())
				wait_time = CONNECTION_RETRY_INTERVAL * (connect_error_times + 1)
				connect_error_times += 1
				if wait_time > CONNECTION_RETRY_INTERVAL_MAX:
					wait_time = CONNECTION_RETRY_INTERVAL_MAX

				print("connection lost streaming api, Retry after %d sec" % wait_time)
				self.debug_log("[%d/%02d/%02d %02d:%02d:%02d] connection lost streaming api, Retry after %d sec\n" %
									  (nt.year, nt.month, nt.day, nt.hour, nt.minute, nt.second, wait_time))
				time.sleep(wait_time)

			# Timeout系は一括処理
			except requests.exceptions.Timeout or socket.timeout or urllib3.exceptions.ReadTimeoutError:
				nt = datetime.fromtimestamp(time.time())
				wait_time = CONNECTION_RETRY_INTERVAL * (timeout_times + 1)
				timeout_times += 1
				if wait_time > CONNECTION_RETRY_INTERVAL_MAX:
					wait_time = CONNECTION_RETRY_INTERVAL_MAX

				print("Connection Timeout, Retry after %d sec" % wait_time)
				self.debug_log("[%d/%02d/%02d %02d:%02d:%02d] Connection Retry" %
									  (nt.year, nt.month, nt.day, nt.hour, nt.minute, nt.second))
				time.sleep(wait_time)

	# メインからはこの関数を介してレスポンスを取得する
	def StreamNewResponse(self):
		jlist = []
		
		# キューからクエリから取り出してjsonエンコードしたあとリストにして返す
		for i in range(len(self.queue)):
			jlist.append(json.loads(self.queue.popleft()))
		return jlist
	
	# ストリーム監視の状態
	def UserStreamingStatus(self,t4p_bot , json, option_str = ""):
		if json["user"]["screen_name"] != "rozeo_s":
			return
		
		if self.created_stream:
			nt = datetime.fromtimestamp(time.time())
			message		= "[%d/%02d/%02d %02d:%02d:%02d]\n" % (nt.year, nt.month, nt.day, nt.hour, nt.minute, nt.second)
			message   += "Bot Status: Active\n"
			message	  += "LoadedStreamingQuery: %d\n" % self.stat_loaded_tweet
			
			t4p_bot.request("POST", "statuses/update", {"status":  "@rozeo_s\n" + message + option_str, "in_reply_to_status_id": json["id"]})

	# スレッドキル用、ただしむりやりバツで閉じたほうが早い(req.iter_linesの関係上)
	def kill(self):
		self.kill_thread.set()
		self.stream.join()
