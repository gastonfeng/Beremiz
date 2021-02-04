with open('plc.bin', 'w') as f:
    for i in range(20):
        for j in range(536):
            f.write(str(chr(0x30 + i)))
