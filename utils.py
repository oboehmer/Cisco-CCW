import getpass
import os


PARAMS = {
    'ccw_clientid': {'descr': 'CCW Client ID', 'default': 'insert_client_id'},
    'ccw_clientsecret': {'descr': 'CCW Client Secret', 'secret': True},
    'cco_username': {'descr': 'CCO Username', 'default': getpass.getuser()},
    'cco_password': {'descr': 'CCO Password', 'secret': True},
}


def get_params(interactive=True):
    result = {}
    for var, params in PARAMS.items():
        # retrieve var from environment (in upper case)
        value = os.environ.get(var.upper(), params.get('default'))
        if not value:
            if not interactive:
                raise ValueError('cannot derive {}, please set environment variable {} accordingly'.format(
                    params['descr'], var
                ))
            else:
                if params.get('secret'):
                    input_func = getpass.getpass
                else:
                    input_func = input
                value = input_func('Please enter {}: '.format(params['descr']))
        result[var] = value
    return result
