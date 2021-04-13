from PIL import Image, ImageDraw
import numpy as np
from reedsolo import RSCodec
import csv
import itertools

class Qr:
    """
    The Qr code class.

    ...

    Attributes
    ----------
    data : str
        the content of the Qr code
    mask : int
        the mask used for the Qr code generation (default 0)
    forceVersion : int
        forces the minimum version of the qr code (default 1)
    errorCorrectionLevel : str
        values: 'L', 'M', 'H' or 'Q'. Four levels of data redundancy. (default 'L')
    
    Im : pillowImage
        The pillow image object of the Qr, so you can manipulate it without saving it.
    
    matrix: np.array()
        The matrix representation of the Qr code, 0 stands for white, 1 for black.

    version: dict
        a dictionnary containing the corresponding information line of qr.csv

    Methods
    -------
    save(path='qr.png')
        Saves the Qr code image to path.
    """

    def __init__(self,data,mask=0,forceVersion=1,errorCorrectionLevel='L'):
        self.data = data
        self.forceVersion = forceVersion
        self.errorCorrectionLevel = errorCorrectionLevel

        self.__loadVersion()
        
        self.mask = mask #default mask: 0, (lines, if i%2 = 0 then black)
        self.mode = 'binary' #default mode: binary

        self.__formatData()
        self.__generateMatrix()

    def __loadVersion(self):
        with open(CSVPATH) as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['version'] == str(self.forceVersion) and row['errorCorrection'] == self.errorCorrectionLevel:
                    version = row
                    version['version'] = int(version['version'])
                    version['size'] = int(version['size'])
                    version['dataBits'] = int(version['dataBits'])
                    version['numeric'] = int(version['numeric'])
                    version['alphanumeric'] = int(version['alphanumeric'])
                    version['binary'] = int(version['binary'])
                    version['alignment'] = [i for i in itertools.product([int(i) for i in version['alignment'].split(',')], repeat=2)] if version['alignment'] != '' else None
                    version['eccSymbolsPerBlock'] = int(version['eccSymbolsPerBlock']) if version['eccSymbolsPerBlock'] != '' else 0
                    version['blocks'] = int(version["blocks"])
            self.version = version

    def __formatData(self): #Transforms the raw data to the binary string that we'll draw on the qr
        
        def stringToBits(string):
            dataBits = ''
            for c in string: #for each character
                dataBits += format(ord(c), '08b') #for ascii only, need other modes implementation
            return dataBits

        def bitsStringToIntsList(bitsString):   
            return [int(bitsString[i:i+8],2) for i in range(0, len(bitsString), 8)]

        def encodedToFinalBits(encoded):
            finalBytes = ''
            for i in encoded:
                finalBytes += format(i,'08b')
            return finalBytes

        def encodeIntsList(intsList):
            # print('intsList: ',[format(i,'02x') for i in intsList]) debug
            rsc = RSCodec(self.version['eccSymbolsPerBlock'])

            #BLOCKS:
            n_blocks = self.version['blocks']
            block_length = len(intsList)//n_blocks
            blocks = [intsList[i*block_length:(i+1)*block_length] for i in range(n_blocks)]
            encoded_blocks = []
            for block in blocks:
                # print('block: ',[format(i,'02x') for i in block],'block length: ', len(block)) debug
                encoded_blocks.append(rsc.encode(block))
            
            encoded = []
            for i in range(len(encoded_blocks[0])):
                for j in range(n_blocks):
                    encoded.append(encoded_blocks[j][i])

            # print('encoded: ',[format(i,'02x') for i in encoded]) debug

            return encoded          
        
        def makeTotalBitsString(dataBits):
            bitPadding = '' if len(dataBits) % 8 == 0 else '0'*(8 - len(dataBits) % 8) #here we add zeros if the last bits does not form a byte
            modeBits = '0100' #For binary, other modes will be implemented later  
            countBits = format(len(dataBits)//8,'08b')
            terminatorBits = '0000'
            
            
            #Byte padding:
            bytePadding = '' 
            capacity = self.version['binary'] #only binary capacity, must implement this for other modes
            missingBytes = capacity - len(dataBits) // 8

            for i in range(missingBytes):
                if i % 2 == 0:
                    bytePadding += format(0xEC,'08b')
                else:
                    bytePadding += format(0x11,'08b')

            totalBitsString = modeBits + countBits + dataBits + terminatorBits + bitPadding + bytePadding

            return totalBitsString
        
        dataBits = stringToBits(self.data)

        totalBitsString = makeTotalBitsString(dataBits)   
        
        intsList = bitsStringToIntsList(totalBitsString)

        encoded = encodeIntsList(intsList)

        finalBits = encodedToFinalBits(encoded)

        self.finalBits = finalBits

    def __generateMatrix(self):
        n = self.version['size']
        tmpMatrix = np.zeros((n,n)) #used to skip pattern zones when writing bits
        matrix = np.zeros((n,n)) #the final matrix
        infoMatrix = np.zeros((n,n)) #used to store the fixed patterns and format bits

        def drawFixedPatterns():
            #horizontal:
            for l in range(6,n-7):
            # for l in range(0,n):
                if l%2 == 0:
                    color = 1
                else:
                    color = 0
                infoMatrix[l,6] = color
                tmpMatrix[l,6] = 1
            
            #vertical:
            for c in range(6,n-7):
            # for c in range(0,n):
                if c%2 == 0:
                    color = 1
                else:
                    color = 0
                infoMatrix[6,c] = color
                tmpMatrix[6,c] = 1


        def drawCorners():
            #top-left corner:
            topLeft = np.array([[1,1,1,1,1,1,1,0,0],
             [1,0,0,0,0,0,1,0,0],
             [1,0,1,1,1,0,1,0,0],
             [1,0,1,1,1,0,1,0,0],
             [1,0,1,1,1,0,1,0,0],
             [1,0,0,0,0,0,1,0,0],
             [1,1,1,1,1,1,1,0,1],
             [0,0,0,0,0,0,0,0,0],
             [0,0,0,0,0,0,1,0,0]])
            
            infoMatrix[0:9,0:9] = topLeft
            tmpMatrix[0:9,0:9] = np.ones((9,9))

            #bottom-left corner:
            bottomLeft = np.array(
            [[0,0,0,0,0,0,0,0,1],
             [1,1,1,1,1,1,1,0,0],
             [1,0,0,0,0,0,1,0,0],
             [1,0,1,1,1,0,1,0,0],
             [1,0,1,1,1,0,1,0,0],
             [1,0,1,1,1,0,1,0,0],
             [1,0,0,0,0,0,1,0,0],
             [1,1,1,1,1,1,1,0,0]])

            infoMatrix[n-8:n,0:9] = bottomLeft
            tmpMatrix[n-8:n,0:9] = np.ones((8,9))
        
            #top-right corner:
            bottomLeft = np.array(
            [[0,1,1,1,1,1,1,1],
             [0,1,0,0,0,0,0,1],
             [0,1,0,1,1,1,0,1],
             [0,1,0,1,1,1,0,1],
             [0,1,0,1,1,1,0,1],
             [0,1,0,0,0,0,0,1],
             [0,1,1,1,1,1,1,1],
             [0,0,0,0,0,0,0,0],
             [0,0,0,0,0,0,0,0]])

            infoMatrix[0:9,n-8:n] = bottomLeft
            tmpMatrix[0:9,n-8:n] = np.ones((9,8))

        drawCorners()

        def drawVersionInformation():
            #LEFT: #-11
            versionBitsInv = VERSIONBITS[str(self.version['version'])][::-1] #[::-1] to invert the string order
            count = 0
            for c in range(6):
                for l in range(3):
                    tmpMatrix[n+l-11,c] = 1
                    infoMatrix[n+l-11,c] = int(versionBitsInv[count])
                    count += 1

            #RIGHT: #-11
            count = 0
            for l in range(6):
                for c in range(3):
                    tmpMatrix[l,n+c-11] = 1
                    infoMatrix[l,n+c-11] = int(versionBitsInv[count])
                    count += 1
        
        if self.version['version'] >= 7: #For qr codes version 7 or higher, we need to add 6*3 pixels version information blocks
            drawVersionInformation()
    

        def drawAlignments(): #For version > 1, we need to draw little 5*5 alignments patterns
            alignment = np.array([
                [1,1,1,1,1],
                [1,0,0,0,1],
                [1,0,1,0,1],
                [1,0,0,0,1],
                [1,1,1,1,1]
            ])

            for pos in self.version['alignment']:

                    if (tmpMatrix[pos[0]-2:pos[0]+3,pos[1]-2:pos[1]+3] == np.zeros((5,5))).all():  #pos[0] < n-1 and pos[1] < n-1:
                        infoMatrix[pos[0]-2:pos[0]+3,pos[1]-2:pos[1]+3] = alignment
                        tmpMatrix[pos[0]-2:pos[0]+3,pos[1]-2:pos[1]+3] = np.ones((5,5))


        if self.version['version'] > 1:
            drawAlignments()

        drawFixedPatterns()
        

        def drawBits():
                                        
            def isDrawable(l,c):
                if tmpMatrix[l,c] == 0:
                    return True
                else:
                    return False

            def isBorder(l,c,matrix):
                if l >= matrix.shape[0] or c >= matrix.shape[1] or l < 0 or c < 0 :
                    return True
                else:
                    return False

            l = n - 1
            c = n - 1
            
            upPattern = [(0,-1),(-1,1)]
            downPattern = [(0,-1),(1,1)]

            patterns = [upPattern,downPattern]

            patternCounter = 0
            stepCounter = 0
            bitCounter = 0

            while bitCounter < len(self.finalBits):

                if isBorder(l,c,matrix):
                    if c == 8: #to avoid the vertical timing pattern
                        c -= 1
                    c = c-2
                    if patternCounter % 2 == 0:
                        l=l+1
                    else:
                        l=l-1
                    patternCounter +=1 #we change the direction (going up or down)

                else:
                    if isDrawable(l,c):
                        matrix[l,c] = self.finalBits[bitCounter] #testString[bitCounter] 
                        # self.matrixToImg(matrix) for debbuging
                        bitCounter += 1
                        l = l + patterns[patternCounter % 2][stepCounter % 2][0]
                        c = c + patterns[patternCounter % 2][stepCounter % 2][1]
                        stepCounter +=1

                    else:
                        l = l + patterns[patternCounter % 2][stepCounter % 2][0]
                        c = c + patterns[patternCounter % 2][stepCounter % 2][1]
                        stepCounter +=1
        
        drawBits()
            
        def applyMask():
            for l in range(n):
                for c in range(n):
                    if MASKS[str(self.mask)](l,c) == 0 and tmpMatrix[l,c] == 0:
                        #here we switch the value
                        matrix[l,c] = 0 if matrix[l,c] == 1 else 1

        applyMask()

        finalMatrix = matrix + infoMatrix
            

        # mergeMatrices()

        def drawFormatBits():

            formatBits = FORMATBITS[self.errorCorrectionLevel + str(self.mask)]
            pixelsToDraw = [(8,0),(8,1),(8,2),(8,3),(8,4),(8,5),(8,7),(8,8),(7,8),(5,8),(4,8),(3,8),(2,8),(1,8),(0,8),
            (n-1,8),(n-2,8),(n-3,8),(n-4,8),(n-5,8),(n-6,8),(n-7,8),
            (8,n-8),(8,n-7),(8,n-6),(8,n-5),(8,n-4),(8,n-3),(8,n-2),(8,n-1)]
            for i,pos in enumerate(pixelsToDraw):
                finalMatrix[pos[0],pos[1]] = formatBits[i%15]

        drawFormatBits()
        
        self.matrix = finalMatrix
        self.__matrixToImg(finalMatrix)

    def __matrixToImg(self,matrix):
        Img = Image.new('1',(self.version['size'],self.version['size']))

        def drawPixel(pos,bit): #to invert 0 and 1 (because for pillow 1 = white whereas for the qr code 1 = black)
            if bit == 1:
                Img.putpixel(pos,0)
            else:
                Img.putpixel(pos,1)

        for l in range(matrix.shape[0]):
            for c in range(matrix.shape[1]):
                drawPixel((c,l),matrix[l,c])
                
        self.Img = Img


    def save(self,path='qr.png',scale=1): #saves the qr code image to path
        self.Img.save(path)


#CONSTANTS:
FORMATBITS = { #All of the format bits, 'L,M,Q & H' for the quality (ECC level) and 0 to 7 for the used mask
    'L0': '111011111000100',
    'L1': '111001011110011',
    'L2': '111110110101010',
    'L3': '111100010011101',
    'L4': '110011000101111',
    'L5': '110001100011000',
    'L6': '110110001000001',
    'L7': '110100101110110',
    'M0': '101010000010010',
    'M1': '101000100100101',
    'M2': '101111001111100',
    'M3': '101101101001011',
    'M4': '100010111111001',
    'M5': '100000011001110',
    'M6': '100111110010111',
    'M7': '100101010100000',
    'Q0': '011010101011111',
    'Q1': '011000001101000',
    'Q2': '011111100110001',
    'Q3': '011101000000110',
    'Q4': '010010010110100',
    'Q5': '010000110000011',
    'Q6': '010111011011010',
    'Q7': '010101111101101',
    'H0': '001011010001001',
    'H1': '001001110111110',
    'H2': '001110011100111',
    'H3': '001100111010000',
    'H4': '000011101100010',
    'H5': '000001001010101',
    'H6': '000110100001100',
    'H7': '000100000111011',
}

VERSIONBITS = { #For qr codes version 7 or higher, we need to add 6*3 pixels version information blocks
    '7':'000111110010010100',
    '8':'001000010110111100',
    '9':'001001101010011001',
    '10':'001010010011010011',
    '11':'001011101111110110',
    '12':'001100011101100010',
    '13':'001101100001000111',
    '14':'001110011000001101',
    '15':'001111100100101000',
    '16':'010000101101111000',
    '17':'010001010001011101',
    '18':'010010101000010111',
    '19':'010011010100110010',
    '20':'010100100110100110',
    '21':'010101011010000011',
    '22':'010110100011001001',
    '23':'010111011111101100',
    '24':'011000111011000100',
    '25':'011001000111100001',
    '26':'011010111110101011',
    '27':'011011000010001110',
    '28':'011100110000011010',
    '29':'011101001100111111',
    '30':'011110110101110101',
    '31':'011111001001010000',
    '32':'100000100111010101',
    '33':'100001011011110000',
    '34':'100010100010111010',
    '35':'100011011110011111',
    '36':'100100101100001011',
    '37':'100101010000101110',
    '38':'100110101001100100',
    '39':'100111010101000001',
    '40':'101000110001101001',
}

MASKS = {
    '0': lambda i,j : (i+j) % 2 ,
    '1': lambda i,j : i % 2,
    '2': lambda i,j : j % 3,
    '3': lambda i,j : (i + j) % 3,
    '4': lambda i,j : (i/2 + j/3) % 2, #broken
    '5': lambda i,j : (i*j) % 2 + (i*j)% 3,
    '6': lambda i,j : ((i*j) % 3 + i*j) % 3,
    '7': lambda i,j : ((i*j) % 3 + i + j) % 2,
}

CSVPATH = 'qr.csv'

if __name__ == '__main__':  
    qr = Qr('github.com/nohehf/qrpy',mask=0,forceVersion=2,errorCorrectionLevel='L')
    qr.save()
