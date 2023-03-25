from typing import List, Union
from pathlib import Path
import re
import urllib.request
import zipfile

import geopandas as gpd
import pandas as pd
import pyproj
import shapely
import shapely.geometry
import shapely.ops


def load_rgi6_outlines(
        path: str = 'nsidc0770_00.rgi60.complete.zip'
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
    pattern = re.compile(r'^(?P<prefix>[^_]+)_(?P<name>[0-9]{2}_rgi60_[^\.]+)')
    gdfs = []
    parent_zip = zipfile.ZipFile(path)
    for child_name in parent_zip.namelist():
        layer = pattern.match(child_name).groupdict()
        if layer['name'].startswith('00'):
            continue
        print(layer['name'])
        with parent_zip.open(child_name, 'r') as child_zip:
            gdfs.append(gpd.read_file(child_zip))
    return gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True), crs=gdfs[0].crs)


def load_rgi7_outlines(path: str = '.') -> gpd.GeoDataFrame:
    """
    Load all RGI7 outlines into a single dataframe.
  
    Parameters
    ----------
    path
      Path to `*.tar.gz` files downloaded from
      https://cluster.klima.uni-bremen.de/~fmaussion/misc/rgi7_data/l4_rgi7b0_tar.
      Missing files are automatically downloaded.
    """
    base_url = 'https://cluster.klima.uni-bremen.de/~fmaussion/misc/rgi7_data/l4_rgi7b0_tar'
    regions = [
        '01_alaska',
        '02_western_canada_usa',
        '03_arctic_canada_north',
        '04_arctic_canada_south',
        '05_greenland_periphery',
        '06_iceland',
        '07_svalbard_jan_mayen',
        '08_scandinavia',
        '09_russian_arctic',
        '10_asia_north',
        '11_central_europe',
        '12_caucasus_middle_east',
        '13_asia_central',
        '14_asia_south_west',
        '15_asia_south_east',
        '16_low_latitudes',
        '17_southern_andes',
        '18_new_zealand',
        '19_subantarctic_antarctic_islands'
    ]
    gdfs = []
    for region in regions:
        print(region)
        stem = f'RGI2000-v7.0-G-{region}'
        path: Path = Path(path)
        Path(path).mkdir(parents=True, exist_ok=True)
        filename = path / f'{stem}.tar.gz'
        if not filename.exists:
            url = f'{base_url}/{filename}'
            urllib.request.urlretrieve(url, str(filename))
        gdf = gpd.read_file(f'/vsitar/{filename}/{stem}/{stem}.shp')
        # Reduce 3D coordinates to 2D
        gdf.geometry = shapely.force_2d(gdf.geometry)
        gdfs.append(gdf)
    return gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True), crs=gdfs[0].crs)


def polygonize(
        geom: shapely.geometry.base.BaseGeometry
) -> Union[shapely.Polygon, shapely.MultiPolygon]:
    """
    Convert geometry to (Multi)Polygon, removing all zero-area components.
  
    Raises
    ------
    ValueError: Geometry has zero area.
    """
    try:
        # Remove zero-area children
        geoms = [x for x in geom.geoms if x.area]
    except AttributeError:
        if geom.area:
            return geom
        raise ValueError('Geometry has zero area')
    if not geoms:
        raise ValueError('Geometry has zero area')
    if len(geoms) == 1:
        return geoms[0]
    return shapely.MultiPolygon(geoms)


def split_and_filter_polygons(
        geom: Union[shapely.Polygon, shapely.MultiPolygon],
        min_area: float = 1e5,
        transformer: pyproj.Transformer = None
) -> List[shapely.Polygon]:
    """
    Split multipolygons into polygons and drop small polygons.
  
    Parameters
    ----------
    geom
      Polygon geometry.
    min_area
      Minimum area in square meters of multipolygon parts.
    transformer:
      Coordinate transformer to apply to compute area in square meters.
    """
    if transformer:
        geom_area = shapely.ops.transform(transformer.transform, geom)
    else:
        geom_area = geom
    if isinstance(geom, shapely.MultiPolygon):
        return [
            g for g, ga in zip(geom.geoms, geom_area.geoms) if ga.area > min_area
        ]
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
    print('Finding intersecting geometries')
    matches = sindex.query_bulk(gs, 'intersects')
    is_unique_pair = (matches[0] != matches[1]) & (matches[0] < matches[1])
    pairs = matches[:, is_unique_pair].transpose()
    # Compute pairwise overlap and report those with non-zero overlap
    print('Computing overlap of intersecting pairs')
    overlaps = []
    for counter, (i, j) in enumerate(pairs, start=1):
        if counter%10 == 0 or counter == len(pairs):
            print(f'[{len(pairs)}] {counter}', end='\r', flush=True)
        if i != j:
            overlap = gs.iloc[i].intersection(gs.iloc[j])
            try:
                overlap = polygonize(overlap)
            except ValueError:
                continue
            overlaps.append({
                'i': i,
                'j': j,
                'i_area_fraction': overlap.area / gs.iloc[i].area,
                'j_area_fraction': overlap.area / gs.iloc[j].area,
                'geometry': overlap
            })
    if len(overlaps) > 0:
        return gpd.GeoDataFrame(overlaps, crs=gs.crs)
    else:
        return gpd.GeoDataFrame(overlaps)


def compute_cross_overlaps(
        x: gpd.GeoSeries,
        y: gpd.GeoSeries
) -> gpd.GeoDataFrame:
    """
    Compute overlaps between pairs of input geometries.
  
    The results are reported with the following columns:
  
    * i: Integer index of the geometry from x.
    * j: Integer index of the geometry from y.
    * i_area_fraction, j_area_fraction: Area of the overlap divided by the area of
      the i and j geometry, respectively.
    * geometry: Geometry of overlap.
  
    Parameters
    ----------
    x
      Geometry series.
    y
      Geometry series.
    """
    if x.crs != y.crs:
        raise ValueError(f'CRS of x and y are not equal')
    y_sindex = y.sindex
    # Identify intersecting geometry pairs
    print('Finding intersecting geometries')
    pairs = y_sindex.query_bulk(x, 'intersects').transpose()
    # Compute pairwise overlap and report those with non-zero overlap
    print('Computing overlap of intersecting pairs')
    overlaps = []
    for counter, (i, j) in enumerate(pairs, start=1):
        if counter%10 == 0 or counter == len(pairs):
            print(f'[{len(pairs)}] {counter}', end='\r', flush=True)
        overlap = x.iloc[i].intersection(y.iloc[j])
        try:
            overlap = polygonize(overlap)
        except ValueError:
            continue
        overlaps.append({
            'i': i,
            'j': j,
            'i_area_fraction': overlap.area / x.iloc[i].area,
            'j_area_fraction': overlap.area / y.iloc[j].area,
            'geometry': overlap
        })
    return gpd.GeoDataFrame(overlaps, crs=x.crs)


def resolve_self_overlaps(
        overlaps: gpd.GeoDataFrame,
        geoms: gpd.GeoSeries,
        min_area: float = 1e5,
        transformer: pyproj.Transformer = None
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
    for counter, row in enumerate(overlaps.to_dict(orient='records')):
        if counter%10 == 0 or counter == (len(overlaps) - 1):
            print(f'[{len(overlaps) - 1}] {counter}', end='\r', flush=True)
        gi = [row['i'], row['j']]
        g = [fixed[i] if i in fixed else geoms[i] for i in gi]
        # Differemce overlap from each geometry
        d = (
            polygonize(g[0].difference(row['geometry'])),
            polygonize(g[1].difference(row['geometry']))
        )
        # Choose difference that minimizes total perimeter
        first_choice = int(
            (d[0].boundary.length + g[1].boundary.length) >
            (g[0].boundary.length + d[1].boundary.length)
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
            raise ValueError(f'Failed to resolve overlap of {gi} (#{counter})')
    return gpd.GeoSeries(
        fixed.values(), index=pd.Index(fixed.keys(), name=geoms.index.name)
    )
