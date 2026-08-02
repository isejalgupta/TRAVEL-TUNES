"""
Music logic for TripTunes.

A direct port of the MusicTrie / PlaylistHeap from the console app:

  - Trie              -> prefix search + autocomplete
  - KMP               -> full-text substring search over name + artist
  - Max-heap          -> playlist generation ranked by rating

Pure Python, no database or web dependencies.
"""

import heapq
import itertools
from dataclasses import dataclass, field


@dataclass
class Song:
    name: str
    artist: str
    genre: str
    mood: str
    rating: float
    id: int = 0


class _TrieNode:
    __slots__ = ("children", "is_end", "song")

    def __init__(self):
        self.children = {}
        self.is_end = False
        self.song = None


class MusicTrie:
    def __init__(self):
        self.root = _TrieNode()

    def insert(self, song: Song):
        node = self.root
        for ch in song.name.lower():
            node = node.children.setdefault(ch, _TrieNode())
        node.is_end = True
        node.song = song

    def _collect(self, node, out):
        if node is None:
            return
        if node.is_end and node.song:
            out.append(node.song)
        for child in node.children.values():
            self._collect(child, out)

    def search_prefix(self, prefix: str) -> list:
        node = self.root
        for ch in prefix.lower():
            if ch not in node.children:
                return []
            node = node.children[ch]
        out = []
        self._collect(node, out)
        return out

    def autocomplete(self, prefix: str, limit: int) -> list:
        return self.search_prefix(prefix)[:limit]

    def all_songs(self) -> list:
        out = []
        self._collect(self.root, out)
        return out

    def by_artist(self, artist: str) -> list:
        lo = artist.lower()
        return [s for s in self.all_songs() if s.artist.lower() == lo]


# ------------------------------------------------------------------
#  KMP full-text search (substring match on name OR artist)
# ------------------------------------------------------------------

def _kmp_table(pattern: str) -> list:
    lps = [0] * len(pattern)
    length = 0
    i = 1
    while i < len(pattern):
        if pattern[i] == pattern[length]:
            length += 1
            lps[i] = length
            i += 1
        elif length != 0:
            length = lps[length - 1]
        else:
            lps[i] = 0
            i += 1
    return lps


def _kmp_contains(text: str, pattern: str) -> bool:
    if not pattern:
        return True
    t, p = text.lower(), pattern.lower()
    lps = _kmp_table(p)
    i = j = 0
    while i < len(t):
        if t[i] == p[j]:
            i += 1
            j += 1
            if j == len(p):
                return True
        elif j != 0:
            j = lps[j - 1]
        else:
            i += 1
    return False


def kmp_search(songs: list, query: str) -> list:
    return [s for s in songs if _kmp_contains(s.name, query) or _kmp_contains(s.artist, query)]


# ------------------------------------------------------------------
#  Max-heap playlist generation (rank by rating)
# ------------------------------------------------------------------

def generate_playlist(songs: list, count: int) -> list:
    # Python's heapq is a min-heap, so negate rating for max-heap behaviour.
    # counter breaks ties so Song objects are never compared directly.
    counter = itertools.count()
    heap = [(-s.rating, next(counter), s) for s in songs]
    heapq.heapify(heap)
    out = []
    for _ in range(min(count, len(heap))):
        out.append(heapq.heappop(heap)[2])
    return out


def filter_songs(songs: list, mood: str = "", genre: str = "") -> list:
    result = songs
    if mood:
        result = [s for s in result if s.mood == mood]
    if genre:
        result = [s for s in result if s.genre == genre]
    return result


if __name__ == "__main__":
    data = [
        Song("Tum Hi Ho", "Arijit Singh", "Bollywood", "Emotional", 4.9),
        Song("Tujh Mein Rab", "Roop Kumar Rathod", "Bollywood", "Romantic", 4.9),
        Song("Channa Mereya", "Arijit Singh", "Bollywood", "Emotional", 4.9),
        Song("Jai Ho", "A.R. Rahman", "Bollywood", "Happy", 4.9),
        Song("Naatu Naatu", "Rahul Sipligunj", "Telugu", "Happy", 5.0),
    ]
    trie = MusicTrie()
    for s in data:
        trie.insert(s)

    print("prefix 'tu':", [s.name for s in trie.search_prefix("tu")])
    print("by artist Arijit:", [s.name for s in trie.by_artist("Arijit Singh")])
    print("kmp 'rab':", [s.name for s in kmp_search(trie.all_songs(), "rab")])
    print("playlist top 3:", [(s.name, s.rating) for s in generate_playlist(data, 3)])
    print("emotional only:", [s.name for s in filter_songs(data, mood="Emotional")])