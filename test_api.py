#!/usr/bin/env python

from utils import get_params
from CCW import CCW

params = get_params()
try:
    ccw = CCW(**params)
    if ccw.send_hello():
        print('Hello successful')
    else:
        print('ERROR: send_hello() returned False?!')
except Exception as e:
    print('ERROR: ' + str(e))
