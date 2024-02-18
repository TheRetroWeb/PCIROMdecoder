VERSION = "0.1"

#######################################
# The Retro Web PCI ROM Decoder
#
# Local test script
#######################################

import struct
import sys
import os

print("The Retro Web PCI ROM Decoder (local test)")
print("Version " + VERSION +"\n")
print("Written primarily by Matthew Petry (fireTwoOneNine)")
print("Special Thanks to the PCI ID Project (https://pci-ids.ucw.cz/)\n")

if len(sys.argv) == 1:
   print(sys.argv[0] + " <ROM file>")
   print("Append -t to parse for strings")
   exit()

file = open(sys.argv[1], "rb")
rawRead = file.read()
EOFile = os.path.getsize(sys.argv[1])

# header component internal offsets
VID = 4 # vendor ID
DID = 6 # device ID
CID = 15 # class type
SCD = 14 # subclass type

######################################
# Read ROM 8 bits (1 byte) at a time #
#                                    #
# Direction 0 for reading bytes from #
# low to high                        #
######################################
def readROM8(start, end, direction=0):
    i = 0
    data = []
    if (direction == 1):
        for x in range(start, end+1, 1):
            #print(hex(x))
            #print(rawRead[x:x+2].hex())
            data.append(rawRead[x:x+1].hex())
    else:
        for x in range(end, start-1, -1):
            #print(hex(x))
            #print(rawRead[x:x-1:-1].hex())
            data.append(rawRead[x:x-1:-1].hex())
    return data

######################################
# Read ROM 16 bits (2B) at a time    #
#                                    #
# Direction 0 for reading bytes as   #
# big-endian                         #
######################################
def readROM16(start, end, direction=0):
    i = 0
    data = []
    if (direction == 1):
        for x in range(start, end+1, 2):
            #print(hex(x))
            #print(rawRead[x:x+2].hex())
            data.append(rawRead[x:x+2].hex())
    else:
        for x in range(end, start-1, -2):
            #print(hex(x))
            #print(rawRead[x:x-1:-1].hex())
            data.append(rawRead[x:x-2:-1].hex())
    return data

######################################
# Read ROM as UTF-8 formatted string #
######################################    
def readROMtext(start, end):
    return rawRead[start:end].decode("utf-8")

######################################
# Attempt to read only "valid" text  #
######################################    
def readROMsaneText(start, end):
    tempString = ""
    finalString = ""
    garbage = 0
    for x in range(start, end+1):
        if (31 < int(rawRead[x]) < 127):
            if (garbage == 1):
                garbage = 0
                tempString = tempString + '\n'
            tempString = tempString + chr(rawRead[x])
        else:
            garbage = 1
            if (len(tempString) > 8):
                finalString = finalString + tempString
            tempString = ""
    return finalString

######################################
# Convert Python string of hex number#
# to an int                          #
######################################     
def hexStr2int(string):
    return int(string, 16)

# Find start of PCI header structure
if not (readROM16(0x00, 0x01, 1) == ['55aa']):
    print("bad PCI signature! Attempting fallbacks...")
    if (readROM16(0x00, 0x01, 1) == ['4e56']):
        print("Modern Nvidia ROM detected. Scanning for PCI header...")
        i = 0
        while (i < EOFile):
            if (readROM16(i, i+3, 1) == ['5043', '4952']):
                print("Found PCIR header at "+hex(i)+"!")
                hO = i
                break
            i = i + 1    
    else:
        print("No PCI headers found! Exiting...")
        exit()
else:         
    print("good PCI signature!")
    prettyOffset = readROM16(0x18, 0x19)
    print("Header Offset at 0x"+prettyOffset[0])
    hO = hexStr2int(prettyOffset[0])

# Confirm valid PCI header    
try:
    headerSignature = readROMtext(hO, hO+4)
except:
    print("Error reading header signature! Exiting...")
    exit()
print("Text at offset: "+ headerSignature)

if not (headerSignature == "PCIR"):
    print("Bad header signature! Exiting...")
    exit()

print("Signature valid!\n")

# Read Vendor and Device IDs
vendorID = readROM16(hO+VID, hO+VID+1)
deviceID = readROM16(hO+DID, hO+DID+1)


# Parse for Vendor and Device names from PCI ID database
PCIids = open("pci.ids", 'r')
searchType = 0
for line in PCIids:
    if searchType == 0:
        if (line[0:4] == vendorID[0]):
            vendorName = line[6:].rstrip()
            searchType = 1
    else:
        if not ((line[0] == '\t') or (line[0] == '#')):
            deviceName = "unknown"
            break
        if (line[1:5] == deviceID[0]):
            deviceName = line[7:].rstrip()
            break
print("Vendor: [" + vendorID[0] + "] " + vendorName)
print("Device: [" + deviceID[0] + "] " + deviceName)
print("\n")

# Read Class and Subclass IDs
classID = readROM8(hO+CID, hO+CID)
subclassID = readROM8(hO+SCD, hO+SCD)

# Parse for Class and Subclass names from PCI ID database
PCIclass = open("pciclasses.ids", 'r')
searchType = 0
for line in PCIclass:
    if searchType == 0:
        # print(line[2:4])
        if (line[2:4] == classID[0]):
            className = line[6:].rstrip()
            searchType = 1
    else:
        if not ((line[0] == '\t') or (line[0] == '#')):
            subclassName = "unknown"
            break
        if (line[1:3] == subclassID[0]):
            subclassName = line[5:].rstrip()
            break
print("Class Type: " + className)
print("Subclass Type: " + subclassName)

# Parse human-readable text if requested
try:
    if (sys.argv[2] == "-t"):            
        print("\n***Parsing for text...***\n")
        print(readROMsaneText(0x00, EOFile-1))
except:
    print("\nUse argument -t to if you wish to parse for strings in the file")
    
file.close()
PCIids.close()
PCIclass.close()