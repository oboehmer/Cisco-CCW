# Parse order and serial information into a structured object
# some code reused from https://github.com/CiscoSE/ccwquery/blob/master/ccwparser.py
import re
from datetime import datetime

import pandas as pd


class Order(object):
    '''
    Order object attributes:
    - billtoparty
    - party
    - status
    - salesorder
    - shiptoname
    - lineitems  (list of dicts, key'ed by linenumber (i.e. 1.0, 2.0, 2.0.1, etc.))
        sku
        description
        quantity
        amount
        promiseddelivery
        serials: (list of serial numbers, only filled for toplevel items)
        shipset

    - display_order_detail()
        prints order details in a table on the screen
    '''
    def __init__(self, checkorder_response, toplevel_only=True):    # noqa, C901
        '''
        Set up a CCW Order object based on API data retrieved from CCW checkOrderStatus API response (passed as dict/json).
        By default we only track toplevel line items (i.e. 1.0, 2.0, 3.0), so the object only holds those. You can set
        toplevel_only arg to False to change this.
        Note: Serial numbers are only retrieved for top-level line items at the moment.
        '''
        self.checkorder_response = checkorder_response

        po_header = self.checkorder_response['ShowPurchaseOrder']['value']['DataArea']['PurchaseOrder'][0]['PurchaseOrderHeader']

        self.billtoparty = po_header['BillToParty']['Name'][0]['value']
        self.party = po_header['Party'][0]['Name'][0]['value']
        self.status = po_header['Status'][0]['Description']['value']
        self.salesorder = po_header['SalesOrderReference'][0]['ID']['value']
        self.orderdate = po_header['OrderDateTime']
        for l in po_header['DocumentReference']:
            if l['typeCode'] == 'OrderName':
                self.ordername = l['ID']['value']
                break
        else:
            self.ordername = ''
        self.shiptoname = po_header['ShipToParty']['Name'][0]['value']
        try:
            a = []
            for l in po_header['ShipToParty']['Location'][0]['Address'][0]['AddressLine']:
                a.append(l['value'])
            a.append(po_header['ShipToParty']['Location'][0]['Address'][0]['CityName']['value'])
            a.append(po_header['ShipToParty']['Location'][0]['Address'][0]['CountryCode']['value'])
            self.shiptoaddress = ', '.join(a)
        except KeyError:
            self.shiptoaddress = 'unknown/error'

        try:
            self.shiptocontactname = po_header['ShipToParty']['Contact'][0]['PersonName'][0]['GivenName']['value']
        except KeyError:
            self.shiptocontactname = 'unknown/error'

        try:
            for l in po_header['ShipToParty']['Contact'][0]['TelephoneCommunication']:
                if l['typeCode'] == 'Phone':
                    self.shiptocontactphone = l['ID'][0]['value']
                    break
            else:
                self.shiptocontactphone = ''
        except KeyError:
            self.shiptocontactphone = 'unknown/error'

        try:
            self.shiptocontactemail = po_header['ShipToParty']['Contact'][0]['EMailAddressCommunication'][0]['ID'][0]['value']
        except KeyError:
            self.shiptocontactemail = 'unknown/error'

        self.amount = po_header['TotalAmount']['value']
        self.currencycode = po_header['TotalAmount']['currencyCode']
        # add all the lineitems
        lineitems = self.checkorder_response['ShowPurchaseOrder']['value']['DataArea']['PurchaseOrder'][0]['PurchaseOrderLine']

        self.lineitems = {}
        for l in lineitems:
            linenumber = l['SalesOrderReference']['LineNumberID']['value']

            is_toplevel = (re.match(r'\d+\.0$', linenumber) is not None)
            if toplevel_only and not is_toplevel:
                continue
            item = {'sku': l['Item']['ID']['value'],
                    'description': l['Item']['Description'][0]['value'],
                    'quantity': l['Item']['Lot'][0]['Quantity']['value'],
                    'amount': l['ExtendedAmount']['value'],
                    'promiseddelivery': l.get('PromisedDeliveryDateTime', ''),
                    }
            try:
                item['requesteddelivery'] = l['FulfillmentTerm'][0]['RequestedDeliveryDate']
            except KeyError:
                item['requesteddelivery'] = ''
            try:
                item['status'] = l['Status'][0]['Code']['value']
            except KeyError:
                item['status'] = ''

            if item['status'] == 'Closed':
                try:
                    if l['Status'][0]['Extension'][0]['typeCode'] == 'ShipmentDate':
                        item['shipdate'] = l['Status'][0]['Extension'][0]['DateTime'][0]['value']
                except KeyError:
                    item['shipdate'] = 'not found'

                item['Tracking Number'] = item['Tracking URL'] = ''
                for step in l.get('TransportStep', []):
                    for t in step['TransportationTerm'][0]['Description']:
                        if t.get('typeCode', '') == 'Tracking Number':
                            item['Tracking Number'] = t.get('value', '')
                        if t.get('typeCode', '') == 'Tracking URL':
                            item['Tracking URL'] = t.get('value', '')
                            break
                    if item['Tracking URL']:
                        break
            else:
                item['Tracking Number'] = item['Tracking URL'] = ''
                item['shipdate'] = ''

            # set keys we might set later
            item.update({
                'serials': [],
                'shipset': '',
            })

            self.lineitems[linenumber] = item

    def _search_lineitem(self, linenumber, sku, quantity):
        '''
        retrieve a  product lineID based on the major line number, SKU and quantity.
        Return product lineID
        '''
        m = re.match(r'(\d+\.)', linenumber)
        if not m:
            start_match = ''
        else:
            start_match = m.group(1)
        for k, v in self.lineitems.items():
            if k.startswith(start_match) and v['sku'] == sku and str(v['quantity']) == str(quantity):
                return k
        else:
            return None

    @staticmethod
    def _convert_date(datestring, dateformat='text'):
        '''
        convert time strings 2021-09-14T06:11:16Z to a dateformat, which can be
        'text' (returns 14-Sep-2021), 'datetime' (returns python datetime.datetime object),
        'pandas' (pd.Timestamp)
        '''
        if dateformat.lower() == 'text':
            nonevalue = ''
        elif dateformat.lower() == 'datetime':
            nonevalue = None
        elif dateformat.lower() == 'pandas':
            nonevalue = None
        else:
            raise ValueError('Unknown dateformat passed')

        if not datestring:
            return nonevalue
        if datestring.endswith('Z'):
            datestring = datestring[:-1]
        try:
            d = datetime.fromisoformat(datestring)
        except ValueError:
            return nonevalue

        if dateformat.lower() == 'text':
            return d.strftime('%d-%b-%Y')
        elif dateformat.lower() == 'datetime':
            return d
        elif dateformat.lower() == 'pandas':
            return pd.Timestamp(d)
        else:
            assert False, "we shouldn't end here"

    def add_serial_data(self, serialdata):
        '''
        add serial data to the order object (this one is retrieved through different API call)
        '''
        for linenumber, item in serialdata.items():
            order_linenumber = self._search_lineitem(linenumber, item['sku'], item['quantity'])
            if order_linenumber:
                self.lineitems[order_linenumber]['serials'] = [e['serialNumber'] for e in item['serials'] if 'serialNumber' in e]
                self.lineitems[order_linenumber]['shipset'] = item['shipset']
            # else:
            #     print(f'Warning: line number in order not found for serial linenumber {linenumber}')

    def display_order_detail(self, display_serials=False):
        """
        display_order_detail - This method will display to the screen the details of the line items of the order.
        :param toplevel_only: This parameter specifies if we want to only display the top order part number
                as opposed to all the sub line items.
        :return: none
        """
        message = 'Sales Order: {}\n'.format(self.salesorder)
        message += 'Order Name : {}\n'.format(self.ordername)
        message += 'Order Date : {:10.10}\n'.format(self._convert_date(self.orderdate))
        format_string = '{:8}  {:>6} {:20}  {:60} {:10}  {:11} {:11} {:11} {:7}\n'
        message += format_string.format(
            'Line', 'Qty', 'Sku', 'Description', 'Status', 'Requested', 'Promised', 'Ship Date', 'Shipset'
        )
        message += format_string.format(
            '-----', '------', '--------------------',
            '-----------------------------------------------------',
            '----------', '-----------', '-----------', '-----------', '-------'
        )

        for k, v in self.lineitems.items():
            message += '{:<8}  {:>6} {:<20}  {:<60.60} {:<10.10}  {:<11.11} {:<11.11} {:<11.11} {:>7}\n'.format(
                k, str(v['quantity']), v['sku'], v['description'], v['status'],
                self._convert_date(v['requesteddelivery']),
                self._convert_date(v['promiseddelivery']),
                self._convert_date(v['shipdate'] or ''),
                v['shipset'] or ''
            )
            if display_serials and v['serials']:
                message += '{:<8}  {:<6} {}\n'.format('', '', ','.join(v['serials']))
        print(message)

    def return_order_details(self, dateformat='text'):
        """
        Return the order details as a list of dictionaries, which can be easily exported into
        Excel
        """
        result = []
        for k, v in self.lineitems.items():
            line = {}
            line['SO Number'] = self.salesorder
            line['SO Name'] = self.ordername
            line['SO Date'] = self._convert_date(self.orderdate, dateformat=dateformat)

            # pull out known attributes, and then append other line items which might have been added
            # later. this avoids having to adjust this function whenever we add a new method.
            item = dict(v)
            line['Line Number'] = k
            line['Quantity'] = item.pop('quantity')
            line['Item Name'] = item.pop('sku')
            line['Item Description'] = item.pop('description')
            line['Line Status'] = item.pop('status')
            line['Requested Delivery'] = self._convert_date(item.pop('requesteddelivery'), dateformat=dateformat)
            line['Promised Delivery'] = self._convert_date(item.pop('promiseddelivery'), dateformat=dateformat)
            line['Ship Date'] = self._convert_date(item.pop('shipdate'), dateformat=dateformat)
            line['Shipset'] = item.pop('shipset', '')
            line['Serial Numers'] = ' '.join(item.pop('serials', []))
            line['Ship-To Name'] = self.shiptoname
            line['Ship-To Address'] = self.shiptoaddress
            line['Ship-To Contact'] = self.shiptocontactname
            line['Ship-To Contact Phone'] = self.shiptocontactphone
            line['Ship-To Contact Email'] = self.shiptocontactemail

            line.update(item)
            result.append(line)

        return result
