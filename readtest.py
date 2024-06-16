VERSION = "1.1"

#######################################
# The Retro Web PCI ROM Decoder
#
# Local test script
#######################################

import struct
import sys
import os
import glob

print("\n*****************************************************************")
print("The Retro Web PCI ROM Decoder (local test)")
print("Version " + VERSION +"\n")
print("Written primarily by Matthew Petry (fireTwoOneNine)")
print("Special Thanks to the PCI ID Project (https://pci-ids.ucw.cz/)")
print("*****************************************************************\n")

# command argument parser
# TODO: add fancier commands/parser
if len(sys.argv) == 1:
   print(sys.argv[0] + " <ROM file>")
   print("Append -t to parse for strings")
   print("")
   exit()

# create glob list if directory or wildcard search
files = []
if (os.path.isdir(sys.argv[1])):
    sys.argv[1] = sys.argv[1] + "**\*.*"
if ("*" in sys.argv[1]):
    files = glob.glob(sys.argv[1], recursive=True)
else:    
    files.append(sys.argv[1])

# header component internal offsets
VID = 4 # vendor ID
DID = 6 # device ID
CID = 15 # class type
SCD = 14 # subclass type
PFID = 13 # programming interface

### FOR YOUR FYI, short-hand variable names:
# pO = PnP Offset; address offset to the 0x55AA PnP header
# hO = Header Offset; address offset to the PCIR header
# sA = Starting Address
### These are used for the sake of keeping line lengths sane

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
            data.append(rawRead[x:x+1].hex())
    else:
        for x in range(end, start-1, -1):
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
            data.append(rawRead[x:x+2].hex())
    else:
        for x in range(end, start-1, -2):
            data.append(rawRead[x:x-2:-1].hex())
    return data

######################################
# Read ROM as UTF-8 formatted string #
######################################    
def readROMtext(start, end, terminator=-1):
    return rawRead[start:end].decode("utf-8")

######################################
# Read ROM as text until terminator  #
######################################  
def readROMtextTerminated(start, terminator):
    finalString = ""
    i = start
    while not (rawRead[i] == terminator):
        finalString = finalString + chr(rawRead[i])
        i = i + 1
    return finalString

######################################
# Attempt to read only "valid" text  #
######################################    
def readROMsaneText(start, end):
    tempString = ""
    finalString = ""
    garbage = 0
    for x in range(start, end+1):
        if (31 < int(rawRead[x]) < 127): # only allow printable ASCII characters
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

######################################
# Brute-force search for "PCIR"      #
# header in file                     #
###################################### 
def findPCIheader(startAddr):
    i = startAddr
    while (i < EOFile):
        if (readROM16(i, i+3, 1) == ['5043', '4952']): # "PCIR"
            print("Found PCIR header at "+hex(i)+"!")
            return i
        i = i + 1    
    else:
        print("No PCI headers found!")
        return -1

######################################
# Brute-force search for 0x55AA PnP  #
# header in file                     #
###################################### 
def findPnPheader(startAddr):
    i = startAddr
    while (i < EOFile):
        if (readROM16(i, i+1, 1) == ['55aa']):
            print("Found PnP header at "+hex(i)+"!")
            return i
        i = i + 1    
    else:
        print("No PnP headers found!")
        return -1

######################################
# Lookup Vendor and Device ID in     #
# PCI ID database                    #
###################################### 
def getVendorDevice(hO):
    vendorID = readROM16(hO+VID, hO+VID+1)
    deviceID = readROM16(hO+DID, hO+DID+1)
    vendorName = ""
    deviceName = ""
    PCIids = open("pci.ids", 'r')
    searchType = 0
    for lineNum, line in enumerate(PCIids, start = 1):
        if searchType == 0: # searching for vendor ID
            if (line[0:4] == vendorID[0]):
                vendorName = line[6:].rstrip()
                searchType = 1
        else: # searching for device ID
            if not ((line[0] == '\t') or (line[0] == '#')): # run out of vendor's devices
                deviceName = "unknown"
                deviceLine = -1
                break
            if (line[1:5] == deviceID[0]):
                deviceName = line[7:].rstrip()
                deviceLine = lineNum
                break
    PCIids.close()
    if (vendorName == ""): # failsafe if vendor not in DB (wtf?)
        vendorName = "unknown"
        deviceName = "unknown"
        deviceLine = -1
    return (vendorID, deviceID, vendorName, deviceName, deviceLine)        

######################################
# Lookup Subsystem VID+DID in        #
# PCI ID database                    #
###################################### 
def getSubsys(subVendor, subDevice, deviceLine):
    PCIids = open("pci.ids", 'r')
    subDeviceName = -1
    for lineNum, line in enumerate(PCIids, start=1):
        if (lineNum <= deviceLine):
            pass
        elif (line[2:11] == (subVendor + " " + subDevice)):
            subDeviceName = line[13:].rstrip()
        elif not (line[0:2] == '\t\t'):
            break
    PCIids.close()
    return subDeviceName

######################################
# Lookup Class and Subclass ID in    #
# PCI ID database                    #
###################################### 
def getClassSubclass(hO):
    className = ""
    progInfName = ""
    classID = readROM8(hO+CID, hO+CID)
    subclassID = readROM8(hO+SCD, hO+SCD)
    progInfID = readROM8(hO+PFID, hO+PFID)
    PCIclass = open("pciclasses.ids", 'r')
    searchType = 0
    for line in PCIclass:
        if searchType == 0: # search for class ID
            if (line[0:4] == "C " + classID[0]):
                className = line[6:].rstrip()
                searchType = 1
        elif searchType == 1: # search for subclass ID
            if not ((line[0] == '\t') or (line[0] == '#')):
                subclassName = "unknown"
                break
            if (line[1:3] == subclassID[0]):
                subclassName = line[5:].rstrip()
                searchType = 2
        else: # search for programming interface
           if not (line[0:2] == '\t\t'): # run out of programming interfaces
                progInfName = -1
                break
           if (line[2:4] == progInfID[0]):
                progInfName = line[6:].rstrip()
                break
    if (className == ""): # fail safe if class not in DB (wtf, but less so than vendor)
        className = "unknown"
        subclassName = "unknown"
        progInfName = -1
    PCIclass.close()
    return (className, subclassName, progInfName, classID, subclassID, progInfID)

######################################
# Detect if ATI/AMD VBIOS, and read  #
# data from ATOMBIOS if recognized   #
###################################### 
def readATI(sA, deviceLine):
    try:
        if (readROMtext(sA+0x30, sA+0x39) == " 76129552"): # missing the ending zero, python is being strange
            print("ATI VBIOS detected.")
            print("Build date: " + readROMtext(sA+0x50, sA+0x60))
            abOffset = sA + hexStr2int(readROM16(sA+0x48, sA+0x49)[0])
            if (readROMtext(abOffset+4,abOffset+8) == "ATOM"):
                print("\nATOMBIOS table found.")
                nameOffset = hexStr2int(readROM16(abOffset+0x10, abOffset+0x11)[0])
                configOffset = hexStr2int(readROM16(abOffset+0x0c, abOffset+0x0d)[0])
                subSysVendor = readROM16(abOffset+0x18, abOffset+0x19)[0]
                subSysDevice = readROM16(abOffset+0x1A, abOffset+0x1B)[0]
                print("Name: " + readROMtextTerminated(sA+nameOffset+1, 0x0D).lstrip())
                print("Subsys Vendor ID: " + subSysVendor)
                print("Subsys ID: " + subSysDevice)
                subSysName = getSubsys(subSysVendor, subSysDevice, deviceLine)
                if not (subSysName == -1):
                    print("Subdevice identified: " + subSysName)
            else:
                print("No ATOMBIOS Table found.")
    except:
        pass

######################################
# Detect if Nvidia VBIOS, and read   #
# data headers if recognized         #
###################################### 
def readNV(sA, hO, deviceLine):
    if (readROM16(sA+0x4, sA+0xA, 1) == ['4b37', '3430', '30e9', '4c19']): # K74000L with 0x19 end byte
        print("NVidia VBIOS detected.")
        print("Build date: " + readROMtext(sA+0x38, sA+0x40))
        subSysDetected = 0
        # this next line is awful but so is Nvidia
        # modern Nvidia, "NPDE" magic, but have dumb edgecase for Kepler and Maxwell which don't have the subsys data here...
        if (readROM16(hO+0x20, hO+0x22, 1) == ['4e50', '4445']) and \
            (not ((readROM16(hO+0x29, hO+0x31)[0] == 'b8ff') and (readROM16(hO+0x32, hO+0x33)[0] == '4942'))):
                subSysVendor = readROM16(hO+0x29, hO+0x31)[0]
                subSysDevice = readROM16(hO+0x32, hO+0x33)[0]          
                subSysDetected = 1
        else: # old Nvidia
            subSysVendor = readROM16(sA+0x54, sA+0x55)[0]
            subSysDevice = readROM16(sA+0x56, sA+0x57)[0]
            subSysDetected = 1
        if (subSysDetected == 1):
            print("Subsys Vendor ID: "+ subSysVendor)
            print("Subsys ID: "+ subSysDevice)
            subSysName = getSubsys(subSysVendor, subSysDevice, deviceLine)
            if not (subSysName == -1):
                print("Subdevice identified: " + subSysName)

######################################
# Detect EFI ROM, and read data      #
# headers if recognized              #
###################################### 
def readEFI(pO):
    if (readROM16(pO+0x4, pO+0x5) == ['0ef1']):
        print("EFI ROM detected.")
        machType = readROM16(pO+0xa, pO+0xb)
        knownMach = ['0x14c', '0200', '0ebc', '8664', '01c0', '01c2', '01c4', 'aa64']
        machNames = ['x86', 'Itanium', 'EFI Byte Code', 'x86-64', 'ARM32', 'ARM32+THUMB', 'ARMv7', 'ARM64']
        for i in knownMach:
            machIndex = knownMach.index(i)
            if (machType[0] == knownMach[machIndex]):
                print("This is a "+ machNames[machIndex] + " EFI Image.")

######################################
# Main ROM decoder function          #
###################################### 
def decodeROM(startAddr):
    # Find start of PnP header structure
    if not (readROM16(startAddr, startAddr+1, 1) == ['55aa']):
        print("bad PnP Option ROM signature at "+hex(startAddr)+"! Attempting fallback scan...")
        pO = findPnPheader(startAddr)
        hO = findPCIheader(startAddr)
        if (hO == -1):
            return -1
    else:
        pO = startAddr         
        print("good PnP signature!")
        prettyOffset = readROM16(startAddr + 0x18, startAddr + 0x19)
        hO = startAddr + hexStr2int(prettyOffset[0])
        print("Header Offset at "+ str(hex(hO)))

    # Read PCI header at defined offset
    try:
        headerSignature = readROMtext(hO, hO+4)
    except: # invalid header, and so invalid that it's not printable ASCII
        print("Error reading header signature! Trying fallback scan...")
        hO = findPCIheader(startAddr)
        if (hO == -1):
            print("This may be a ROM for a non-PCI device, or a bad dump.")
            return -1
        headerSignature = readROMtext(hO, hO+4)
        print("***WARNING: PCI Data Structure at incorrect address!***")
        print("*** This ROM may be corrupted. Continuing anyway... ***\n")

    # Check if PCI header valid
    if not (headerSignature == "PCIR"):
        print("Text at offset: "+ headerSignature)
        print("Bad header signature!")
        hO = findPCIheader(startAddr)
        if (hO == -1):
            print("This may be a ROM for a non-PCI device, or a bad dump.")
            return -1
        # WTF??? If we're here, the offset was wrong, but the fallback found a table
        # These ROMs should not be valid, but some cards probably
        # do weird shit to their ROM before presenting it to the BIOS
        print("***WARNING: PCI Data Structure at incorrect address!***")
        print("*** This ROM may be corrupted. Continuing anyway... ***\n")
    print("Signature valid!\n")

    # Print Vendor and Device IDs
    (vendorID, deviceID, vendorName, deviceName, deviceLine)  = getVendorDevice(hO)
    print("Vendor: [" + vendorID[0] + "] " + vendorName)
    print("Device: [" + deviceID[0] + "] " + deviceName)
    print("\n")

    # Print Class, Subclass, and ProgInf (if available)
    (className, subclassName, progInfName, classID, subclassID, progInfID) = getClassSubclass(hO)
    print("Class Type: [" + str(classID[0]) + "] " + className)
    print("Subclass Type: [" + str(subclassID[0]) + "] " + subclassName)
    if not (progInfName == -1):
        print("Programming Interface Type: [" + str(progInfID[0]) + "] " + progInfName)

    codeType = readROM8(hO+0x14, hO+0x14)[0]
    
    if codeType == "00":
        print("Code Type: x86 (BIOS)")
    elif codeType == "01":
        print("Code Type: Open Firmware")
    elif codeType == "02":
        print("Code Type: HP PA-RISC")
    elif codeType == "03":
        print("Code Type: x86 (UEFI)")
    # extend if-elif once i have juicy non-x86 ROMs to test

    print("\nSearching for additional structures...")
    readATI(pO, deviceLine)
    readNV(pO, hO, deviceLine)
    readEFI(pO)

    if (len(sys.argv) == 2):
            print("\n***Reading strings in first 500 characters of PCI ROM space***\n")
            print(readROMsaneText(pO, pO+500))
            print("\nUse argument -t to if you wish to parse for all strings in the file")

    # check if PCI ROM reports as last one.....or..if offset to next image is zero (yes i found a case of this)
    if ((readROM8(hO+0x15, hO+0x15) == ['80']) or (hexStr2int(readROM16(hO+0x10, hO+0x11)[0]) == 0)):
        print("\nLast PCI image in ROM.")
        return -1
    else:
        print("\nContinuing to next image in ROM...")
        imageBlocks = readROM16(hO+0x10, hO+0x11)[0] # read number of 512-byte blocks to next image
        print("Current image is " + imageBlocks + " blocks long.")
        imageBytes = (hexStr2int(imageBlocks) * 512) # now make it bytes
        print("Jumping "+ str(imageBytes) + " bytes.")
        print("********************************************\n")
        return (pO+imageBytes)

######################################
# Check file extension               #
######################################
# Can't be eating .html files, sorry
def fileExtCheck(file):
    allowedExt = ['.rom', '.ROM', '.bin', '.BIN']
    for i in allowedExt:
        if i in file[len(file)-5:]: return 1
    return 0


#####################################################
# START EXECUTION
#####################################################    

for file in files:
    if ((os.path.isfile(file)) and fileExtCheck(file)):
        currFile = open(file, "rb")
        rawRead = currFile.read()
        EOFile = os.path.getsize(file)
        print("***************************************************************")
        print("ROM File: "+ file)
        print("***************************************************************")    
        imageCount = 1
        nextPCIbase = 0
        while not (nextPCIbase == -1):
            print("Image #"+str(imageCount)+":\n")
            nextPCIbase = decodeROM(nextPCIbase)
            imageCount = imageCount + 1

        # Parse human-readable text
        try:
            if (sys.argv[2] == "-t"):            
                print("\n***Parsing for text...***\n")
                print(readROMsaneText(0x00, EOFile-1))
        except:
            pass
        currFile.close()

print("\n*****************************************************************")
print("ROM decoding complete.")
print("*****************************************************************")
