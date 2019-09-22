from typing import List


class Thing(object):
    a: List[int] = []

    def __init__(self):
        print('{}', len(self.a))


if __name__ == "__main__":
    t = Thing()
    q = Thing()
    t.a = [1]
    print('q.a: {}', len(q.a))
    print('t.a: {}', len(t.a))
