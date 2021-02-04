import os

packages = {
    "NTPClient": 'https://gitee.com/kaikong/NTPClient.git',
    'TraceRecorder': 'https://gitee.com/kaikong/TraceRecorder.git',
    'LwIP': 'https://gitee.com/kaikong/LwIP.git',
    'STM32Ethernet': 'https://gitee.com/kaikong/STM32Ethernet.git',
    'ShiftRegister74HC595': 'https://gitee.com/kaikong/ShiftRegister74HC595.git',
    'pt100_hx711': 'https://gitee.com/kaikong/pt100_hx711.git',
    'debouncer': 'https://gitee.com/kaikong/debouncer.git',
    'USBStick_stm32': 'https://gitee.com/kaikong/USBStick_stm32.git',
    'ArduinoHttpClient': 'https://gitee.com/kaikong/ArduinoHttpClient.git',
    'littlefs': 'https://gitee.com/kaikong/littlefs.git',
    'ad7689': 'https://gitee.com/kaikong/ad7689.git',
    'ch423': 'https://gitee.com/kaikong/ch423.git',
    'Rtc_Pcf8563': 'https://gitee.com/kaikong/Rtc_Pcf8563.git',
    'pt100rtd': 'https://gitee.com/kaikong/pt100rtd.git',
    'MCPDAC': 'https://gitee.com/kaikong/MCPDAC.git',
    'STM32_USB_Host_Library': 'https://gitee.com/kaikong/STM32_USB_Host_Library.git',
    'SPIFlash': 'https://gitee.com/kaikong/SPIFlash.git',
    'msgpack-arduino': 'https://gitee.com/kaikong/msgpack-arduino.git',
    'Q2-HX711-Arduino-Library': 'https://gitee.com/kaikong/Q2-HX711-Arduino-Library.git',
    'kt1260': 'https://gitee.com/kaikong/kt1260.git',
    'kt1264': 'https://gitee.com/kaikong/kt1264.git',
    'iec_types': 'https://gitee.com/kaikong/iec_types.git',
    'modbus': 'https://gitee.com/kaikong/modbus.git',
    'FatFs': 'https://gitee.com/kaikong/FatFs.git',
    'STM32FreeRTOS': 'https://gitee.com/kaikong/STM32FreeRTOS.git',
    'ArduinoJson': 'https://e.coding.net/kaikong/ArduinoJson.git',
    'xme802_4': 'https://gitee.com/kaikong/xme802_4.git',
    'zxa-07': 'https://gitee.com/kaikong/zxa-07.git',
    'tm7707': 'https://gitee.com/kaikong/tm7707.git',
    'protocol': 'https://gitee.com/kaikong/protocol.git',
    'board': 'https://gitee.com/kaikong/board.git',
    'PacketSerial': 'https://gitee.com/kaikong/PacketSerial.git',
    'softPLC': 'https://gitee.com/kaikong/softPLC.git',
    'plc_debug': 'https://gitee.com/kaikong/plc_debug.git',
    'plc_app': 'https://gitee.com/kaikong/plc_app.git',
    'XYmodem': 'https://gitee.com/kaikong/XYmodem.git',
    'plc_rte': 'https://gitee.com/kaikong/plc_rte.git',
    'dpjxx': 'https://gitee.com/kaikong/dpjxx.git',
    'retain_flash': 'https://gitee.com/kaikong/retain_flash.git',
    "CanFestival-3":"https://gitee.com/kaikong/CanFestival-3.git",
    'ArduinoRS485': 'https://gitee.com/kaikong/ArduinoRS485.git',
    'RA165':'https://gitee.com/kaikong/RA165.git',
    'swspi':'https://gitee.com/kaikong/swspi.git',
    'AccelStepper':'https://gitee.com/kaikong/AccelStepper.git',
    'ltc2496': 'https://gitee.com/kaikong/ltc2496.git',
    'TinyGSM': 'https://gitee.com/kaikong/TinyGSM.git',
    'bacnet': 'https://gitee.com/kaikong/bacnet-stack.git',
    'retain_mcu': 'https://gitee.com/kaikong/retain_mcu.git',
    'SimpleKalmanFilter': 'https://gitee.com/kaikong/SimpleKalmanFilter.git',
    'FlashDB': 'https://gitee.com/kaikong/FlashDB.git'
}

flagWithPackage = {'USE_USBH': ['FatFs', 'STM32_USB_Host_Library', 'USBStick_stm32'], 'USE_NTPClient': ["NTPClient"],
                   'TRC_USE_TRACEALYZER_RECORDER': ['TraceRecorder']}


def _local_package(package, mt):
    return '%s/%s.zip' % (os.path.join(mt, 'library'), package)


def flag2package(flags):
    pks = []
    for f in flags:
        if not flags[f]: continue
        pk = flagWithPackage.get(f)
        if pk: pks += pk
    return pks


def package_get(logger, label_dict, libs, exclude, mt):
    plist = []
    use_local = label_dict.get('LOCAL_PACKAGE')
    if use_local:
        logger.write(_("Use Local Package.\n"))
    else:
        logger.write(_("Use Net Package.\n"))
    lst = flag2package(label_dict) + libs
    lst = list(set(lst))
    lst = [x for x in lst if x not in exclude]
    for label in lst:
        package = packages.get(label)
        if package:
            if use_local:
                pkg = _local_package(label, mt)
            else:
                pkg = packages[label]
            if pkg: plist.append(pkg)
    return plist
