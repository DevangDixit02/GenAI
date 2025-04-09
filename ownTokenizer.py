class EnglishCharTokenizer:
    def __init__(self):
        self.vocabSpace = {}
        self.NumvocabSpace = {}

        idx = 0
        for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz ":
            self.vocabSpace[ch] = idx
            self.NumvocabSpace[idx] = ch
            idx += 1

    def encode(self, text):
        return [self.vocabSpace[char] for char in text if char in self.vocabSpace]

    def decode(self, ids):
        return "".join(self.NumvocabSpace[i] for i in ids)



tokenizer = EnglishCharTokenizer()
text = "Humpty Dumpty sat on a wall"
encoded = tokenizer.encode(text)
decoded = tokenizer.decode(encoded)

print("Original:", text)
print("Encoded:", encoded)
print("Decoded:", decoded)
