# Running the locust.io load test

## Setup
```
mkvirtualenv europa.testing
workon europa.testing
pip install locust
```

## Run Load Tests
```
locust -H http://localhost:9080 -f locust.io/load_authorization.py --no-web -c 500 -r 10 -n 10000
```
