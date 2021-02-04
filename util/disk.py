import os
import re
import subprocess


def sh(command, print_msg=True):
    p = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    result = p.stdout.read().decode('gbk')
    if print_msg:
        print(result)
    return result


def usbpath():
    u = []
    if os.name == 'nt':
        disks = sh("wmic logicaldisk get deviceid,description,VolumeName",
                   print_msg=False).split('\n')
        for disk in disks:
            if 'Removable' in disk or '可移动磁盘' in disk:
                u += [(re.search(r'\w:', disk).group(), disk)]
        return u
    elif os.name == 'posix':
        return sh('ll -a /media')[-1].strip()
    else:
        return sh('ls /Volumes')[-1].strip()


if __name__ == '__main__':
    print(usbpath())
