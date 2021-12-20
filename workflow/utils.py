import shutil
import os
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns

# RGI6
import zipfile

def open_zip_shapefile(fpath, exclude_pattern='', include_pattern=''):
    with zipfile.ZipFile(fpath, "r") as z:
        for f in z.filelist:
            if f.filename.endswith('.shp'):
                if exclude_pattern and exclude_pattern in f.filename:
                    continue
                if include_pattern and include_pattern not in f.filename:
                    continue
                fname = f.filename
                
    return gpd.read_file('zip://' + fpath + '/' + fname)

# This could be made lazy to speed up imports
maps = {}
fpath = '../../rgi7_data/l0_support_data/ne_10m_coastline.zip'
maps['coast_hr'] = open_zip_shapefile(fpath)
fpath = '../../rgi7_data/l0_support_data/ne_50m_coastline.zip'
maps['coast_mr'] = open_zip_shapefile(fpath)
fpath = '../../rgi7_data/l0_support_data/ne_110m_coastline.zip'
maps['coast_lr'] = open_zip_shapefile(fpath)
fpath = '../../rgi7_data/l0_support_data/ne_10m_admin_0_countries.zip'
maps['countries_hr'] = open_zip_shapefile(fpath)
fpath = '../../rgi7_data/l0_support_data/ne_50m_admin_0_countries.zip'
maps['countries_mr'] = open_zip_shapefile(fpath)
fpath = '../../rgi7_data/l0_support_data/ne_110m_admin_0_countries.zip'
maps['countries_lr'] = open_zip_shapefile(fpath)

data_dir = '../../rgi7_data/'

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
    return len(shp.loc[np.round(shp['area'] * 1e-6, 3) < 0.01]) > 0

def size_filter(shp):
    return shp.loc[np.round(shp['area'] * 1e-6, 3) >= 0.01].copy()

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
