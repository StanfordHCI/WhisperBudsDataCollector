import random


def get_text_arr():
    A_arr = []
    with open("zh-cn.txt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                A_arr.append(line.strip())
    return A_arr


class TextGenerator:
    def __init__(self):
        self.A_arr = get_text_arr()
        self.idx = -1

    def __call__(self):
        self.idx += 1
        return self.A_arr[self.idx % len(self.A_arr)]


if __name__ == "__main__":
    text_arr = get_text_arr()
    print(text_arr)
