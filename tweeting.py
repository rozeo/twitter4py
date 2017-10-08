#!/bin/python3.6
# coding: utf-8
import my_key
from twitter4py import twitter4py

if __name__ == "__main__":
    t4p = twitter4py(
                     my_key.CONS_KEY,
                     my_key.CONS_KEY_SEC,
                     my_key.ACC_TOK,
                     my_key.ACC_TOK_SEC
                    )

    while True:
        tweet_str = ""
        print("---------------------------------------------------------")
        print("tweet text:")
        while True:
            inp = input()
            if inp == "":
                break
            else:
                tweet_str += inp + "\n"

        if tweet_str == "":
            break

        t4p.request("POST", "statuses/update", {"status": tweet_str})

        print()
