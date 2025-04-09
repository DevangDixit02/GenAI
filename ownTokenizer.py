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
        return [
            [self.vocabSpace[char] for char in word if char in self.vocabSpace]
            for word in text.split()
        ]

    def decode(self, batch_ids):
        return " ".join(
            "".join(self.NumvocabSpace[i] for i in word_ids) for word_ids in batch_ids
        )


# Example :
tokenizer = EnglishCharTokenizer()
text = "Humpty Dumpty sat on a wall"
encoded = tokenizer.encode(text)
decoded = tokenizer.decode(encoded)

print("Original:", text)
print("Encoded :", encoded)
print("Decoded :", decoded)
