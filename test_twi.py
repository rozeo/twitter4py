#coding: utf-8

#branch分けしました

import time
import my_key
from twitter4py import twitter4py
from twitter4py import ConvUTC2JST
        
if __name__ == '__main__':
    t4p = twitter4py(my_key.CONS_KEY,my_key.CONS_KEY_SEC,my_key.ACC_TOK,my_key.ACC_TOK_SEC)
    j = t4p.CreateUserStreaming({"with":"followings","replies":"all"})
    
    while True:
        js = t4p.StreamNewResponse()
        if js:
            for j in js:
                try:
                    print("[" + ConvUTC2JST(j['created_at']) + "] " + j["user"]["name"] + " (@" + j["user"]["screen_name"] + ")\n" + j['text'] + "\n")
                except KeyError:
                    pass
                except NameError:
                    pass
        time.sleep(0.5)
    t4p.kill()
        
    
   
