""" Author: Ethan Welty

License: BSD

Repository: https://github.com/ezwelty/rgi_links
"""
from typing import Iterable, List, Tuple, Union
from pathlib import Path
import re
import urllib.request
import zipfile
import geopandas as gpd
import networkx
import pandas as pd
import pyproj
import shapely
import shapely.geometry
import shapely.ops


def _print_progress(index: int, n: int, interval: int = 10) -> None:
    """
    Print progress.

    Parameters
    ----------
    index
        Current index (0-based). Printed as a count (1-based).
    n
        Total count.
    interval
        How often to print. Last count (`n`) is always printed.
    """
    if index % interval == 0 or index == (n - 1):
        print(f"[{n}] {index + 1}", end="\r", flush=True)


def load_rgi6_outlines(
    path: str = "nsidc0770_00.rgi60.complete.zip",
) -> gpd.GeoDataFrame:
    """
    Load all RGI6 outlines into a single dataframe.

    Parameters
    ----------
    path
        Path to `nsidc0770_00.rgi60.complete.zip`.
        Download manually from https://nsidc.org/data/nsidc-0770/versions/6
        with a NASA Earthdata login.
    """
    pattern = re.compile(r"^(?P<prefix>[^_]+)_(?P<name>[0-9]{2}_rgi60_[^\.]+)")
    gdfs = []
    parent_zip = zipfile.ZipFile(path)
    for child_name in parent_zip.namelist():
        layer = pattern.match(child_name).groupdict()
        if layer["name"].startswith("00"):
            continue
        print(layer["name"])
        with parent_zip.open(child_name, "r") as child_zip:
            gdfs.append(gpd.read_file(child_zip))
    return gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True), crs=gdfs[0].crs)


def load_rgi7_outlines(path: str = ".") -> gpd.GeoDataFrame:
    """
    Load all RGI7 outlines into a single dataframe.

    Parameters
    ----------
    path
        Path to `*.tar.gz` files downloaded from
        https://cluster.klima.uni-bremen.de/~fmaussion/misc/rgi7_data/l4_rgi7b0_tar.
        Missing files are automatically downloaded.
    """
    base_url = (
        "https://cluster.klima.uni-bremen.de/~fmaussion/misc/rgi7_data/l4_rgi7b0_tar"
    )
    regions = [
        "01_alaska",
        "02_western_canada_usa",
        "03_arctic_canada_north",
        "04_arctic_canada_south",
        "05_greenland_periphery",
        "06_iceland",
        "07_svalbard_jan_mayen",
        "08_scandinavia",
        "09_russian_arctic",
        "10_asia_north",
        "11_central_europe",
        "12_caucasus_middle_east",
        "13_asia_central",
        "14_asia_south_west",
        "15_asia_south_east",
        "16_low_latitudes",
        "17_southern_andes",
        "18_new_zealand",
        "19_subantarctic_antarctic_islands",
    ]
    gdfs = []
    for region in regions:
        print(region)
        stem = f"RGI2000-v7.0-G-{region}"
        path: Path = Path(path)
        Path(path).mkdir(parents=True, exist_ok=True)
        filename = path / f"{stem}.tar.gz"
        if not filename.exists:
            url = f"{base_url}/{filename}"
            urllib.request.urlretrieve(url, str(filename))
        gdf = gpd.read_file(f"/vsitar/{filename}/{stem}/{stem}.shp")
        # Reduce 3D coordinates to 2D
        gdf.geometry = shapely.force_2d(gdf.geometry)
        gdfs.append(gdf)
    return gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True), crs=gdfs[0].crs)


def polygonize(
    geom: shapely.geometry.base.BaseGeometry,
) -> Union[shapely.Polygon, shapely.MultiPolygon]:
    """
    Convert geometry to (Multi)Polygon, removing all zero-area components.

    Raises
    ------
    ValueError
        Geometry has zero area.
    """
    try:
        # Remove zero-area children
        geoms = [x for x in geom.geoms if x.area]
    except AttributeError:
        if geom.area:
            return geom
        raise ValueError("Geometry has zero area")
    if not geoms:
        raise ValueError("Geometry has zero area")
    if len(geoms) == 1:
        return geoms[0]
    return shapely.MultiPolygon(geoms)


def split_and_filter_polygons(
    geom: Union[shapely.Polygon, shapely.MultiPolygon],
    min_area: float = 10000,
    transformer: pyproj.Transformer = None,
) -> List[shapely.Polygon]:
    """
    Split multipolygons into polygons and drop small polygons.

    Parameters
    ----------
    geom
        Polygon geometry.
    min_area
        Minimum area in square meters of multipolygon parts.
    transformer
        Coordinate transformer to apply to compute area in square meters.
    """
    if transformer:
        geom_area = shapely.ops.transform(transformer.transform, geom)
    else:
        geom_area = geom
    if isinstance(geom, shapely.MultiPolygon):
        return [g for g, ga in zip(geom.geoms, geom_area.geoms) if ga.area > min_area]
    if geom_area.area > min_area:
        return [geom]
    return []


def compute_self_overlaps(gs: gpd.GeoSeries) -> gpd.GeoDataFrame:
    """
    Compute overlaps between pairs of input geometries.

    The results are reported with the following columns:

    * i, j: Integer indices of the overlapping geometries.
    * i_area_fraction, j_area_fraction: Area of the overlap divided by the area of
      the i and j geometry, respectively.
    * geometry: Geometry of overlap.

    Parameters
    ----------
    gs
        Geometry series.
    """
    sindex = gs.sindex
    # Identify intersecting geometry pairs
    print("Finding intersecting geometries")
    matches = sindex.query_bulk(gs, "intersects")
    is_unique_pair = (matches[0] != matches[1]) & (matches[0] < matches[1])
    pairs = matches[:, is_unique_pair].transpose()
    # Compute pairwise overlap and report those with non-zero overlap
    print("Computing overlap of intersecting pairs")
    overlaps = []
    for counter, (i, j) in enumerate(pairs):
        _print_progress(counter, len(pairs))
        if i != j:
            overlap = gs.iloc[i].intersection(gs.iloc[j])
            try:
                overlap = polygonize(overlap)
            except ValueError:
                continue
            overlaps.append(
                {
                    "i": i,
                    "j": j,
                    "i_area_fraction": overlap.area / gs.iloc[i].area,
                    "j_area_fraction": overlap.area / gs.iloc[j].area,
                    "geometry": overlap,
                }
            )
    # Return same columns even if empty
    columns = ["i", "j", "i_area_fraction", "j_area_fraction", "geometry"]
    return gpd.GeoDataFrame(overlaps, columns=columns, crs=gs.crs)


def compute_cross_overlaps(x: gpd.GeoSeries, y: gpd.GeoSeries) -> gpd.GeoDataFrame:
    """
    Compute overlaps between pairs of input geometries.

    The results are reported with the following columns:

    * i: Integer index of the geometry from x.
    * j: Integer index of the geometry from y.
    * i_area_fraction, j_area_fraction: Area of the overlap divided by the area
      of the i and j geometry, respectively.
    * geometry: Geometry of overlap.

    Parameters
    ----------
    x
        Geometry series.
    y
        Geometry series.
    """
    if x.crs != y.crs:
        raise ValueError(f"CRS of x and y are not equal")
    y_sindex = y.sindex
    # Identify intersecting geometry pairs
    print("Finding intersecting geometries")
    pairs = y_sindex.query_bulk(x, "intersects").transpose()
    # Compute pairwise overlap and report those with non-zero overlap
    print("Computing overlap of intersecting pairs")
    overlaps = []
    for counter, (i, j) in enumerate(pairs):
        _print_progress(counter, len(pairs))
        overlap = x.iloc[i].intersection(y.iloc[j])
        try:
            overlap = polygonize(overlap)
        except ValueError:
            continue
        overlaps.append(
            {
                "i": i,
                "j": j,
                "i_area_fraction": overlap.area / x.iloc[i].area,
                "j_area_fraction": overlap.area / y.iloc[j].area,
                "geometry": overlap,
            }
        )
    # Return same columns even if empty
    columns = ["i", "j", "i_area_fraction", "j_area_fraction", "geometry"]
    return gpd.GeoDataFrame(overlaps, columns=columns, crs=x.crs)


def resolve_self_overlaps(
    overlaps: gpd.GeoDataFrame,
    geoms: gpd.GeoSeries,
    min_area: float = 10000,
    transformer: pyproj.Transformer = None,
) -> gpd.GeoSeries:
    """
    Resolves overlaps by differencing the overlap from one of the polygons.

    The polygon is chosen such that differencing results in the smallest total
    boundary length, unless this results in a multipolygon.
    Fixes are applied iteratively, since the same polygon may be involved in
    multiple overlaps.

    The modified polygons are returned with an index matching `geoms`.

    Parameters
    ----------
    overlaps
        Overlaps in the format returned by :func:`compute_self_overlaps`.
    geoms
        Original geometries with index matching columns `i` and `j` of `overlaps`.
    min_area
        Minimum area in square meters of multipolygon parts.
    transformer:
        Coordinate transformer to apply to compute area in square meters.

    Raises
    ------
    ValueError
        Failed to resolve overlap
    """
    fixed = {}
    for counter, row in enumerate(overlaps.to_dict(orient="records")):
        _print_progress(counter, len(overlaps))
        gi = [row["i"], row["j"]]
        g = [fixed[i] if i in fixed else geoms[i] for i in gi]
        # Differemce overlap from each geometry
        d = (
            polygonize(g[0].difference(row["geometry"])),
            polygonize(g[1].difference(row["geometry"])),
        )
        # Choose difference that minimizes total perimeter
        first_choice = int(
            (d[0].boundary.length + g[1].boundary.length)
            > (g[0].boundary.length + d[1].boundary.length)
        )
        fixed_geom = None
        for choice in (first_choice, int(not first_choice)):
            if isinstance(d[choice], shapely.MultiPolygon):
                polygons = split_and_filter_polygons(
                    d[choice], min_area=min_area, transformer=transformer
                )
                if len(polygons) == 1:
                    fixed_geom = polygons[0]
                    break
            else:
                # Keep single polygons smaller than limit
                fixed_geom = d[choice]
                break
        if fixed_geom:
            fixed[gi[choice]] = fixed_geom
        else:
            raise ValueError(f"Failed to resolve overlap of {gi} (#{counter})")
    return gpd.GeoSeries(
        fixed.values(), index=pd.Index(fixed.keys(), name=geoms.index.name)
    )


def _validate_pairs(x: Iterable, y: Iterable) -> Tuple[pd.Series, pd.Series]:
    # Cast to Series, avoiding
    pairs = tuple(pd.Series(s, copy=False) for s in (x, y))
    if pairs[0].size != pairs[1].size:
        raise ValueError("Pair indices have unequal length")
    if not pairs[0].index.equals(pairs[1].index):
        raise ValueError("Pair indices have unequal row index")
    if any(s.isnull().any() for s in pairs):
        raise ValueError("Pair indices contain null values")
    return pairs


def count_pair_relations(x: Iterable, y: Iterable) -> Tuple[pd.Series, pd.Series]:
    """
    Count the number of records associated with each pairwise relation.

    For each pair between two groups,
    returns the total number of (directly) related records from each group.
    For example:

    * A|1 (1:1)
    * A|1, A|2 (1:2)
    * A|1, B|1 (2:1)
    * A|1, B|1, B|2, C|2 (2:2)
    * A|1, B|1, B|2, C|2, C|3 (2:2 chain of A,B|1,2 and B,C|2,3)

    Parameters
    ----------
    x
        Indices of first group.
    y
        Indices of second group.

    Raises
    ------
    ValueError
        Pair indices have unequal length
    ValueError
        Pair indices have unequal row index (if provided as pandas.Series)
    ValueError
        Pair indices contain null values

    Examples
    -------
    One-to-one and one-many relationships.

    * A|1 (1:1)
    * B|2, B|3 (1:2)
    * C|4, D|4 (2:1)

    >>> xn, yn = count_pair_relations(['A', 'B', 'B', 'C', 'D'], [1, 2, 3, 4, 4])
    >>> xn.astype(str) + ':' + yn.astype(str)
    0    1:1
    1    1:2
    2    1:2
    3    2:1
    4    2:1
    dtype: object

    Many-many relationships.

    * A|1, B|1, B|2, C|2, D|2

    >>> xn, yn = count_pair_relations(['A', 'B', 'B', 'C', 'D'], [1, 1, 2, 2, 2])
    >>> xn.astype(str) + ':' + yn.astype(str)
    0    2:2
    1    3:2
    2    3:2
    3    3:2
    4    3:2
    dtype: object

    A|1 is 2:2 because A,B are related to 1,2 (A -> 1 -> A,B -> 1,2).
    All others are 3:2 because B,C,D are related to 1,2.
    """
    pairs = _validate_pairs(x, y)
    # For each column, count the occurences of each id
    counts = [s.groupby(s).transform("count") for s in pairs]
    # For each id in a column, find the maximum count in the other column
    return tuple(
        count.groupby(index).transform("max")
        for index, count in zip(pairs, counts[::-1])
    )


def label_pair_clusters(x: Iterable, y: Iterable) -> pd.Series:
    """
    Label clusters of pairwise relations.

    For each pair, returns an integer index that groups the pair to all other
    pairs to which it is directly or indirectly related.

    Parameters
    ----------
    x
        Indices of first group.
    y
        Indices of second group.

    Raises
    ------
    ValueError
        Pair indices have unequal length
    ValueError
        Pair indices have unequal row index (if provided as pandas.Series)
    ValueError
        Pair indices contain null values

    Examples
    -------
    One-to-one and one-many relationships.

    * A|1 (1:1)
    * B|2, B|3 (1:2)
    * C|4, D|4 (2:1)

    >>> label_pair_clusters(['A', 'B', 'B', 'C', 'D'], [1, 2, 3, 4, 4])
    0    0
    1    1
    2    1
    3    2
    4    2
    dtype: int64

    Many-many relationships.

    * A|1, B|1, B|2, C|2, D|2

    >>> label_pair_clusters(['A', 'B', 'B', 'C', 'D'], [1, 1, 2, 2, 2])
    0    0
    1    0
    2    0
    3    0
    4    0
    dtype: int64
    """
    pairs = _validate_pairs(x, y)
    # Ensure ids are globally unique
    if pairs[0].isin(pairs[1]).any():
        pairs = tuple(pd.factorize(s)[0] for s in pairs)
        pairs[1] += pairs[0].max() + 1
    # Build undirected network from pairs
    graph = networkx.Graph()
    graph.add_edges_from(zip(*pairs))
    # Assign pairs to clusters
    cluster_ids = {}
    for i, cluster in enumerate(networkx.connected_components(graph)):
        cluster_ids.update({key: i for key in cluster})
    return pairs[0].map(cluster_ids)
