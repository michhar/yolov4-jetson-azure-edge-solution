import base64

chars = str(input("Enter an 8-character string: "))
if len(chars) != 8:
    print("Enter a charater with a length of 8")
    exit()

chars = chars * 8
encoded_chars = base64.b64encode(chars, 'utf-8')
print(len(encoded_chars))
print(encoded_chars)
