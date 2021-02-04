import requests

url = 'http://192.168.31.100'

# files = {'name':'plc.bin','filename':'plc.bin','data': open('plc.bin', "rb")}
with open('plc.bin', "rb") as f:
    print(len(f.read()))
requests.post('%s/upload' % (url), files={'plc.bin': open('plc.bin', "rb")})

while False:
    try:
        print(requests.get(url))
        print(requests.get(url + '/MatchMD5'))
        print(requests.post(url + '/GetTraceVariables'))
    except:
        print('error')
