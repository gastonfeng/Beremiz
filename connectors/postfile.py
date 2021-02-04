import requests
import umsgpack


def postfile(ip, src, destname):
    try:
        files = {destname: open(src, "rb")}
        r = requests.post("http://%s/upload" % ip, files=files)
        if r.status_code == 200:
            return True
        return False

    except Exception as e:
        print(e)
    return False


if __name__ == '__main__':
    d = [(1021, False, None)]
    t = umsgpack.packb(d)
    while True:
        r = requests.get("http://192.168.31.156/GetPLCstatus")
        if r.status_code == 200:
            print(r.content)
        r = requests.post("http://192.168.31.156/SetTraceVariablesList", data=t)
        if r.status_code == 200:
            print(r.content)
        r = requests.post("http://192.168.31.156/GetTraceVariables")
        if r.status_code == 200:
            print(r.content)

    postfile('192.168.31.156', 'mDns.py')
