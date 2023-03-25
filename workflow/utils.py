import shutil
import glob
import os
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import pyproj
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.validation import make_valid
import shapely.geometry as shpg
from overlaps_helpers import compute_self_overlaps, resolve_self_overlaps

import zipfile
import tarfile

area_size_threshold_m2 = 9500

def open_zip_shapefile(fpath, exclude_pattern='', include_pattern=''):
    with zipfile.ZipFile(fpath, "r") as z:
        for f in z.filelist:
            if f.filename.endswith('.shp'):
                if exclude_pattern and exclude_pattern in f.filename:
                    continue
                if include_pattern and include_pattern not in f.filename:
                    continue
                fname = f.filename
                
    shpf = gpd.read_file('zip://' + fpath + '/' + fname)
    for f in glob.glob(f"{os.path.dirname(fpath)}/*.properties"):
        os.remove(f)
    
    return shpf

def open_tar_shapefile(fpath):
    with tarfile.open(fpath, "r:gz") as tar:
        for member in tar.getmembers():
            if '.shp' in member.path:
                fname = member.path
    shpf = gpd.read_file('tar://' + fpath + '/' + fname)
    for f in glob.glob( f"{os.path.dirname(fpath)}/*.properties"):
        os.remove(f)
    return shpf
    
# This could be made lazy to speed up imports
data_dir = '/home/www/fmaussion/misc/rgi7_data'

maps = {}
fpath = f'{data_dir}/l0_support_data/ne_10m_coastline.zip'
maps['coast_hr'] = open_zip_shapefile(fpath)
fpath = f'{data_dir}/l0_support_data/ne_50m_coastline.zip'
maps['coast_mr'] = open_zip_shapefile(fpath)
fpath = f'{data_dir}/l0_support_data/ne_110m_coastline.zip'
maps['coast_lr'] = open_zip_shapefile(fpath)
fpath = f'{data_dir}/l0_support_data/ne_10m_admin_0_countries.zip'
maps['countries_hr'] = open_zip_shapefile(fpath)
fpath = f'{data_dir}/l0_support_data/ne_50m_admin_0_countries.zip'
maps['countries_mr'] = open_zip_shapefile(fpath)
fpath = f'{data_dir}/l0_support_data/ne_110m_admin_0_countries.zip'
maps['countries_lr'] = open_zip_shapefile(fpath)

wgms_classes = {
    0:'NA',
    1:'Ice-sheet',
    2:'Ice-field',
    3:'Ice cap',
    4:'Outlet gl',
    5:'Valley gl',
    6:'Moutain gl',
    7:'Glacieret',
    8:'Ice shelf',
    9:'Rock gl',
    10:'10?',
}


def mkdir(path, reset=False):
    """Checks if directory exists and if not, create one.

    Parameters
    ----------
    reset: erase the content of the directory if exists

    Returns
    -------
    the path
    """

    if reset and os.path.exists(path):
        shutil.rmtree(path)
    try:
        os.makedirs(path)
    except FileExistsError:
        pass
    return path


def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between one point 
    on the earth and an array of points (specified in decimal degrees)
    """
    
    # convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])

    # haversine formula 
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a)) 
    r = 6371000 # Radius of earth in meters
    return c * r

def submission_summary(shp):
    
    sdf = pd.DataFrame()

    for subid in shp.subm_id.unique().astype(int):
        s_loc = shp.loc[shp.subm_id == subid]

        date = s_loc['src_date'].str[:4].astype(int)
        release_date = s_loc['release_dt'].str[:4].astype(int)

        lysts = s_loc['analysts'].unique()
        lysts = ', '.join([n.split(',')[0].strip() for n in lysts[0].split(';')])

        subms = s_loc['submitters'].unique()
        subms = ', '.join([n.split(',')[0].strip() for n in subms[0].split(';')])
        
        geogs = ', '.join(s_loc['geog_area'].unique())

        sdf.loc[subid, 'N'] = len(s_loc)
        sdf.loc[subid, 'A'] = (s_loc['area'].sum() * 1e-6).round(1)
        sdf.loc[subid, 'analysts'] = lysts
        sdf.loc[subid, 'submitters'] = subms
        try:
            sdf.loc[subid, 'release_date'] = release_date.mode().values
        except ValueError:
            sdf.loc[subid, 'release_date'] = release_date.mode().values[0]
        sdf.loc[subid, 'geog_area'] = geogs
        try:
            sdf.loc[subid, 'src_date_mode'] = date.mode().values
        except ValueError:
            sdf.loc[subid, 'src_date_mode'] = date.mode().values[0]
        sdf.loc[subid, 'src_date_min'] = date.min()
        sdf.loc[subid, 'src_date_max'] = date.max()
        
    for c in ['N', 'release_date', 'src_date_mode', 'src_date_min', 'src_date_max']:
        sdf[c] = sdf[c].astype(int)
    sdf.index.name = 'subm_id'
    
    # Classification
    df_class = sdf[['N']].copy()
    for subid in shp.subm_id.unique().astype(int):
        s_loc = shp.loc[shp.subm_id == subid]
        for s in s_loc['primeclass'].unique():
            s = int(s)
            df_class.loc[subid, f'N {wgms_classes[s]}'] = int((s_loc['primeclass'] == s).sum())
    df_class = df_class.fillna(0)
    for c in df_class:
        df_class[c] = df_class[c].astype(int)

    return sdf, df_class

def needs_size_filter(shp):
    return len(shp.loc[shp['area'] < area_size_threshold_m2]) > 0

def size_filter(shp):
    return shp.loc[shp['area'] >= area_size_threshold_m2].copy()

def find_duplicates(df):
    rp = gpd.GeoDataFrame(df.representative_point(), columns=['geometry'])
    rp['orig_index'] = df.index
    isin = gpd.overlay(rp, df, how='intersection')
    if len(isin) == len(rp):
        print('Seems Okay!')
        return
    dupes = isin['orig_index'].duplicated()
    dupes = df.loc[isin.loc[dupes]['orig_index'].unique()]
    print(f'Potential duplicates: {len(dupes)}')
    return dupes

def find_neighbors(s, df, n=10):
    lon, lat = s.representative_point().iloc[0].coords.xy
    dis = (df['CenLon'] - lon)**2 + (df['CenLat'] - lat)**2
    return df.loc[dis.sort_values().index[:n]].copy()
    

def plot_map(shp, reg, figsize=(14, 14), edgecolor=None, linewidth=1, loc='best', title=None, mapres='mr', is_rgi6=False, savefig=True, aspect=None):
    
    f, ax = plt.subplots(figsize=figsize)
    handles = []
    
    if is_rgi6:
        for itis in [True, False]:
            fc = 'C0' if itis else 'C3'
            label = 'Same as RGI6' if itis else 'New in RGI7'
            ec = fc if edgecolor is None else edgecolor
            s_loc = shp.loc[shp['is_rgi6'] == itis]
            if len(s_loc) > 0:
                s_loc.plot(ax=ax, facecolor=fc, edgecolor=ec, linewidth=linewidth)
                area = s_loc['area'].sum() * 1e-6
            else:
                area = 0
            handles.append(mpatches.Patch(facecolor=fc, label=f'{label} - N={len(s_loc)}, A={area:.1f} km²'))
    else:
        for i, subid in enumerate(shp.subm_id.unique().astype(int)):
            fc = f'C{i}'
            ec = fc if edgecolor is None else edgecolor
            s_loc = shp.loc[shp.subm_id == subid]
            s_loc.plot(ax=ax, facecolor=fc, edgecolor=ec, linewidth=linewidth)
            area = s_loc['area'].sum() * 1e-6
            handles.append(mpatches.Patch(facecolor=fc, label=f'{subid} - N={len(s_loc)}, A={area:.1f} km²'))
    
    ax.autoscale(enable=False, axis='both', tight=True)
    maps[f'coast_{mapres}'].plot(ax=ax, facecolor='none', edgecolor='k', aspect=None)
        
    # Alternative solution for "Polygon handles not passing to legend"
    ax.legend(handles=handles, loc=loc);
    if title is None:
        title = f'RGI{reg:02d}'
    ax.set_title(title)
    
    if aspect is not None:
        ax.set_aspect(aspect)
    
    if savefig:
        plot_dir = data_dir + f'/l3_rgi7a_plots/RGI{reg:02d}'
        mkdir(plot_dir)
        plotname = 'isrgi6_map' if is_rgi6 else 'inventory_map'
        plt.savefig(plot_dir + f'/{plotname}.png', bbox_inches='tight', dpi=150)

def plot_date_hist(shp, reg=None, figsize=(10, 5), reset_index=False, title=None, savefig=True):
    
    f, ax = plt.subplots(figsize=figsize)
    date = shp['src_date'].str[:4].astype(int).to_frame('src_date')
    date['area'] = shp['area']
    date = date.groupby('src_date')['area'].sum().to_frame()
    if reset_index:
        date = date.reindex(np.arange(date.index.min(), date.index.max()+1, dtype=int), fill_value=0)
    date['area'] = date['area'] / date['area'].sum()
    date = date.reset_index()
    
    if title is None:
        title = f'RGI{reg:02d}'
    
    sns.barplot(ax=ax, x='src_date', y='area', data=date, color='grey');
    ax.set_ylabel('Relative area'); ax.set_xlabel('Source date'); ax.set_title(title);
    
    if savefig:
        plot_dir = data_dir + f'/l3_rgi7a_plots/RGI{reg:02d}'
        mkdir(plot_dir)
        plotname = 'date_hist'
        plt.savefig(plot_dir + f'/{plotname}.png', bbox_inches='tight', dpi=150)

        
def haversine(lon1, lat1, lon2, lat2):
    """Great circle distance between two (or more) points on Earth
    Parameters
    ----------
    lon1 : float
       scalar or array of point(s) longitude
    lat1 : float
       scalar or array of point(s) longitude
    lon2 : float
       scalar or array of point(s) longitude
    lat2 : float
       scalar or array of point(s) longitude
    Returns
    -------
    the distances
    Examples:
    ---------
    >>> haversine(34, 42, 35, 42)
    82633.46475287154
    >>> haversine(34, 42, [35, 36], [42, 42])
    array([ 82633.46475287, 165264.11172113])
    """

    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = np.sin(dlat / 2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    return c * 6371000  # Radius of earth in meters


def recursive_valid_polygons(geoms):
    """Given a list of geometries, makes sure all geometries are valid polygons of area >9500"""
    new_geoms = []
    for geom in geoms:
        new_geom = make_valid(geom)
        try:
            new_geoms.extend(recursive_valid_polygons(list(new_geom.geoms)))
        except AttributeError:
            new_s = gpd.GeoSeries(new_geom)
            new_s.crs = 'EPSG:4326'
            if new_s.to_crs({'proj':'cea'}).area.iloc[0] >= area_size_threshold_m2:
                new_geoms.append(new_geom)
    assert np.all([type(geom) == shpg.Polygon for geom in new_geoms])
    return new_geoms


def correct_geoms(gdf):
    """Makes sure the geodataframe is full of valid polygons."""
    
    gdf_new = gdf.copy()
    is_valid = gdf.is_valid
    
    n_not_valid = (~is_valid).sum()
    print(f'Found {n_not_valid} invalid geometries out of {len(gdf)}. Correcting...')
    
    total_area_bef = gdf['area'].sum()
    
    geoms_to_add = []
    
    counter = 0
    for i, s in gdf.loc[~is_valid].iterrows():
        counter += 1
        if counter%10 == 0 or counter == n_not_valid:
            print(f'[{n_not_valid}] {counter}', end='\r', flush=True)
        new_geoms = recursive_valid_polygons([s.geometry])
        if len(new_geoms) == 0:
            raise RuntimeError(f'No valid geometry for anlys_id {int(s.anlys_id)}')
        elif len(new_geoms) == 1:
            new_geom = new_geoms[0]
            assert type(new_geom) == shpg.Polygon, int(s.anlys_id)
            new_s = gpd.GeoSeries(new_geom)
            new_s.crs = 'EPSG:4326'
            area_new = new_s.to_crs({'proj':'cea'}).area.iloc[0]
            
            gdf_new.loc[i, 'geometry'] = new_geom
            gdf_new.loc[i, 'area'] = area_new
        else:
            print(f'Multiple geometries ({len(new_geoms)}) for anlys_id {int(s.anlys_id)}')
            areas = []
            for geom in new_geoms:
                new_s = gpd.GeoSeries(geom)
                new_s.crs = 'EPSG:4326'
                areas.append(new_s.to_crs({'proj':'cea'}).area.iloc[0])
            if np.all(np.isclose(areas, areas[0])):
                print('Seems to be a duplicate. Keeping first one and thats it.') 
                gdf_new.loc[i, 'geometry'] = new_geoms[0]
                gdf_new.loc[i, 'area'] = areas[0]
            else:
                print('Adding new entries to the list of outlines.')
                gdf_new.loc[i, 'geometry'] = new_geoms[0]
                gdf_new.loc[i, 'area'] = areas[0]
                
                for new_geom, new_area in zip(new_geoms[1:], areas[1:]):
                    new_geos = gdf.loc[[i]].copy()
                    new_geos['geometry'] = new_geom
                    new_geos['area'] = new_area
                    geoms_to_add.append(new_geos)
    
    if geoms_to_add:
        print(f'Adding {len(geoms_to_add)} geometeries in total')
        gdf_new = pd.concat([gdf_new]+geoms_to_add, ignore_index=True)
        
    total_area_aft = gdf_new['area'].sum()
    is_valid = gdf_new.is_valid
    print(f'After correction, {(~is_valid).sum()} geometries are still invalid.')
    print(f'Area changed by {total_area_aft - total_area_bef:.1f} m2 ({total_area_aft/total_area_bef*100 - 100:.04f}%, '
          f'or {int((total_area_aft - total_area_bef)/area_size_threshold_m2)} tiny glaciers)')
    return gdf_new.reset_index()


def fix_overaps(gdf, check=True):
    
    total_area_bef = gdf['area'].sum()
    
    # --- Compute RGI7 self overlaps
    overlaps = compute_self_overlaps(gdf.geometry)
    
    print(f'Found {len(overlaps)} overlaps out of {len(gdf)}. ', end='')
    if len(overlaps) == 0:
        print('Returning.')
        return gdf
    
    print('Correcting...')
    
    resolved = resolve_self_overlaps(
      overlaps=overlaps,
      geoms=gdf.geometry,
      min_area=1e4,
      transformer=pyproj.Transformer.from_crs(
        'EPSG:4326', {'proj': 'cea'}, always_xy=True
      )
    )
    
    # --- Correct
    gdf.geometry[resolved.index] = resolved
    
    gdf['area'] = gdf.to_crs({'proj':'cea'}).area
    total_area_aft = gdf['area'].sum()
    
    print(f'After correction, Area changed by {total_area_aft - total_area_bef:.1f} m2 ({total_area_aft/total_area_bef*100 - 100:.04f}%, '
          f'or {int((total_area_aft - total_area_bef)/area_size_threshold_m2)} tiny glaciers)')
    
    if check:
        print(f'Final check...')
        remaining = compute_self_overlaps(gdf.geometry)
        assert remaining['geometry'].to_crs({'proj': 'cea'}).area.lt(1e-6).all()
        print(f'OK! Check done')
    
    return gdf


def correct_geoms_deprecated(gdf, pick_second=False):
    
    gdf_new = gdf.copy()
    isv = gdf.is_valid
    geoms_to_add = []
    
    n_no = (~isv).sum()
    if not pick_second:
        print(f'Found {n_no} invalid geometries out of {len(gdf)}. Correcting...')
    
    total_area_bef = gdf['area'].sum()
    
    counter = 0
    for i, s in gdf.loc[~isv].iterrows():
          
        new_geom = make_valid(s.geometry)
        additional_geom = None
        
        # Area check
        area_bef = s['area']
        
        if type(new_geom) != shpg.Polygon:
            # Check everyones area
            areas = []
            for geom in new_geom.geoms:
                new_s = gpd.GeoSeries(geom)
                new_s.crs = gdf.crs
                areas.append(new_s.to_crs({'proj':'cea'}).area.iloc[0])
            
            # Pick the one
            arg_areas = np.argsort(areas)
            if pick_second:
                new_geom = new_geom.geoms[arg_areas[-2]]
            else:
                new_geom = new_geom.geoms[arg_areas[-1]]
            
            if type(new_geom) != shpg.Polygon:
                # Do it again if not polygon
                areas = []
                for geom in new_geom.geoms:
                    new_s = gpd.GeoSeries(geom)
                    new_s.crs = gdf.crs
                    areas.append(new_s.to_crs({'proj':'cea'}).area.iloc[0])
                
                # Pick the one
                arg_areas = np.argsort(areas)
                if pick_second:
                    raise RuntimeError('Probably not good to be here')
                new_geom = new_geom.geoms[arg_areas[-1]]

        assert type(new_geom) == shpg.Polygon, int(s.anlys_id)
          
        new_s = gpd.GeoSeries(new_geom)
        new_s.crs = gdf.crs
        area_new = new_s.to_crs({'proj':'cea'}).area.iloc[0]
        if not pick_second and not np.allclose(area_bef, area_new, rtol=1e-3):
            print(f'High correction: {int(s.anlys_id)}. Area diff: {area_new - area_bef} m2 ({area_new/area_bef*100 - 100:.04f}%)', end=' ')
            if np.isclose(abs(area_new/area_bef*100), 50):
                print('Seems to be a duplicate. Correcting and ignoring.')    
            elif np.isclose(area_new, area_bef, atol=1e6):
                print('Smaller than 0.1 km2. Ignoring.')  
            else:
                print('Likely two or more geometries. Adding a new entry to the list of outlines.')
                additional_geom = correct_geoms(gdf.loc[[i]].copy(), pick_second=True)

        gdf_new.loc[i, 'geometry'] = new_geom
        gdf_new.loc[i, 'area'] = area_new
    
        if additional_geom is not None:
            geoms_to_add.append(additional_geom)
    
    if geoms_to_add:
        gdf_new = pd.concat([gdf_new]+geoms_to_add, ignore_index=True)
    
    total_area_aft = gdf_new['area'].sum()
    
    isv = gdf_new.is_valid
    
    if not pick_second:
        print(f'After correction, {(~isv).sum()} geometries are still invalid.')
        print(f'Area changed by {total_area_aft - total_area_bef:.1f} m2 ({total_area_aft/total_area_bef*100 - 100:.04f}%)')
    
    return gdf_new
