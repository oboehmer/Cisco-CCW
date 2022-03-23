# Repository to hold scripts to track orders or check estimates in Cisco Commerce Workspace (CCW)

## Installation Guide

1. Clone this repository to a folder and change directory into the folder
```
git clone hhttps://github.com/oboehmer/Cisco-CCW.git
cd Cisco-CCW
```

2. Set up a virtual environment in it and install the required packages

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=$(pwd)
``` 

3. Set the following environment variables: `CCO_PASSWORD` to your CEC password (if not set the scripts prompts you to add it) and `CCW_CLIENTSECRET` to the secret for your client. In Linux/MacOS, you can use the following commands in your Terminal (note that the `read -s ..` command does not each the password as you type it):

```
$ read -s CCO_PASSWORD
<enter your pass>
$ read -s CCW_CLIENTSECRET
<enter the secrect>
$ export CCO_PASSWORD CCW_CLIENTSECRET
```

The scripts also need to know your CCO username and CCW client ID. You can put the latter into utils.py as default, and/or populate them in the environment:

```
$ export CCO_USERNAME='xxxx'
$ export CCW_CLIENTID='xxxxxxxxxxxxxxxx'
```

4. Test the API and the setup of your environment:

```
$ python test_api.py 
Hello successful
```

5. Try to retrieve an order:

```
$ ./get_order_status.py 1234567890
```
You can use the options `--collect-sublevels` and/or `--show-serials` to show more than the main lineitems or to show serial numbers (only for the main lineitems).

6. Try to retrieve a quote/estimate

$ ./get_estimate_details.py 1234567890




## Using the CCW Modules 

Check the get_order_status.py or get_estimate_details as  example on how to use the CCW, Order and Estimate modules. The CCW object takes cco_username/password/client-secret/client-id information as required arguments, there is a method in utils.py which populates this based on the environment variable and defaults.


## CCW API Documentation:

- [Getting Started with CCW API](https://apiconsole.cisco.com/docs)
- [Order Status API Doc](https://www.cisco.com/E-Learning/gbo-ccw/cdc_bulk/Cisco_Commerce_B2B_Implementation_Guides/Notifications/Order_Status_API/Order_Status_API_IG.pdf)
- [Serial Number API Doc](https://www.cisco.com/E-Learning/gbo-ccw/cdc_bulk/Cisco_Commerce_B2B_Implementation_Guides/Notifications/Get_SerialNumber_API/Get_Serial_Number_Details_API_IG.pdf)
- [Estimate API Doc](https://www.cisco.com/E-Learning/gbo-ccw/cdc_bulk/Cisco_Commerce_B2B_Implementation_Guides/Estimate/Manage_Estimate_Web_Services/Manage_Estimate_Web_Services_IG.pdf)
