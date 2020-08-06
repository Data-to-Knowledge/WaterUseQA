"""
This program analyses and visualises water use data for a list of WAPs, over
the course of the entire Hilltop time-series.

Author: Alan Ambury
Last Edited: 19 June 2020
Contact the developer: alan@whiterockconsulting.co.nz

Inputs to the program:
1. The user needs to specify a csv file that contains a list of WAPs
2. The user needs to specify if they wish to export Statistics [s], Plots [p]
   or Both [b].

Outputs of the program:
Depending on the user's export preferences the program will create:
1. A spreadsheet for each WAP containing a summary of a) water use data that is
available in Hilltop, b) negative values removed from the data, and 
c) monthly water use statistics.
2. A pdf file for each WAP containing a collection of time-series plots.

In order to run the program the user needs to:
1. Have installed the hilltop-py package developed by Mike Exner-Kittridge
2. Have installed the pandas, seaborn, matplotlib, datetime and pdsql modules
(NB: these come packaged with the Anaconda distribution of Python).
3. Have access to the CrcActSiteSumm table, stored in the ConsentsReporting
database, on the edwprod01 server.
"""

import pandas as pd
import seaborn as sns
import datetime as dt
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from hilltoppy import web_service as ws
from pdsql import mssql as sq
import os.path


def get_filename():
    """Prompts the user to enter the name of the csv file containing a list
    of WAPs."""
    filename = None
    while filename is None:
        filename = input("Enter the name of the csv file that contains the WAP list: ")
        csv_filename = filename + '.csv'
        if not os.path.isfile(csv_filename):
            print(csv_filename, "does not exist!")
            filename = None
    return csv_filename    


def read_csv(filename):
    """Reads the contents of a given csv file, that contains a list of WAP
    datasets"""
    infile = open(filename)
    lines = infile.readlines()
    infile.close()
    return lines

def get_export_response():
    """This function asks the user to specify the files they wish to export"""
    export_response = None
    while export_response is None:
        export_prompt = input("Export Statistics [s], Plots [p] or Both [b]?: ")
        if export_prompt not in ['s', 'p', 'b']:
            print("Please enter 's', 'p' or 'b'")
        else:
            export_response = export_prompt
    return export_response


def get_measurement_list(site):
    """Extracts the measurement types that are available in the Hilltop WaterUse.hts file
    for a given site"""
    base_url = 'http://wateruse.ecan.govt.nz'
    hts = 'WaterUse.hts'
    raw_list = ws.measurement_list(base_url, hts, site)
    raw_list2 = raw_list.reset_index()    
    filtered_list = raw_list2.loc[raw_list2['Measurement'].isin(['Compliance Volume','Water Meter','Volume','Volume [Flow]','Volume [Average Flow]'])]
    return filtered_list


def process_measurement_list(dataframe, from_date=None, to_date=None):
    """This function prepares the measurement list so that it can be used to 
    extract water use data"""
    processed_list = dataframe.copy()
    # Add a default start date is start date is null
    if processed_list['From'].isnull().values.any():
        processed_list['From'] = processed_list['From'].fillna(pd.Timestamp('2000-01-01 00:00:00'))
    # Order by start date
    processed_list2 = processed_list.sort_values(by=['From'], ascending=True).reset_index(drop=True)
    # Add date attributes
    processed_list2.rename(columns={'From': 'FromDate', 'To': 'ToDate'}, inplace=True)
    
    if isinstance(from_date, str):
        processed_list2 = processed_list2[processed_list2['ToDate'] > pd.Timestamp(from_date)]
        processed_list2.loc[processed_list2['FromDate'] < pd.Timestamp(from_date), 'FromDate'] = from_date
        processed_list2.loc[pd.to_datetime(processed_list2['FromDate']) >= pd.Timestamp(from_date), 'FromDate'] = pd.to_datetime(processed_list2.loc[pd.to_datetime(processed_list2['FromDate']) >= pd.Timestamp(from_date), 'FromDate']).dt.date
    else:
        processed_list2['FromDate'] = processed_list2['FromDate'].dt.date
        
    if isinstance(to_date, str):
        processed_list2 = processed_list2[processed_list2['FromDate'] < pd.Timestamp(to_date)]
        processed_list2.loc[processed_list2['ToDate'] > pd.Timestamp(to_date), 'ToDate'] = to_date
        processed_list2.loc[pd.to_datetime(processed_list2['ToDate']) <= pd.Timestamp(to_date), 'ToDate'] = pd.to_datetime(processed_list2.loc[pd.to_datetime(processed_list2['ToDate']) <= pd.Timestamp(to_date), 'ToDate']).dt.date
    else:
        processed_list2['ToDate'] = processed_list2['ToDate'].dt.date
    
    return processed_list2


def extract_water_use_data(dataframe, site):
    """This function iterates through a measurement list, extracting water use
    data from Hilltop, and compiling it into a dataframe"""
    # Set base parameters
    base_url = 'http://wateruse.ecan.govt.nz'
    hts = 'WaterUse.hts'    
    # Create empty dataframe to append raw data into
    raw_data = pd.DataFrame(columns = ['Measurement','DateTime','Value'])
    # Find the start date of the time series
    from_d = dataframe['FromDate'].iloc[0]
    # Iterate through measurement list, extracting data and compiling
    for index, row in dataframe.iterrows():
        measurement = row['Measurement']
        to_d = row['ToDate']
        if from_d <= to_d:
            try:
                print("Extracting {0} data from {1} to {2}".format(measurement, from_d, to_d))
                tsdata = ws.get_data(base_url, hts, site, measurement, from_date=str(from_d), to_date=str(to_d))
                tsdata2 = tsdata.reset_index().drop(columns='Site')
                raw_data = pd.concat([raw_data, tsdata2], ignore_index=True)
                # Adjust start date to prevent overlapping time series
                from_d = to_d + dt.timedelta(days=1)
            except:
                print('No data extracted for:', measurement)
                from_d = to_d + dt.timedelta(days=1)
        else:
            print('Skipping extraction for:', measurement)
    return raw_data


def convert_water_use_data(dataframe):
    """This function creates a common unit for all the water use data
    (volume extracted in cubic metres)."""
    vol_data = dataframe.copy()
    # Add date variable
    vol_data['Date'] = vol_data['DateTime'].dt.date
    # Convert water meter data to volume
    vol_data.loc[vol_data['Measurement'] == 'Water Meter', 'Vol'] = vol_data.Value.diff()
    # Leave other measurement types as they are already in the correct unit
    vol_data.loc[vol_data['Measurement'] != 'Water Meter', 'Vol'] = vol_data.Value    
    return vol_data


def summarise_negative_values(dataframe):
    """This function analyses any negative values in the water use dataset"""
    # Find negative values
    neg_filter = dataframe[dataframe['Vol'] < 0]
    neg_data = neg_filter.copy()
    #Add extra time variables
    neg_data['Year'] = neg_data['DateTime'].dt.year
    neg_data['MonthVal'] = neg_data['DateTime'].dt.month 
    neg_data['MonthVal2'] = neg_data['MonthVal'].apply(lambda x: '{0:0>2}'.format(x))
    neg_data['Month'] = neg_data['Year'].astype(str) + "-" + neg_data['MonthVal2'].astype(str)
    # Summarise negative values by month
    neg_monthly = neg_data.groupby(['Month'])['Vol'].agg(['count', 'sum']).rename(columns={
        'count':'Negative Value Count', 'sum':'Negative Value Sum'})
    return neg_monthly


def remove_negative_values(dataframe):
    """This function removes negative values from the water use dataset"""
    vol_data2 = dataframe[dataframe['Vol'] >= 0]
    return vol_data2


def calculate_spike_parameters(dataframe):
    """This function calculates measures of central tendency that will be used
    to detect spikes"""
    # Filter out rows where extraction is greater than zero
    nonzero_vol = dataframe[dataframe.Vol > 0]
    # Calculate mean and standard deviation
    mean = nonzero_vol['Vol'].mean()
    sd = nonzero_vol['Vol'].std()
    return mean, sd


def detect_spikes(dataframe, mean, sd):
    """This function identifies spikes (extreme values of water extraction) and
    adds flags to the water use dataset"""
    vol_stats = dataframe.copy()
    # Add spike columns to dataframe
    vol_stats['sd5'] = 0  
    vol_stats['sd10'] = 0
    vol_stats['sd20'] = 0
    # Add flags if a single value is classified as a spike
    if sd >=1 and len(vol_stats) > 100:
        vol_stats.loc[vol_stats['Vol'] > mean + sd * 5, 'sd5'] = 1
        vol_stats.loc[vol_stats['Vol'] > mean + sd * 10, 'sd10'] = 1
        vol_stats.loc[vol_stats['Vol'] > mean + sd * 20, 'sd20'] = 1 
    return vol_stats


def generate_daily_stats(dataframe):
    """This function generates daily water use statistics"""
    # Aggregate by date
    daily_stats = dataframe.groupby('Date').agg({'Measurement':'max',
                                                 'Vol':'count',
                                                 'sd5':'sum',
                                                 'sd10':'sum',
                                                 'sd20':'sum'})
    # Add extra time variables
    daily_stats = daily_stats.reset_index().rename(columns={'index':'Date'})
    daily_stats['Datetime'] = pd.to_datetime(daily_stats['Date'])
    daily_stats['Year'] = daily_stats['Datetime'].dt.year
    daily_stats['MonthVal'] = daily_stats['Datetime'].dt.month 
    daily_stats['MonthVal2'] = daily_stats['MonthVal'].apply(lambda x: '{0:0>2}'.format(x))
    daily_stats['Month'] = daily_stats['Year'].astype(str) + "-" + daily_stats['MonthVal2'].astype(str)
    return daily_stats
    

def generate_monthly_stats(dataframe):
    """This function generates monthly water use statistics"""
    # Aggregate by month
    monthly_stats = dataframe.groupby('Month').agg({'Measurement':'max',
                                                    'Vol':['count','sum'],
                                                    'sd5':'sum',
                                                    'sd10':'sum',
                                                    'sd20':'sum'})
    # Rename columns
    monthly_stats.columns = ['_'.join(col) for col in monthly_stats.columns]
    monthly_stats.rename(columns={'Measurement_max': 'MeasType', 'Vol_count':'DaysWithData',
                                  'Vol_sum':'TotalReports', 'sd5_sum':'Spikes > 5sd','sd10_sum':'Spikes > 10sd',
                                  'sd20_sum':'Spikes > 20sd'}, inplace=True)       
    return monthly_stats


def generate_extraction_stats(dataframe):
    """This function generates monthly extraction statistics"""
    # Retain all datapoints where the volume extracted is greater than zero
    nonzero_vol = dataframe[dataframe.Vol > 0]
    extraction_data = nonzero_vol.copy()
    if len(extraction_data) >=1:
        # Add extra time variables
        extraction_data['Year'] = extraction_data['DateTime'].dt.year
        extraction_data['MonthVal'] = extraction_data['DateTime'].dt.month 
        extraction_data['MonthVal2'] = extraction_data['MonthVal'].apply(lambda x: '{0:0>2}'.format(x))
        extraction_data['Month'] = extraction_data['Year'].astype(str) + "-" + extraction_data['MonthVal2'].astype(str)    
        # Convert the volume readings to a numeric datatype
        extraction_data['Vol'] = extraction_data['Vol'].apply(pd.to_numeric)
        # Calculate monthly extraction stats
        extraction_monthly = extraction_data.groupby('Month').agg({'Vol':['min','mean','max']})
        # Rename columns
        extraction_monthly.columns = ['_'.join(col) for col in extraction_monthly.columns]
        extraction_monthly.rename(columns={'Vol_min':'MinExtraction', 'Vol_mean':'MeanExtraction', 'Vol_max':'MaxExtraction'}, inplace=True)     
        # Round values
        extraction_monthly.MinExtraction = extraction_monthly.MinExtraction.round(3)
        extraction_monthly.MeanExtraction = extraction_monthly.MeanExtraction.round(1)
        extraction_monthly.MaxExtraction = extraction_monthly.MaxExtraction.round(1)
    else:
        # If there is no extraction data, create an empty dataframe with column headings
        column_names = ['Month', 'MinExtraction', 'MeanExtraction', 'MaxExtraction']
        extraction_monthly = pd.DataFrame(columns = column_names)
    return extraction_monthly


def combine_monthly_stats(dataframe1, dataframe2):
    """This function combines all the monthly statistics into one dataframe"""
    monthly_stats2 = pd.merge(dataframe1, dataframe2, on='Month', how='left')
    # Change column order
    monthly_stats2 = monthly_stats2[['MeasType','DaysWithData','TotalReports','MinExtraction','MeanExtraction',
                                         'MaxExtraction','Spikes > 5sd','Spikes > 10sd','Spikes > 20sd']]
    return monthly_stats2


def export_monthly_stats(measurements, statistics, neg_summary, site):
    """This function exports water use statistics to Excel"""
    # Create Excel file
    writer = pd.ExcelWriter(site.replace('/','-') + ' - Summary Stats.xlsx', engine='xlsxwriter')
    # Export measurement list
    measurements.to_excel(writer, sheet_name='HilltopMeasurements')
    worksheet = writer.sheets['HilltopMeasurements']
    worksheet.set_column('B:I', 20)
    # Export summary of negative values
    neg_summary.to_excel(writer, sheet_name='NegativesRemoved')
    worksheet = writer.sheets['NegativesRemoved']
    worksheet.set_column('B:D', 20)      
    # Export monthly statistics
    statistics.to_excel(writer, sheet_name='MonthlyStatistics')
    worksheet = writer.sheets['MonthlyStatistics']
    worksheet.set_column('A:A', 10)
    worksheet.set_column('B:B', 20)
    worksheet.set_column('C:J', 15)
    # Save file
    writer.save()


def get_consent_conditions(site_id):
    """This function extracts consent conditions for a site of interest""" 
    # Read table of consent conditions and convert to a pandas dataframe (Ecan)
    server = 'edwprod01'
    database = 'ConsentsReporting'
    table = 'reporting.CrcActSiteSumm'
    crc_table = sq.rd_sql(server, database, table)
    # Extract the active consents for the specified site
    consents = crc_table.loc[(crc_table['ExtSiteID'] == site_id) & (crc_table['ConsentStatus'] == 'Issued - Active')]
    # If there are no active consents, extract the most recent consent for the specified site
    if len(consents) == 0:
        all_consents = crc_table.loc[(crc_table['ExtSiteID'] == site_id)]
        most_recent = all_consents['ToDate'].max()
        consents = all_consents.loc[all_consents['ToDate'] == most_recent]
    return consents


def summarise_consent_conditions(dataframe):
    """This function derives values - from the consent conditions - that can be
    used in the time-series plots"""
    consent_values = dataframe.groupby('ExtSiteID').agg({'ConsentedRate':'sum','ConsentedMultiDayVolume':'sum','ConsentedMultiDayPeriod':'max'})
    max_rate = consent_values['ConsentedRate'].values[0]
    max_vol = round(max_rate * 86.4, 2)
    multiday_vol = consent_values['ConsentedMultiDayVolume'].values[0] 
    return_period = consent_values['ConsentedMultiDayPeriod'].values[0]
    return max_rate, max_vol, multiday_vol, return_period


def process_plot_data1(dataframe):
    """This function calculates daily totals, adds in any days that are missing data and gets the
    dataframe ready for plotting. It is applied when there are no consent conditions that need to
    be taken into account."""
    # Aggregate data by day
    daily_counts = dataframe.groupby(['Date'])['Vol'].agg(['count', 'sum']).rename(columns={'count':'Readings', 'sum':'Volume'})
    # Find first and last dates
    from_date = dataframe['Date'].min()
    to_date = dataframe['Date'].max()
    # Derive start date of the first water year
    from_year = from_date.year
    from_month = from_date.month
    if from_month <= 6:
        start_date = dt.date(from_year - 1, 7, 1)
    elif from_month > 6:
        start_date = dt.date(from_year, 7, 1)
    # Add missing dates to dataframe
    idx = pd.date_range(start_date, to_date)
    daily_counts2 = daily_counts.reindex(idx)
    daily_counts2 = daily_counts2.reset_index().rename(columns={'index':'Date'})
    # Add extra date attributes
    daily_counts2['Year'] = daily_counts2['Date'].dt.year
    daily_counts2['MonthVal'] = daily_counts2['Date'].dt.month 
    daily_counts2['MonthVal2'] = daily_counts2['MonthVal'].apply(lambda x: '{0:0>2}'.format(x))
    daily_counts2['Month'] = daily_counts2['Year'].astype(str) + "-" + daily_counts2['MonthVal2'].astype(str)
    daily_counts2['Day'] = daily_counts2['Date'].dt.day
    # Derive extraction rate in L/s
    daily_counts2['Rate'] = daily_counts2['Volume'] * (1000/86400)  
    # Set missing reading counts to 0
    daily_counts2['Readings'].fillna(value=0, inplace=True)
    return daily_counts2


def process_plot_data2(dataframe, return_period):
    """This function calculates daily totals, adds in any days that are missing data and gets the
    dataframe ready for plotting. It is applied when there are consent conditions that need to
    be taken into account."""
    # Aggregate data by day
    daily_counts = dataframe.groupby(['Date'])['Vol'].agg(['count', 'sum']).rename(columns={'count':'Readings', 'sum':'Volume'})
    # Find first and last dates
    from_date = dataframe['Date'].min()
    to_date = dataframe['Date'].max()
    # Derive start date of the first water year
    from_year = from_date.year
    from_month = from_date.month
    if from_month <= 6:
        start_date = dt.date(from_year - 1, 7, 1)
    elif from_month > 6:
        start_date = dt.date(from_year, 7, 1)
    # Add missing dates to dataframe
    idx = pd.date_range(start_date, to_date)
    daily_counts2 = daily_counts.reindex(idx)
    daily_counts2 = daily_counts2.reset_index().rename(columns={'index':'Date'})
    # Add extra date attributes
    daily_counts2['Year'] = daily_counts2['Date'].dt.year
    daily_counts2['MonthVal'] = daily_counts2['Date'].dt.month 
    daily_counts2['MonthVal2'] = daily_counts2['MonthVal'].apply(lambda x: '{0:0>2}'.format(x))
    daily_counts2['Month'] = daily_counts2['Year'].astype(str) + "-" + daily_counts2['MonthVal2'].astype(str)
    daily_counts2['Day'] = daily_counts2['Date'].dt.day
    # Derive extraction rate in L/s
    daily_counts2['Rate'] = daily_counts2['Volume'] * (1000/86400)  
    # Derive 30 day rolling average
    daily_counts2['MA'] = daily_counts2.Volume.rolling(window=int(return_period)).mean()
    # Set missing reading counts to 0
    daily_counts2['Readings'].fillna(value=0, inplace=True)
    return daily_counts2


def generate_daily_plots1(dataframe, site):
    """This function generates the daily plots and outputs them to a pdf file.
    It is applied when there are no consent conditions that need to be taken
    into account."""
    # Open pdf
    filename = site.replace('/','-') + ' - Time Series Plots'
    pp = PdfPages(filename + '.pdf')
    # Calculate months in dataframe
    grid_count = dataframe['Month'].nunique()    
    # Create bar plot of daily readings
    daily_report_grid = sns.FacetGrid(dataframe, col="Month", hue="Month",
                    col_wrap=12, height=1.5)
    daily_report_grid.map(plt.bar, "Day", "Readings")
    daily_report_grid.fig.tight_layout(w_pad=1)
    if grid_count < 12:
        plt.subplots_adjust(top=0.7)
    elif grid_count >= 12 and grid_count <= 24:
        plt.subplots_adjust(top=0.8)
    else:
        plt.subplots_adjust(top=0.9)
    daily_report_grid.fig.suptitle('Meter readings received (daily)')
    daily_report_grid.savefig(pp, format='pdf')
    plt.close()
    # Create line plot of daily volumes
    daily_vol_grid = sns.FacetGrid(dataframe, col="Month", hue="Month",
                    col_wrap=12, height=1.5, dropna=False)
    daily_vol_grid.map(plt.plot, "Day", "Volume")
    daily_vol_grid.fig.tight_layout(w_pad=1)
    if grid_count <= 12:
        plt.subplots_adjust(top=0.7)
    elif grid_count > 12 and grid_count <= 24:
        plt.subplots_adjust(top=0.8)
    else:
        plt.subplots_adjust(top=0.9)
    daily_vol_grid.fig.suptitle('Daily volume extracted in m3')
    daily_vol_grid.savefig(pp, format='pdf')
    plt.close()
    # Create line plot of daily extraction rates
    daily_rate_grid = sns.FacetGrid(dataframe, col="Month", hue="Month",
                    col_wrap=12, height=1.5, dropna=False)
    daily_rate_grid.map(plt.plot, "Day", "Rate")
    daily_rate_grid.fig.tight_layout(w_pad=1)
    if grid_count <= 12:
        plt.subplots_adjust(top=0.7)
    elif grid_count > 12 and grid_count <= 24:
        plt.subplots_adjust(top=0.8)
    else:
        plt.subplots_adjust(top=0.9)
    daily_rate_grid.fig.suptitle('Average daily extraction rate in L/s')
    daily_rate_grid.savefig(pp, format='pdf')
    plt.close()
    # Close pdf
    pp.close()
    
    
def generate_daily_plots2(dataframe, site, max_rate, max_vol, multiday_vol, return_period):
    """This function generates the daily plots and outputs them to a pdf file.
    It is applied when there are consent conditions that need to be taken into
    account."""
    # Open pdf
    filename = site.replace('/','-') + ' - Time Series Plots'
    pp = PdfPages(filename + '.pdf')
    # Calculate months in dataframe
    grid_count = dataframe['Month'].nunique()    
    # Create bar plot of daily readings
    daily_report_grid = sns.FacetGrid(dataframe, col="Month", hue="Month",
                    col_wrap=12, height=1.5)
    daily_report_grid.map(plt.bar, "Day", "Readings")
    daily_report_grid.fig.tight_layout(w_pad=1)
    if grid_count <= 12:
        plt.subplots_adjust(top=0.7)
    elif grid_count > 12 and grid_count <= 24:
        plt.subplots_adjust(top=0.8)
    else:
        plt.subplots_adjust(top=0.9)
    daily_report_grid.fig.suptitle('Meter readings received (daily)')
    daily_report_grid.savefig(pp, format='pdf')
    plt.close()
    # Create line plot of daily volumes
    daily_vol_grid = sns.FacetGrid(dataframe, col="Month", hue="Month",
                    col_wrap=12, height=1.5, dropna=False)
    daily_vol_grid.map(plt.plot, "Day", "Volume")
    daily_vol_grid.map(plt.axhline, y=max_vol, ls='--', c='gray')
    daily_vol_grid.fig.tight_layout(w_pad=1)
    if grid_count <= 12:
        plt.subplots_adjust(top=0.7)
    elif grid_count > 12 and grid_count <= 24:
        plt.subplots_adjust(top=0.8)
    else:
        plt.subplots_adjust(top=0.9)
    daily_vol_grid.fig.suptitle('Daily volume extracted in m3')
    daily_vol_grid.savefig(pp, format='pdf')
    plt.close()
    # Create line plot of extracted volume moving average
    daily_ma_grid = sns.FacetGrid(dataframe, col="Month", hue="Month",
                    col_wrap=12, height=1.5, dropna=False)
    daily_ma_grid.map(plt.plot, "Day", "MA")
    ref_line = round(multiday_vol/return_period, 1)
    daily_ma_grid.map(plt.axhline, y=ref_line, ls='--', c='gray')
    daily_ma_grid.fig.tight_layout(w_pad=1)
    if grid_count <= 12:
        plt.subplots_adjust(top=0.7)
    elif grid_count > 12 and grid_count <= 24:
        plt.subplots_adjust(top=0.8)
    else:
        plt.subplots_adjust(top=0.9)
    period = str(int(return_period))
    daily_ma_grid.fig.suptitle('Volume extracted (m3) - {} day moving average'.format(period))
    daily_ma_grid.savefig(pp, format='pdf')
    plt.close()
    # Create line plot of daily extraction rates
    daily_rate_grid = sns.FacetGrid(dataframe, col="Month", hue="Month",
                    col_wrap=12, height=1.5, dropna=False)
    daily_rate_grid.map(plt.plot, "Day", "Rate")
    daily_rate_grid.map(plt.axhline, y=max_rate, ls='--', c='gray')
    daily_rate_grid.fig.tight_layout(w_pad=1)
    if grid_count <= 12:
        plt.subplots_adjust(top=0.7)
    elif grid_count > 12 and grid_count <= 24:
        plt.subplots_adjust(top=0.8)
    else:
        plt.subplots_adjust(top=0.9)
    daily_rate_grid.fig.suptitle('Average daily extraction rate in L/s')
    daily_rate_grid.savefig(pp, format='pdf')
    plt.close()
    # Close pdf
    pp.close()    
    

def main():
    """This function controls the execution of the main program"""
    
    ## Get instructions
    # Get site list
    csv_input = get_filename()
    site_list = read_csv(csv_input)
    # Get export preferences
    export_response = get_export_response()
    
    ## Iterate through site list
    for wap in site_list:
        site = wap.rstrip("\n")
        print("")
        print("Processing {}".format(site))
        try:
            ## Initial extraction and processing
            # Extract measurement list
            mslist = get_measurement_list(site)
            # Process measurement list
            mslist2 = process_measurement_list(mslist, '2018-07-01', '2019-06-30')
            # Extract water use data
            wu_data = extract_water_use_data(mslist2, site)
            # Convert water use data to a common unit
            vol_data = convert_water_use_data(wu_data)
            # Summarise any negative values in the water use dataset
            neg_summary = summarise_negative_values(vol_data)
            # Remove negative values from water use dataset
            vol_data2 = remove_negative_values(vol_data)
            
            ## Create monthly summary stats and export to Excel
            if export_response in ['s', 'b']:
                print("Calculating monthly statistics")
                # Calculate spike detection parameters
                mean, sd = calculate_spike_parameters(vol_data2)
                # Detect spikes
                vol_stats = detect_spikes(vol_data2, mean, sd)
                # Summarise water use statistics by day
                daily_stats = generate_daily_stats(vol_stats)
                # Summarise water use statistics by month
                monthly_stats = generate_monthly_stats(daily_stats)
                # Summarise extraction statistics by month
                extraction_stats = generate_extraction_stats(vol_data2)
                # Combine monthly stats
                monthly_stats2 = combine_monthly_stats(monthly_stats, extraction_stats)
                # Export water use statistics to Excel
                export_monthly_stats(mslist2, monthly_stats2, neg_summary, site)
            else:
                print("Monthly statistics have been bypassed")
        
            ## Generate time series plots
            if export_response in ['p', 'b']:
                print("Generating time series plots")
                # Get consent conditions
                site_id = site.split('-')[0]
                consents = get_consent_conditions(site_id)     
                # Scenario 1 (no consents, no extra features to add to plots)
                if len(consents) == 0:
                    plot_data = process_plot_data1(vol_data2)
                    generate_daily_plots1(plot_data, site)            
                #Scenario 2 (has consents, add extra features to plots)
                elif len(consents) >= 1:
                    max_rate, max_vol, multiday_vol, return_period = summarise_consent_conditions(consents)
                    plot_data = process_plot_data2(vol_data2, return_period)
                    generate_daily_plots2(plot_data, site, max_rate, max_vol, multiday_vol, return_period)                
            else:
                print("Time series plots have been bypassed")
                print("Process completed")
            
        # Report if a site is not in the WaterUse.hts file                 
        except:
            print("{0} has no data in the Hilltop WaterUse.hts file".format(site))
    
main()