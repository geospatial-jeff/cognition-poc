import geohash

precision_size = {'1': [500.94e4, 499.26e4],
                  '2': [125.23e4, 624.1e3],
                  '3': [156.1e3, 156.1e3],
                  '4': [39.1e3, 39.1e3],
                  '5': [4.9e3, 4.9e3],
                  '6': [1.2e3, 609.4],
                  '7': [152.9, 152.4],
                  '8': [38.2, 19],
                  '9': [4.8, 4.8],
                  '10': [1.2, 0.595],
                  '11': [0.149, 0.149],
                  '12': [0.037, 0.019]
                  }

def bbox_query(extent, tree, precision):
    """Given an extent and tree loaded with geohashes, return all geohashes which intersect the extent"""
    tl_hash = geohash.encode(extent[3], extent[0], precision=precision)
    tr_hash = geohash.encode(extent[3], extent[1], precision=precision)
    br_hash = geohash.encode(extent[2], extent[1], precision=precision)
    bl_hash = geohash.encode(extent[2], extent[0], precision=precision)

    common_hash = commonprefix([tl_hash, tr_hash, br_hash, bl_hash])
    intersecting_hashes = tree.prefix_query(common_hash)
    centroids = [geohash.decode_exactly(x)[:2][::-1] for x in intersecting_hashes]

    xspace = x_spacing(centroids)
    yspace = y_spacing(centroids)

    valid_list = []

    for idx, hash in enumerate(intersecting_hashes):
        centroid = centroids[idx]
        if centroid[0] < extent[1]+xspace*0.5 and centroid[0] > extent[0]-xspace*0.5 and centroid[1] < extent[3]+yspace*0.5 and centroid[1] > extent[2]-yspace*0.5:
            valid_list.append(hash)
    return list(set(valid_list))

def find_corners(geohash_list):
    """Given a list of goehashes, find the corner hashes"""
    coords = [geohash.decode(x) for x in geohash_list]
    y, x = zip(*coords)
    tl = (x[x.index(min(x))], y[y.index(max(y))])
    tr = (x[x.index(max(x))], y[y.index(max(y))])
    bl = (x[x.index(min(x))], y[y.index(min(y))])
    br = (x[x.index(max(x))], y[y.index(min(y))])
    return {
        'tl': geohash_list[coords.index(tl[::-1])],
        'tr': geohash_list[coords.index(tr[::-1])],
        'bl': geohash_list[coords.index(bl[::-1])],
        'br': geohash_list[coords.index(br[::-1])],
            }

def commonprefix(m):
    "Given a list of strings, returns the longest common leading component"
    if not m: return ''
    s1 = min(m)
    s2 = max(m)
    for i, c in enumerate(s1):
        if c != s2[i]:
            return s1[:i]
    return s1

def y_spacing(centroids):
    """Row length is unknown, need to iterate through each row until we get to the next column"""
    l = centroids.copy()
    first_y = l[0][1]
    while l[0][1] == first_y:
        l.pop(0)
    return abs(first_y - l[0][1])

def x_spacing(centroids):
    return abs(centroids[0][0] - centroids[1][0])
