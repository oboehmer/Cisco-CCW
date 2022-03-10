#!/usr/bin/env python
import argparse
import sys
import traceback
import pandas as pd

from CCW import CCW
from utils import get_params

parser = argparse.ArgumentParser(description='Get Order Status')
parser.add_argument('orders', metavar='SO#', type=str, nargs='+',
                    help='one or more sales order numbers')
parser.add_argument('--collect-sublevels', action='store_true', default=False,
                    help='collect and report non-toplevel items')
parser.add_argument('--show-serials', action='store_true', default=False,
                    help='show serial numbers')
parser.add_argument('--excel-output', type=str, default=None,
                    help='output as excel')

args = parser.parse_args()
params = get_params()
ccw = CCW(**params)

toplevel_only = args.collect_sublevels is False

if args.excel_output and not args.excel_output.endswith('.xlsx'):
    print('Error: excel output file must end with .xslx')
    sys.exit(1)

excel_lines = []
for so in args.orders:
    try:
        print('Checking for order {}'.format(so))
        order = ccw.get_order_status(sales_order=so, toplevel_only=toplevel_only, add_serials=True)
        if not args.excel_output:
            order.display_order_detail(display_serials=args.show_serials)
        else:
            excel_lines += order.return_order_details(dateformat='pandas')
            print(f'Collected {len(excel_lines)} line(s)')
    except Exception as e:
        print('Error while processing {}: {}'.format(so, str(e)))
        print(traceback.format_exc())

if args.excel_output:
    if len(excel_lines):
        pd.DataFrame(excel_lines).to_excel(args.excel_output, index=False)
        print(f'Created Excel file {args.excel_output}')
    else:
        print('No lines collected, excel file not created')
