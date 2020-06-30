"""
This program analyses and visualises water use data for a WAP of interest, for
a specified month.

Author: Alan Ambury
Last Edited: 24 May 2020
Contact the developer: alan@whiterockconsulting.co.nz

Inputs to the program:
1. The user needs to specify the WAP of interest.
2. The user needs to specify the start date of the month of interest.

Outputs of the program:
1. If the WAP has one or more measurement type in Hilltop - for the month of 
interest - a separate PDF file is generated for each measurement type. Each PDF
file contains plots of a) the number of water meter readings per hour and 
b) volumes extracted per hour, over a 35 day period.

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


def get_date():
    """This function prompts the user to enter the start date for the month of interest"""
    user_date = None
    while user_date is None:
        date_entry = input("Enter the start date for the plots in YYYY-MM-DD format: ")
        try:
            year, month, day = map(int, date_entry.split('-'))
            user_date = dt.date(year, month, day)
            print("Data will be extracted for the 35 days starting on {}".format(user_date))
        except ValueError:
            print("Not a valid date. Please try again using YYYY-MM-DD format")        
    return user_date


def get_measurement_list(site):
    """Extracts the measurement types that are available in the Hilltop WaterUse.hts file
    for a given site"""
    base_url = 'http://wateruse.ecan.govt.nz'
    hts = 'WaterUse.hts'
    raw_list = ws.measurement_list(base_url, hts, site)
    raw_list2 = raw_list.reset_index()    
    filtered_list = raw_list2.loc[raw_list2['Measurement'].isin(['Compliance Volume','Water Meter','Volume','Volume [Flow]','Volume [Average Flow]'])]
    return filtered_list


def extract_water_use_data(site, measurement, from_d, to_d):
    """This function extracts water use data from Hilltop, and compiles it into a dataframe"""
    # Set base parameters
    base_url = 'http://wateruse.ecan.govt.nz'
    hts = 'WaterUse.hts'
    tsdata = ws.get_data(base_url, hts, site, measurement, from_date=str(from_d), to_date=str(to_d))
    tsdata2 = tsdata.reset_index().drop(columns='Site')
    return tsdata2


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


def process_hourly_data(dataframe):
    """This function calculates hourly totals, adds in any days that are missing data and gets the
    dataframe ready for plotting"""
    # Add time variables
    dataframe['Date'] = dataframe['DateTime'].dt.date
    dataframe['Year'] = dataframe['DateTime'].dt.year
    dataframe['Month'] = dataframe['DateTime'].dt.month 
    dataframe['DayVal'] = dataframe['DateTime'].dt.day
    dataframe['Hour'] = dataframe['DateTime'].dt.hour
    # Group by hour
    hourly_vol = dataframe.groupby(['Date','Month','DayVal','Hour'])['Vol'].agg(['count', 'sum']).rename(columns={'count':'Readings', 'sum':'Volume'}).reset_index()
    return hourly_vol


def add_missing_dates(hourly_vol1, from_date, to_date):
    """This function identifies days that are missing data and adds them to the main dataframe"""
    # Generate a full list of dates
    alldates_timestamp = pd.date_range(from_date, to_date)
    alldates_datetime = alldates_timestamp.to_pydatetime()
    alldates = []
    for item in alldates_datetime:
        date = item.date()
        alldates.append(date)
    # Generate a list of dates that have data
    dates_with_data = hourly_vol1['Date'].unique().tolist()
    # Generate a list of dates that are missing data
    missing_dates = list(set(alldates) - set(dates_with_data))
    # Convert to dataframe
    missing_df = pd.DataFrame(missing_dates, columns = ['Date'])
    # Merge into dataset
    hourly_vol2 = pd.merge(hourly_vol1, missing_df, on='Date', how='outer')
    # Tidy up dataframe
    hourly_vol2['Readings'].fillna(0, inplace=True)
    hourly_vol2['Volume'].fillna(0, inplace=True)
    hourly_vol2['Hour'].fillna(0, inplace=True)
    hourly_vol2['Date'] = pd.to_datetime(hourly_vol2['Date'])
    hourly_vol2['DayVal'] = hourly_vol2['Date'].dt.day
    hourly_vol2['Month'] = hourly_vol2['Date'].dt.month
    hourly_vol2['Year'] = hourly_vol2['Date'].dt.year
    hourly_vol2['Hour'] = hourly_vol2['Hour'].astype(int)
    hourly_vol2['Readings'] = hourly_vol2['Readings'].astype(int)
    hourly_vol2['Volume'] = hourly_vol2['Volume'].astype(int)
    # Add in extra date labels needed for plotting
    hourly_vol2['DayVal2'] = hourly_vol2['DayVal'].apply(lambda x: '{0:0>2}'.format(x))
    hourly_vol2['Day'] = hourly_vol2['Year'].astype(str) + "/" + hourly_vol2['Month'].astype(str) + "/" + hourly_vol2['DayVal'].astype(str)    
    # Sort by date and hour
    hourly_vol2.sort_values(by=['Date','Hour'], inplace=True)
    # Drop last row
    hourly_vol2.drop(hourly_vol2.tail(1).index,inplace=True)
    return hourly_vol2

   
def generate_hourly_plots(dataframe, site, measurement, from_date):
    """This function generates the hourly plots and outputs them to a pdf file"""
    # Open pdf
    filename = site.replace('/','-') + ' - {0} - 35 days from {1}'.format(measurement, from_date)
    pp = PdfPages(filename + '.pdf')
    # Create bar plot of meter readings
    hourly_report_grid = sns.FacetGrid(dataframe, col="Day", hue="Day",
                         col_wrap=7, height=1.5)  
    hourly_report_grid.map(plt.bar, "Hour", "Readings")
    hourly_report_grid.fig.tight_layout(w_pad=1)
    plt.subplots_adjust(top=0.9)
    hourly_report_grid.fig.suptitle('Meter readings received (hourly)')
    hourly_report_grid.savefig(pp, format='pdf')
    plt.close()
    # Create line plot of hourly volumes
    hourly_vol_grid = sns.FacetGrid(dataframe, col="Day", hue="Day",
                         col_wrap=7, height=1.5, dropna=False)
    hourly_vol_grid.map(plt.plot, "Hour", "Volume")
    hourly_vol_grid.fig.tight_layout(w_pad=1)
    plt.subplots_adjust(top=0.9)
    hourly_vol_grid.fig.suptitle('Volume extracted in m3 (hourly)')
    hourly_vol_grid.savefig(pp, format='pdf')
    plt.close()
    #Close pdf file
    pp.close()    

    
def main():
    """This function controls the execution of the main program"""
   # Get site
    site = get_site()
    # Get start date
    start_date = get_date()    
    # Generate extraction dates
    end_date = start_date + dt.timedelta(days = 35)
    # Extract measurement list
    mslist = get_measurement_list(site) 
    # Extraction and plotting
    for index, row in mslist.iterrows():
        measurement = row['Measurement']
        try:
            # Extract water use data
            wu_data = extract_water_use_data(site, measurement, start_date, end_date)
            # Convert water use data to a common unit
            vol_data = convert_water_use_data(wu_data)
            # Process hourly data
            hourly_vol = process_hourly_data(vol_data)
            # Add any missing dates
            hourly_vol2 = add_missing_dates(hourly_vol, start_date, end_date)
            # Create plots
            print("Creating plots for {} data".format(measurement))
            generate_hourly_plots(hourly_vol2, site, measurement, start_date)               
        except ValueError:
            print("There is no {} data to plot".format(measurement))
    print("Process completed")
main()