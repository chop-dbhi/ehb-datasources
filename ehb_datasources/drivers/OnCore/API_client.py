from django.conf import settings
import requests
from requests.auth import HTTPBasicAuth
import xml.etree.ElementTree as ET


def create_api_request(api_Usr, api_pass, payload):

    url = "https://oncoretest.research.chop.edu/opas/OpasService"

    querystring = {"wsdl":""}

    auth=HTTPBasicAuth(api_Usr, api_pass)
    headers = {
        'content-type': "text/xml",
        'cache-control': "no-cache",
        }

    response = requests.request("POST", url, auth=auth, data=payload, headers=headers, params=querystring)
    # response = requests.post(url, auth=auth, data=payload, headers=headers, params=querystring)

    print(response.text)

def getProtocolSubjects(protocolID):
    # question - should ResearchCenterSubjectsOnly always be false?
    print (protocolID)

    payload = "<soapenv:Envelope xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\" xmlns:ser=\"http://service.opas.percipenz.com\"> \
                <soapenv:Header/> \
                    <soapenv:Body> \
                        <ser:ProtocolSubjectsRequest> \
                            <ProtocolNo>981</ProtocolNo> \
                            <ResearchCenterSubjectsOnly>false</ResearchCenterSubjectsOnly> \
                        </ser:ProtocolSubjectsRequest> \
                    </soapenv:Body> \
                </soapenv:Envelope>"

    create_api_request(settings.ONCORE_API_USERID, settings.ONCORE_API_PASS, payload)

def create_xml_get_protocol_Subjects(protocolID):
    print (protocolID)
    a = ET.Element('soapenv:Envelope')
    ET.SubElement(a, "{http://schemas.xmlsoap.org/soap/envelope/}soapenv")
    ET.SubElement(a, "{http://service.opas.percipenz.com\}ser")
    b = ET.SubElement(a,'soapenv:Header')
    ET.dump(a)

#getProtocolSubjects(981)
create_xml_get_protocol_Subjects(981)
