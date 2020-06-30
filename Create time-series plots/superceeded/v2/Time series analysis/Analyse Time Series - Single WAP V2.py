"""
This program analyses and visualises water use data for a WAP of interest, over
the course of the entire Hilltop time-series.

Author: Alan Ambury
Last Edited: 24 May 2020
Contact the developer: alan@whiterockconsulting.co.nz

Inputs to the program:
1. The user needs to specify the WAP of interest.
2. The user needs to specify if they wish to export Statistics [s], Plots [p]
   or Both [b].

Outputs of the program:
Depending on the user's export preferences the program will create:
1. A spreadsheet containing a summary of a) water use data that is
available in Hilltop, b) negative values removed from the data, and 
c) monthly water use statistics.
2. A pdf file containing a collection of time-series plots.

In order to run the program the user needs to:
1. Have installed the hilltop-py package developed by Mike Exner-Kittridge
2. Have installed the pandas, numpy, seaborn, matplotlib and datetime modules
(NB: these come packaged with the Anaconda distribution of Python).
"""

import numpy as np
import pandas as pd
import seaborn as sns
import datetime as dt
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from hilltoppy import web_service as ws


def get_site():
    """This function prompts the user to enter the WAP that they wish to generate plots for"""
    site = None
    while site is None:
        site_entry = input("Enter the WAP of interest: ")
        site_list = ws.site_list('http://wateruse.ecan.govt.nz', 'WaterUse.hts')
        if site_entry in site_list.values:
            site = site_entry
        else:
            print("The WAP you have entered is not in the WaterUse.hts file. Please try again.")
    return site


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


def process_measurement_list(dataframe):
    """This function prepares the measurement list so that it can be used to 
    extract water use data"""
    processed_list = dataframe.copy()
    # Add a default start date is start date is null
    if processed_list['From'].isnull().values.any():
        processed_list['From'] = processed_list['From'].fillna(pd.Timestamp('2000-01-01 00:00:00'))
    # Order by start date
    processed_list2 = processed_list.sort_values(by=['From'], ascending=True).reset_index(drop=True)
    # Add date attributes
    processed_list2['FromDate'] = processed_list2['From'].dt.date
    processed_list2['ToDate'] = processed_list2['To'].dt.date
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
    neg_values = len(dataframe) - len(vol_data2)
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
    monthly_stats.rename(columns={'Measurement_max': 'Measurement type', 'Vol_count':'Days with data',
                                  'Vol_sum':'Meter reports', 'sd5_sum':'Spikes > 5sd','sd10_sum':'Spikes > 10sd',
                                  'sd20_sum':'Spikes > 20sd'}, inplace=True)    
    
    return monthly_stats


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
    worksheet.set_column('A:G', 20) 
    # Save file
    writer.save()


def process_plot_data(dataframe):
    """This function calculates daily totals, adds in any days that are missing data and gets the
    dataframe ready for plotting"""
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
    daily_counts2['MA30'] = daily_counts2.Volume.rolling(window=30, min_periods=21).mean()
    # Set missing reading counts to 0
    daily_counts2['Readings'].fillna(value=0, inplace=True)
    return daily_counts2
    

def generate_daily_plots(dataframe, site):
    """This function generates the daily plots and outputs them to a pdf file"""
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
    if grid_count < 12:
        plt.subplots_adjust(top=0.7)
    elif grid_count >= 12 and grid_count <= 24:
        plt.subplots_adjust(top=0.8)
    else:
        plt.subplots_adjust(top=0.9)
    daily_vol_grid.fig.suptitle('Daily volume extracted in m3')
    daily_vol_grid.savefig(pp, format='pdf')
    plt.close()
    # Create line plot of 30 day moving average
    daily_ma30_grid = sns.FacetGrid(dataframe, col="Month", hue="Month",
                    col_wrap=12, height=1.5, dropna=False)
    daily_ma30_grid.map(plt.plot, "Day", "MA30")
    daily_ma30_grid.fig.tight_layout(w_pad=1)
    if grid_count < 12:
        plt.subplots_adjust(top=0.7)
    elif grid_count >= 12 and grid_count <= 24:
        plt.subplots_adjust(top=0.8)
    else:
        plt.subplots_adjust(top=0.9)
    daily_ma30_grid.fig.suptitle('Volume extracted (m3) - 30 day moving average (21 days required)')
    daily_ma30_grid.savefig(pp, format='pdf')
    plt.close()
    # Create line plot of daily extraction rates
    daily_rate_grid = sns.FacetGrid(dataframe, col="Month", hue="Month",
                    col_wrap=12, height=1.5, dropna=False)
    daily_rate_grid.map(plt.plot, "Day", "Rate")
    daily_rate_grid.fig.tight_layout(w_pad=1)
    if grid_count < 12:
        plt.subplots_adjust(top=0.7)
    elif grid_count >= 12 and grid_count <= 24:
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
    # Get site
    site = get_site()
    # Get export preferences
    export_response = get_export_response()
    
    ## Initial extraction and processing
    # Extract measurement list
    mslist = get_measurement_list(site)
    # Process measurement list
    mslist2 = process_measurement_list(mslist)
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
        # Export water use statistics to Excel
        export_monthly_stats(mslist2, monthly_stats, neg_summary, site)
    else:
        print("Monthly statistics have been bypassed")

    ## Generate time series plots
    if export_response in ['p', 'b']:
        print("Generating time series plots")
        # Prepare water use data for plotting
        plot_data = process_plot_data(vol_data2)
        # Generate plots and export to pdf
        generate_daily_plots(plot_data, site)
    else:
        print("Time series plots have been bypassed")
        
    print("Process completed")
    
main()