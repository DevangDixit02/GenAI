import tiktoken

encoder=tiktoken.encoding_for_model('gpt-4o')

text="The quick brown fox jumps over the lazy dog."

tokens=encoder.encode(text)
print(tokens)

decoded=encoder.decode(tokens)
print(decoded)