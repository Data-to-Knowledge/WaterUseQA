"""

"""
import os
import numpy as np
import pandas as pd
from pdsql import mssql
from hilltoppy import util
from hilltoppy import web_service as ws

pd.options.display.max_columns = 10

###############################################
### Parameters

## Don't change
server = 'edwprod01'

hydro_db = 'hydro'
crc_db = 'ConsentsReporting'

site_table = 'ExternalSite'
crc_table = 'reporting.CrcActSiteSumm'

ht_url = 'http://wateruse.ecan.govt.nz'
url_hts = 'WaterUse.hts'

## Query parameters

site_filter = {'SwazGroupName': ['Selwyn-Waihora']}


#########################################
### Functions


def rd_crc(where_in=None, from_date='1900-07-01', to_date='2100-06-30', include_hydroelectric=False):
    """
    Function to filter consents..

    Parameters
    ----------
    from_date : str
        The start date for the time series.
    to_date: str
        The end date for the time series.
    where_in : dict
        The keys should be the column names and the values should be a list of values on those columns.

    Returns
    -------
    DataFrame
        Allocation
    """
    ### allocation
    allo1 = mssql.rd_sql(server, crc_db, crc_table, where_in=where_in)
    if not include_hydroelectric:
        allo1 = allo1[allo1.WaterUse != 'hydroelectric']

    ### Time series filtering
    allo1.loc[:, 'ToDate'] = pd.to_datetime(allo1.loc[:, 'ToDate'], errors='coerce')
    allo1.loc[:, 'FromDate'] = pd.to_datetime(allo1.loc[:, 'FromDate'], errors='coerce')
    allo1 = allo1[(allo1['ToDate'] - allo1['FromDate']).dt.days > 10]
    allo2 = allo1[(allo1.FromDate < to_date) & (allo1.ToDate > from_date)].copy()

    # ### Index the DataFrame
    # allo2.set_index(['RecordNumber', 'HydroGroup', 'AllocationBlock', 'ExtSiteID'], inplace=True)

    return allo2


def rd_sites(where_in=None):
    """
    where_in : dict
        The keys should be the column names and the values should be a list of values on those columns.
    """
    ### Site and attributes
    cols = ['ExtSiteID', 'NZTMX', 'NZTMY']
    if isinstance(where_in, dict):
        for k in where_in:
            if not k in cols:
                cols.extend([k])
    elif where_in is not None:
        raise ValueError('where_in should either be None or a dict')
    sites = mssql.rd_sql(server, hydro_db, site_table, cols, where_in=where_in)
    sites1 = sites[sites.ExtSiteID.str.contains('[A-Z]+\d\d/\d+')].copy()

    return sites1



##############################################
### Query

sites1 = rd_sites(site_filter)

wap_dict = {'ExtSiteID': sites1.ExtSiteID.tolist()}

crc_dict = {'RecordNumber': ['CRC000018', 'CRC000077']}

crc1 = rd_crc(wap_dict)
# crc1 = rd_crc(crc_dict)

ht_sites = ws.site_list(ht_url, url_hts)

ht_sites['ExtSiteID'] = util.convert_site_names(ht_sites.SiteName)

ht_sites1 = ht_sites.dropna()

ht_crc_wap = pd.merge(crc1, ht_sites1, on='ExtSiteID')

ht_waps = ht_crc_wap[['ExtSiteID', 'SiteName']].drop_duplicates()






























































