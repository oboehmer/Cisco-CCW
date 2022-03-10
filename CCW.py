import json
from datetime import datetime

import requests
from Estimate import Estimate
from Order import Order


def get_timestamp():
    """
    get timestamp
    """
    return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')


class CCW:
    """
    Implements basic CCW API methods.
    """
    sso_url = 'https://cloudsso.cisco.com/as/token.oauth2'
    token = None

    def __init__(self, cco_username, cco_password, ccw_clientid, ccw_clientsecret, base_url=None):
        self.cco_username = cco_username
        self.cco_password = cco_password
        self.ccw_clientid = ccw_clientid
        self.ccw_clientsecret = ccw_clientsecret
        self.base_url = base_url or 'https://api.cisco.com/'

        if not self.get_token():
            raise Exception(
                'Cannot authenticate to CCW, incorrect credentials?')

    def get_token(self):
        """
        Retrieve a (new) token and store within the object
        """
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
        }

        payload = 'client_id={}&client_secret={}&grant_type=password&username={}&password={}'.format(
            self.ccw_clientid, self.ccw_clientsecret, self.cco_username, self.cco_password
        )

        response = requests.request(
            "POST", self.sso_url, headers=headers, data=payload)
        if response.ok:
            self.token = response.json()['access_token']
        else:
            response.raise_for_status()
        return self.token is not None

    def send_hello(self):
        url = self.base_url + 'hello'
        headers = {
            'Authorization': 'Bearer ' + self.token,
        }

        response = requests.request("GET", url, headers=headers)
        if response.ok:
            return True
        else:
            response.raise_for_status()

    def get_order_status(self, sales_order, toplevel_only=True, add_serials=True):
        """
        Retrieve the order details and (if set) the serial numbers
        By default, only the toplevel line items (1.0, 2.0, etc.) are returned
        """
        # API documentation https://www.cisco.com/E-Learning/gbo-ccw/cdc_bulk/Cisco_Commerce_B2B_Implementation_Guides/Notifications/Order_Status_API/Order_Status_API_IG.pdf

        if 'api-test' in self.base_url:
            url = self.base_url + 'commerce/ORDER/POE/v2/sync/checkOrderStatus'
        else:
            url = self.base_url + 'commerce/ORDER/v2/sync/checkOrderStatus'

        headers = {
            'Authorization': 'Bearer ' + self.token,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

        query = {
            "GetPurchaseOrder": {
                "value": {
                    "DataArea": {
                        "PurchaseOrder": [
                            {
                                "PurchaseOrderHeader": {
                                    "ID": {
                                        "value": ""
                                    },
                                    "DocumentReference": [
                                        {
                                            "ID": {
                                                "value": ""
                                            }
                                        }
                                    ],
                                    "SalesOrderReference": [
                                        {
                                            "ID": {
                                                "value": str(sales_order)
                                            }
                                        }
                                    ],
                                    "Description": [
                                        {
                                            "value": "Yes",
                                            "typeCode": "details"
                                        }
                                    ]
                                }
                            }
                        ]
                    },
                    "ApplicationArea": {
                        "CreationDateTime": "datetime",
                        "BODID": {
                            "value": "BoDID-test",
                            "schemeVersionID": "V1"
                        }
                    }
                }
            }
        }

        response = requests.request(
            "POST", url, headers=headers, data=json.dumps(query))
        if not response.ok:
            print(response.text)
            response.raise_for_status()

        orderdata = response.json()

        # TODO: Verify success

        order = Order(checkorder_response=orderdata, toplevel_only=toplevel_only)
        # retrieve Serials
        if add_serials:
            try:
                serialdata = self.get_serials(sales_order)
                order.add_serial_data(serialdata)
            except Exception as e:
                print('ERROR adding serial number information to order {}:\n{}'.format(
                    sales_order, str(e)
                ))
        return order

    def get_serials(self, sales_order):
        """
        Retrieve serials for a given sales order.
        Return dict with line number as keys with serials and shipset number
        """
        # API DOcumentation at https://www.cisco.com/E-Learning/gbo-ccw/cdc_bulk/Cisco_Commerce_B2B_Implementation_Guides/Notifications/Get_SerialNumber_API/Get_Serial_Number_Details_API_IG.pdf
        url = self.base_url + 'commerce/ORDER/sync/getSerialNumbers'
        headers = {
            'Authorization': 'Bearer ' + self.token,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

        query = {
            "serialNumberRequest":
            {
                "salesOrderNumber": str(sales_order),
                "pageNumber": 1
            }
        }

        # response might be split across multiple pages, so keep track
        # on current page and execute the request multiple times when
        # needed
        total_pages = None
        current_page = 1
        results = {}
        while True:
            query['serialNumberRequest']['pageNumber'] = current_page
            response = requests.request(
                "POST", url, headers=headers, data=json.dumps(query))
            if not response.ok:
                print(response.text)
                response.raise_for_status()

            data = response.json()

            if data['serialNumberResponse']['responseHeader']['result'] != 'SUCCESS':
                raise Exception(data['serialNumberResponse']['responseHeader']['errorCode'] +
                                ':' + data['serialNumberResponse']['responseHeader']['message'])

            if total_pages is None:
                total_pages = int(
                    data['serialNumberResponse']['responseHeader']['totalPages'])
            # extract serials
            for l in data['serialNumberResponse']['serialDetails']['lines']:
                # only collect toplevel serial

                if l['lineNumber'] not in results:
                    results[l['lineNumber']] = {
                        'serials': l['serialNumbers'],
                        'shipset': l.get('shipSetNumber'),
                        'sku': l['partNumber'],
                        'quantity': l['quantity'],
                    }
                else:
                    results[l['lineNumber']]['serials'] += l['serialNumbers']

            if current_page == total_pages:
                break
            current_page += 1

        return results

    def get_estimate(self, estimate_id, **kwargs):
        """
        Retrieve details for an Estimate/BOM.
        Return Estimate object
        """
        # API Documentation at https://www.cisco.com/E-Learning/gbo-ccw/cdc_bulk/Cisco_Commerce_B2B_Implementation_Guides/Estimate/Manage_Estimate_Web_Services/Manage_Estimate_Web_Services_IG.pdf
        url = self.base_url + 'commerce/EST/v2/async/acquireEstimate'
        headers = {
            'Authorization': 'Bearer ' + self.token,
            'Content-Type': 'application/xml',
            'Accept': 'application/xml',
        }

        query = f'''<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
    <s:Header>
        <h:Messaging xmlns:h="http://docs.oasis-open.org/ebxml-msg/ebms/v3.0/ns/core/200704/"
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns="http://docs.oasis-open.org/ebxml-msg/ebms/v3.0/ns/core/200704/"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
            <UserMessage>
                <MessageInfo>
                    <Timestamp>{get_timestamp()}</Timestamp>
                    <MessageId>urn:uuid:20180213131730@eB2BPSTestTool.cisco.com</MessageId>
                </MessageInfo>
                <PartyInfo>
                    <From>
                        <PartyId>XYZ</PartyId>
                        <Role>http://example.org/roles/Buyer</Role>
                    </From>
                    <To>
                        <PartyId>ESTlistEstimateService.cisco.com</PartyId>
                        <Role>http://example.org/roles/Seller</Role>
                    </To>
                </PartyInfo>
                <CollaborationInfo/>
                <MessageProperties/>
                <PayloadInfo>
                    <PartInfo href="id:part@example.com">
                        <Schema location="http://www.cisco.com/assets/wsx_xsd/QWS/root.xsd" version="2.0"/>
                        <PartProperties>
                            <Property name="Description">WS Test Tool by Partner Services</Property>
                            <Property name="MimeType">application/xml</Property>
                        </PartProperties>
                    </PartInfo>
                </PayloadInfo>
            </UserMessage>
        </h:Messaging>
    </s:Header>
    <s:Body>
        <ProcessQuote releaseID="2014" versionID="1.0" systemEnvironmentCode="Production" languageCode="en-US"
            xmlns="http://www.openapplications.org/oagis/10">
            <ApplicationArea>
                <Sender>
                    <ComponentID schemeAgencyID="Cisco">B2B-3.0</ComponentID>
                </Sender>
                <CreationDateTime>2018-02-13</CreationDateTime>
                <BODID schemeAgencyID="Cisco">urn:uuid:20180213131730@eB2BPSTestTool.cisco.com</BODID>
                <Extension>
                    <Code typeCode="Estimate">Estimate</Code>
                </Extension>
            </ApplicationArea>
            <DataArea>
                <Quote>
                    <QuoteHeader>
                        <ID typeCode="Estimate ID">{estimate_id}</ID>
                        <Extension>
                        </Extension>
                    </QuoteHeader>
                </Quote>
            </DataArea>
        </ProcessQuote>
    </s:Body>
</s:Envelope>'''

        response = requests.request(
            "POST", url, headers=headers, data=query)
        if not response.ok:
            print(response.text)
            response.raise_for_status()
            # NOTREACHED

        # parse XML into our own Estimate object
        return Estimate(response.text, estimate_id=estimate_id)
