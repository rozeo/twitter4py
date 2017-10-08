# twitter4py

## Description
twitter api wrapper for python3

## Example
make class instance with COMSUMER_KEY, COMSUMER_SECRET_KEY, ACCESS_TOKEN, ACCESS_TOKEN_SECRET(get key from dev.twitter.com)
    
    t4p = twitter4py.twitter4py(COMSUMER_KEY, COMSUMER_SECRET_KEY, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    
### Request to REST APIs
#### GET Request
    
    t4p.request("GET", "account/verify_credentials")
    
#### POST Request

    t4p.request("POST", "statuses/update", {"status": "tweet text"})

### Create User Streaming
#### Create Streaming
    t4p.CreateUserStream({options})
