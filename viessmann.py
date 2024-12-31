import asyncio
import sys
import time
import os
import serial
import binascii
import enum
from datetime import datetime
import struct

# Valeur à modifier selon l'installation
PORT = '/dev/ttyUSB0'
DOMAIN = "vitoligno"
readCmds = [
             { 'addr':0x2610,'size':2,'conv':'Div10', 'unit':'℃', 'name':'Température ambiante effective', 'entity':'temperature_ambiante_effective' },
              { 'addr':0x0810,'size':2,'conv':'Div10', 'unit':'℃', 'name':'Température tampon 1', 'entity':'temperature_tampon_1' },
              { 'addr':0x0812,'size':2,'conv':'Div10', 'unit':'℃', 'name':'Température tampon 2', 'entity':'temperature_tampon_2' },
              { 'addr':0x0820,'size':2,'conv':'Div10', 'unit':'℃', 'name':'Température tampon 3', 'entity':'temperature_tampon_3' },
              { 'addr':0x0B16,'size':2,'conv':'Div10', 'unit':'℃', 'name':'Température de fumées', 'entity':'temperature_fumee' },
              { 'addr':0x0B12,'size':2,'conv':'Div10', 'unit':'℃', 'name':'Température chaudière', 'entity': 'temperature_chaudiere' },
              { 'addr':0x080E,'size':2,'conv':'Div10', 'unit':'℃', 'name':'Température extérieure', 'entity': 'temperature_exterieure'},
              { 'addr':0x2306,'size':2,'conv':'Int8', 'unit':'℃', 'name':'Consigne de température ambiante mode normal', 'entity': 'consigne_temperature_mode_normal'},
              { 'addr':0x2307,'size':2,'conv':'Int8', 'unit':'℃', 'name':'Consigne de température ambiante mode réduit', 'entity': 'consigne_temperature_mode_reduit'},
              { 'addr':0x081A,'size':2,'conv':'Div10', 'unit':'℃', 'name':'Température ECS solaire', 'entity': 'temperature_ecs_solaire'},
              { 'addr':0x6564,'size':2,'conv':'Div10', 'unit':'℃', 'name':'Température capteur solaire', 'entity': 'temperature_capteur_solaire'},
              { 'addr':0x2900,'size':2,'conv':'Div10', 'unit':'℃', 'name':'Température de départ', 'entity': 'temperature_depart'},
              { 'addr':0x254C,'size':1,'conv':'Int8', 'unit':'', 'name':'Position vanne mélangeuse', 'entity': 'position_vanne_melangeuse'},
            #   { 'addr':0x00F8,'size':2, 'name':'ID' }
          ]


log.info('Starting Viessmann2HASS')
unknown = 0
ENQ = 1
ACK = 2
NACK = 3
LDAP = 0
RDAP = 0x10
RequestMessage = 0
ResponseMessage = 1
UNACKDMessage = 2
ErrorMessage = 3

undefined = 0
Virtual_READ = 1
Virtual_WRITE = 2
Physical_READ = 3
Physical_WRITE = 4
EEPROM_READ = 5
EEPROM_WRITE = 6
Remote_Procedure_Call = 7
Virtual_MBUS = 33
Virtual_MarktManager_READ = 34
Virtual_MarktManager_WRITE = 35
Virtual_WILO_READ = 36
Virtual_WILO_WRITE = 37
XRAM_READ = 49
XRAM_WRITE = 50
Port_READ = 51
Port_WRITE = 52
BE_READ = 53
BE_WRITE = 54
KMBUS_RAM_READ = 65
KMBUS_EEPROM_READ = 67
KBUS_DATAELEMENT_READ = 81
KBUS_DATAELEMENT_WRITE = 82
KBUS_DATABLOCK_READ = 83
KBUS_DATABLOCK_WRITE = 84
KBUS_TRANSPARENT_READ = 85
KBUS_TRANSPARENT_WRITE = 86
KBUS_INITIALISATION_READ = 87
KBUS_INITIALISATION_WRITE = 88
KBUS_EEPROM_LT_READ = 89
KBUS_EEPROM_LT_WRITE = 90
KBUS_CONTROL_WRITE = 91
KBUS_MEMBERLIST_READ = 93
KBUS_MEMBERLIST_WRITE = 94
KBUS_VIRTUAL_READ = 95
KBUS_VIRTUAL_WRITE = 96
KBUS_DIRECT_READ = 97
KBUS_DIRECT_WRITE = 98
KBUS_INDIRECT_READ = 99
KBUS_INDIRECT_WRITE = 100
KBUS_GATEWAY_READ = 101
KBUS_GATEWAY_WRITE = 102
PROZESS_WRITE = 120
PROZESS_READ = 123
OT_Physical_Read = 180
OT_Virtual_Read = 181
OT_Physical_Write = 182
OT_Virtual_Write = 183
GFA_READ = 201
GFA_WRITE = 202

scriptPathAndName = None
lastModDate = None
commStarted = False
ser = serial.Serial(port=PORT, baudrate=4800, parity=serial.PARITY_EVEN, stopbits=serial.STOPBITS_TWO, bytesize=serial.EIGHTBITS)


def startCommunication():
    #print("SEND EOT")
    ser.flush()
    ser.write(binascii.unhexlify('04'))
    sendStart = False
    t = 0
    while t < 3000:
        #print("... %.1fms" % (t*0.001))
        if ser.in_waiting:
            buf = ser.read()
            if len(buf) == 1:
                if buf[0] == 0x05:
                    #print("RECEIVED ENQ")
                    #print("SEND VS2_START_VS2")
                    ser.write(binascii.unhexlify('160000'))
                    sendStart = True
                    t = 0
                elif sendStart:
                    if buf[0] == 0x06: # VS2_ACK
                        #print("RECEIVED VS2_ACK")
                        return True
                    elif buf[0] == 0x15: # VS2_NACK
                        #print("RECEIVED VS2_NACK")
                        #print("SEND VS2_START_VS2")
                        ser.write(binascii.unhexlify('160000'))
                        sendStart = True
                        t = 0
                    else:
                        #print("RECEIVED %s" % binascii.hexlify(buf))
                        pass
            else:
                #print("RECEIVED %s" % binascii.hexlify(buf))
                pass
        asyncio.sleep(0.1)
        t += 100
    return False


class VS2Message():
    protocol = LDAP
    identifier = RequestMessage
    Command = undefined
    ADDR = 0
    Data = bytes()
    msgBytes = bytes()

    def __init__(self, *args, **kwargs):
        if len(args) == 1:
            self.msgBytes = args[0]
            # log.info("VS2Message(%s)" % binascii.hexlify(self.msgBytes))
            self.protocol = self.msgBytes[0] & 0xF0
            self.identifier = self.msgBytes[0] & 0x0F
            self.Command = self.msgBytes[1]
            self.ADDR = (self.msgBytes[2] << 8) + self.msgBytes[3]
            self.BlockSize = self.msgBytes[4]
            self.Data = self.msgBytes[5:]
        else:
            self.protocol = args[0]
            self.identifier = args[1]
            self.Command = args[2]
            self.ADDR = args[3]
            self.BlockSize = args[4]
            if len(args) > 5:
                self.Data = args[5]
            else:
                self.Data = None

            buf = bytearray([self.protocol | self.identifier, self.Command, self.ADDR >> 8, self.ADDR & 0xFF, self.BlockSize])
            if self.Data:
                buf += bytearray(self.Data)
            buf = bytearray([0x41, len(buf)]) + buf
            buf = buf + bytearray([sum(buf[1:]) & 0xFF])
            self.msgBytes = bytes(buf)
            # log.info("VS2Message(%s)" % binascii.hexlify(self.msgBytes))

    def __str__(self):
        if self.Data:
            str = '%s' % self.Data.hex()
        else:
            str = ''
        # log.info(f'%s %s %s 0x%04x %d:%s' % (self.protocol, self.identifier, self.Command, self.ADDR, self.BlockSize, str))
        return f'%s %s %s 0x%04x %d:%s' % (self.protocol, self.identifier, self.Command, self.ADDR, self.BlockSize, str)

def sendVS2Message(message):
    # log.info("SEND %s" % binascii.hexlify(message))
    ser.write(message)
    t = 0
    buf = None
    receiveStatus = unknown
    while t < 3000:
        #print("... %.1fms" % (t*0.001))
        if ser.in_waiting:
            if buf == None:
                buf = ser.read(ser.in_waiting)
            else:
                buf += ser.read(ser.in_waiting)
            if len(buf):
                if buf[0] == 0x06: # VS2_ACK
                    if receiveStatus != ACK:
                        #print("RECEIVED VS2_ACK")
                        pass
                    receiveStatus = ACK
                elif buf[0] == 0x15: # VS2_NACK
                    if receiveStatus != NACK:
                        #print("RECEIVED VS2_NACK")
                        pass
                    receiveStatus = NACK
                if len(buf) > 1:
                    if receiveStatus == NACK:
                        if buf[1] == 0x06: # VS2_ACK
                            buf = buf[1:]
                            receiveStatus = ACK
                        elif buf[1] == 0x15: # VS2_NACK
                            buf = buf[1:]
                    if len(buf) > 1:
                        if receiveStatus != ACK and receiveStatus != NACK:
                            break # unknown state
                        #print("RECEIVED %s" % binascii.hexlify(buf))
                        if len(buf) > 3 and buf[1] == 0x41 and len(buf) == 1 + buf[2] + 3 and (sum(buf[2:-1]) & 0xff) == buf[-1]:
                            msg = None
                            if buf[0] == 0x06: # VS2_ACK
                                msg = VS2Message(buf[3:-1])
                            ser.write(binascii.unhexlify('06')) # VS2_ACK
                            return msg
        asyncio.sleep(0.1)
        t += 100
    return None



def DateTimeFromBCD(data, offset):
    # data[4+offset] == weekday, 0 = Monday
    return datetime.strptime('%02x%02x-%02x-%02x %02x:%02x:%02x' % (data[0+offset],data[1+offset],data[2+offset],data[3+offset],data[5+offset],data[6+offset],data[7+offset]), '%Y-%m-%d %H:%M:%S')

def PhaseDay(data):
    dayStrs = []
    for dayOffset in range(0,7):
        phases = []
        dateStr = ''
        for r in range(0,8):
            offs = dayOffset*8+r
            if offs >= len(data): # my Viessmann returns just 57 bytes on a 58 byte request
                bb = 0xff
            else:
                bb = data[dayOffset*8+r]
            hour = bb >> 3
            if hour >= 24:
                dateStr += '24:00'
            else:
                min = (bb & 7) * 10
                dateStr += '%02d:%02d' % (hour,min)
            if r & 1:
                phases.append(dateStr)
                dateStr = ''
            else:
                dateStr += '-'
        while phases[-1]=='24:00-24:00':
            del phases[-1]
        dayStrs.append('  '.join(phases))
    result = ''
    lastStr = None
    firstDay = 0
    currentDay = 0
    weekDayList = ['Mo','Di','Mi','Do','Fr','Sa','So']
    for weekDayStr in dayStrs:
        if lastStr == None:
            lastStr = weekDayStr
        elif lastStr != weekDayStr:
            result += '%s-%s:%s ' % (weekDayList[firstDay],weekDayList[currentDay],lastStr)
            firstDay = currentDay + 1
        currentDay += 1
    if currentDay != firstDay:
        result += '%s-%s:%s' % (weekDayList[firstDay],weekDayList[currentDay-1],lastStr)
    return result.strip()

eventTypeConversionFunctions = {
    'Mult2': (lambda data,offset: '%d' % (struct.unpack("<h", data[offset:offset+2])[0] * 2.0)),
    'Mult5': (lambda data,offset: '%d' % (struct.unpack("<h", data[offset:offset+2])[0] * 5.0)),
    'Mult10': (lambda data,offset: '%d' % (struct.unpack("<h", data[offset:offset+2])[0] * 10.0)),
    'Mult100': (lambda data,offset: '%d' % (struct.unpack("<h", data[offset:offset+2])[0] * 100.0)),
    'Div2': (lambda data,offset: '%.1f' % (struct.unpack("<h", data[offset:offset+2])[0] / 2.0)),
    'Div5': (lambda data,offset: '%.1f' % (struct.unpack("<h", data[offset:offset+2])[0] / 5.0)),
    'Div10': (lambda data,offset: '%.1f' % (struct.unpack("<h", data[offset:offset+2])[0] / 10.0)),
    'Div100': (lambda data,offset: '%.01f' % (struct.unpack("<h", data[offset:offset+2])[0] / 10.0)),
    'Sec2Hour': (lambda data,offset: '%.2f' % (struct.unpack("<i", data[offset:offset+4])[0] / 3600.0)),
    'Mult100_Int8': (lambda data,offset: '%d' % (data[offset] * 100)),
    'Int8': (lambda data,offset: '%d' % (data[offset])),
    'Int16': (lambda data,offset: '%d' % (struct.unpack("<h", data[offset:offset+2])[0])),
    'Int32': (lambda data,offset: '%d' % (struct.unpack("<i", data[offset:offset+4])[0])),
    'Solar': (lambda data,offset: 'Heute:%d Wh, -1:%d Wh, -2:%d Wh, -3:%d Wh, -4:%d Wh, -5:%d Wh, -6:%d Wh, -7:%d Wh' % struct.unpack("<8i", data[offset:])),
    'Solar': (lambda data,offset: '%d;%d;%d;%d;%d;%d;%d;%d' % struct.unpack("<8i", data[offset:])),
    'FehlerHistory': (lambda data,offset: '%s %s' % (DateTimeFromBCD(data,offset+1), data[offset])), 
    'PhaseType': (lambda data,offset: 'PhaseType(%s)' % PhaseDay(data[offset:])),
    'DatumUhrzeit': (lambda data,offset: DateTimeFromBCD(data,offset)),
}


@service
@time_trigger('period(now, 30s)')
def update_values():

    global commStarted

    try:
    # if True:

        if not commStarted:
            commStarted = startCommunication()
            if commStarted:
                log.info('### connectionn estabilished')
        if commStarted:
            for cmd in readCmds:
                if 'cmd' in cmd:
                    fc = cmd['cmd']
                else:
                    fc = Virtual_READ
                msg = VS2Message(LDAP, RequestMessage, fc, cmd['addr'], cmd['size'])
                for _ in range(0,5): # 5 tries to read a parameter
                    # log.info(msg.__str__())
                    rmsg = sendVS2Message(msg.msgBytes)
                    if rmsg:
                        break
                if not rmsg: # ignore, if no success
                    continue
                if rmsg.identifier != ResponseMessage:
                    log.info("RECEIVED %s" % rmsg)
                    continue
                if 'conv' in cmd:
                    if 'offset' in cmd:
                        offset = cmd['offset']
                    else:
                        offset = 0
                    result = '%s' % eventTypeConversionFunctions[cmd['conv']](rmsg.Data, offset)
                else:
                    result = '0x%s' % rmsg.Data.hex()
                    if len(rmsg.Data) == 2:
                        result += ' %d' % (rmsg.Data[0] + 256 * rmsg.Data[1])
                if 'unit' in cmd:
                    unit = ' ' + cmd['unit']
                # log.info('%04x:%02x - %s - %s %s' % (cmd['addr'], cmd['size'], cmd['name'], result, unit))
                state.set(DOMAIN + "." + cmd['entity'], str(result), {'state_class':'measurement', 'unit_of_measurement':unit, 'friendly_name': cmd['name']}) 

    except KeyboardInterrupt:
        ser.close()
        commStarted = False
        
    except Exception as e:
        log.error("Unhandled error [" + str(e) + "]")
        ser.close()
        commStarted = False
