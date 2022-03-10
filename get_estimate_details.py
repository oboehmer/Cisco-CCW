#!/usr/bin/env python
import argparse
import traceback

from CCW import CCW
from utils import get_params
from Estimate import EstimateError

parser = argparse.ArgumentParser(description='Get Estimate Details')
parser.add_argument('estimates', metavar='ID#', nargs='+',
                    help='one or more CCW estimate IDs')

args = parser.parse_args()
params = get_params()
ccw = CCW(**params)

for estimate in args.estimates:
    try:
        print('Checking for order {}'.format(estimate))
        ccw.get_estimate(estimate).display_estimate_detail()
    except EstimateError as e:
        print('Error retrieving {}: {}'.format(estimate, str(e)))
    except Exception as e:
        print('Error processing {}: {}'.format(estimate, str(e)))
        print(traceback.format_exc())
