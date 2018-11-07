# import dawg
import pygtrie
from lexpy.trie import Trie as Lexpy_Trie
from lexpy.dawg import DAWG

from .trie import Trie as _Trie


def build_lexpy_dawg(geohash_list):
    dawg = DAWG()
    dawg.add_all(geohash_list)
    dawg.reduce()
    return LexpyDawg(dawg)

def build_lexpy_trie(geohash_list):
    trie = Lexpy_Trie()
    trie.add_all(geohash_list)
    return LexpyTrie(trie)

def build_pygtrie(geohash_list):
    trie = pygtrie.PrefixSet(geohash_list)
    for hash in geohash_list:
        trie.add(hash)
    return GTrie(trie)

def build_trie(geohash_list):
    trie = _Trie()
    for hash in geohash_list:
        trie.add(hash)
    return Trie(trie)

# def build_completion_dawg(geohash_list):
#     d = dawg.CompletionDAWG(geohash_list)
#     return CompletionDAWG(d)

def get_tree(geohash_list, query):
    """Build a tree based on query type"""
    if query == 'builtin':
        return Builtin(geohash_list)
    elif query == 'trie':
        return build_trie(geohash_list)
    elif query == 'gtrie':
        return build_pygtrie(geohash_list)
    elif query == 'lexpy_trie':
        return build_lexpy_trie(geohash_list)
    elif query == 'lexpy_dawg':
        return build_lexpy_dawg(geohash_list)
    # elif query == 'completion_dawg':
    #     return build_completion_dawg(geohash_list)


class LexpyDawg():

    def __init__(self, tree):
        self.tree = tree

    def prefix_query(self, prefix):
        output = self.tree.search_with_prefix(prefix)
        return output

class LexpyTrie():

    def __init__(self, tree):
        self.tree = tree

    def prefix_query(self, prefix):
        output = self.tree.search_with_prefix(prefix)
        return output

class GTrie():

    def __init__(self, tree):
        self.tree = tree

    def prefix_query(self, prefix):
        output = [''.join(x) for x in list(self.tree.iter(prefix))]
        return output

class Trie():

    def __init__(self, tree):
        self.tree = tree

    def prefix_query(self, prefix):
        output = self.tree.start_with_prefix(prefix)
        return output

class Builtin():

    def __init__(self, tree):
        self.tree = tree

    def prefix_query(self, prefix):
        output = [x for x in self.tree if x.startswith(prefix)]
        return output

class CompletionDAWG():

    def __init__(self, tree):
        self.tree = tree

    def prefix_query(self, prefix):
        output = self.tree.keys(prefix)