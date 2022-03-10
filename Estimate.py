"""
class definition for CCW estimates
"""

import xmltodict
from natsort import natsorted

from typing import List


def find_attribute(itemlist, attribute):
    '''
    Checks for a @typeCode or @name attribute value in a dict or list of dicts
    and returns the corresponding #text attribute ('' if not #text is found)
    Returns None if the attribute value is not found.
    '''
    if not isinstance(itemlist, list):
        itemlist = [itemlist]

    for item in itemlist:
        attr = item.get('@typeCode') or item.get('@name')
        if attr == attribute:
            return item.get('#text')
    else:
        return None


class EstimateError(Exception):
    pass


class Estimate(object):
    '''
    Estimate object attributes:
     <todo>
    '''
    def __init__(self, xml_response, **kwargs):
        """
        Set up a CCW Estimate object based on API data retrieved from CCW acquireEstimate API response (passed as XML string).
        """
        # comvert xml response to dictionary to make parsing easier...
        self._estimate_response = xmltodict.parse(xml_response, dict_constructor=dict)
        quote_dict = self._estimate_response['soapenv:Envelope']['soapenv:Body']['AcknowledgeQuote']['DataArea']['Quote']

        # under 'Quote' we do have two subdirectories: QuoteHeader and QuoteLine. Message under QuoteHeader will
        # containg some info if query was not successful. If it was successfull Message is not present and we
        # will go for the QuoteLines that contain all the items of the estimate
        try:
            # if the quote lookup was not successful, reason is found in descrption
            message = quote_dict['QuoteHeader']['Message']['Description']
            if message:
                raise EstimateError(f"Error retrieving quote {kwargs.get('estimate_id')}:  {message}")
        except KeyError:
            pass

        self.estimate_id = quote_dict['QuoteHeader']['ID']['#text']
        self.status = quote_dict['QuoteHeader']['Status']['Reason']
        try:
            self.estimate_name = find_attribute(quote_dict['QuoteHeader']['Extension']['ValueText'], "Estimate Name")
        except KeyError:
            self.estimate_name = None

        items = {}
        # if an estimate only has a single line, xmltodict only returns
        # a single instance of a dict (not a list of dict).. sic
        if isinstance(quote_dict['QuoteLine'], list):
            lines = quote_dict['QuoteLine']
        else:
            lines = [quote_dict['QuoteLine']]

        for v in lines:
            try:
                lineitem = find_attribute(v['Item']['Specification']['Property']['NameValue'], 'CCWLineNumber')
            except AttributeError:
                lineitem = None

            if not lineitem:
                continue

            item = {
                'sku': v['Item']['ID']['#text'],
                'description': v['Item'].get('Description', ''),
                'quantity': int(v['Item']['Extension']['Quantity']['#text']),
                '_lineid': v['LineNumberID'],
                'lineitem': lineitem,
            }
            items[lineitem] = item

        # sort the dict by lineitem in natural order
        self.quotelines = {k: items[k] for k in natsorted(items)}

    @property
    def get_quotelines(self) -> List:
        """get_quotelines

        returns a list of all quotelines

        """
        return self.quotelines.values()

    def display_estimate_detail(self):
        """
        display the estimate on stdout
        """
        message = f"Estimate ID  : {self.estimate_id}\n"
        message += f"Estimate Name: {self.estimate_name}\n"
        message += f"{'Line':8}  {'Qty':6}  {'Sku':21}  {'Description':60}\n"
        message += f"{'-------':8}  {'------':6}  {'--------------------':21}  " \
                   f"{'----------------------------------------------------------':60}\n"

        for k, v in self.quotelines.items():
            # some fileds are not always present, so better check upfront
            message += f"{k: <8} {v['quantity']:<6} {v['sku']:<21}  {v['description']:<60}\n"

        print(message)


if __name__ == '__main__':
    # for debugging
    from utils import get_params
    from CCW import CCW
    params = get_params()
    ccw = CCW(**params)
    e = ccw.get_estimate('xxxx')
    e.display_estimate_detail()
