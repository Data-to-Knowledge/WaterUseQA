"""
This program performs a quick quality assessment for a list of WAPs, focused
on water use data in Hilltop.

Author: Alan Ambury
Last Edited: 24 May 2020
Contact the developer: alan@whiterockconsulting.co.nz

Inputs to the program:
1. The user needs to specify a csv file that contains a list of WAPs

Outputs of the program:
1. A spreadsheet containing summary statistics for each WAP

In order to run the program the user needs to:
1. Have installed the hilltop-py package developed by Mike Exner-Kittridge
2. Have installed the pandas, numpy, and datetime modules
(NB: these come packaged with the Anaconda distribution of Python).
"""

import numpy as np
import pandas as pd
import datetime as dt
from hilltoppy import web_service as ws
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


def extract_and_combine_data(dataframe, site):
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
                tsdata = ws.get_data(base_url, hts, site, measurement, from_date=str(from_d), to_date=str(to_d))
                tsdata2 = tsdata.reset_index().drop(columns='Site')
                raw_data = pd.concat([raw_data, tsdata2], ignore_index=True)
                # Adjust start date to prevent overlapping time series
                from_d = to_d + dt.timedelta(days=1)
            except:
                from_d = to_d + dt.timedelta(days=1)
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
    neg_count = neg_filter.count()['Vol']
    return neg_count


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


def generate_summary_stats(dataframe, site, data_exists, meas_types, neg_count, mean):
    """This function generates daily water use statistics"""
    # meas_types
    meas_used = dataframe['Measurement'].nunique()
    start_date = dataframe['Date'].min()  
    end_date = dataframe['Date'].max()
    total_days = (end_date - start_date).days + 1
    days_with_data = dataframe['Date'].nunique()
    total_reports = dataframe['Vol'].count()
    # neg_count
    min_extraction = dataframe[dataframe['Vol']>0].min()['Vol']
    # mean
    max_extraction = dataframe['Vol'].max()
    sd5 = dataframe['sd5'].sum()
    sd10 = dataframe['sd10'].sum()
    sd20 = dataframe['sd20'].sum()
    # Write summary stats to dataframe
    stats = {'Site':site, 'InHilltop':data_exists, 'MeasTypes':meas_types, 'MeasUsed':meas_used, 
             'StartDate':start_date, 'EndDate':end_date, 'TotalDays':total_days,
             'DaysWithData':days_with_data, 'TotalReports':total_reports,
             'MinExtraction': round(min_extraction, 3), 'MeanExtraction': round(mean, 1),
             'MaxExtraction':round(max_extraction, 1), 'NegativeValues':neg_count,
             'Spikes > 5sd':sd5, 'Spikes > 10sd':sd10, 'Spikes > 20sd':sd20}
    stats_df = pd.DataFrame(data=stats, index=['Default'])
    return stats_df


def record_missing_site(site, data_exists):
    """This function adds a row to the results dataframe when a site has no Hilltop data"""
    # Write summary information to dataframe
    stats = {'Site':site, 'InHilltop':data_exists, 'MeasTypes':'', 'MeasUsed':'',
             'StartDate':'', 'EndDate':'', 'TotalDays':'',
             'DaysWithData':'', 'TotalReports':'', 'MinExtraction':'',
             'MeanExtraction':'', 'MaxExtraction':'', 'NegativeValues':'',
             'Spikes > 5sd':'', 'Spikes > 10sd':'', 'Spikes > 20sd':''}    
    missing_df = pd.DataFrame(data=stats, index=['Default'])
    return missing_df    


def export_summary_stats(dataframe, csv_input):
    """This function exports water use statistics to Excel"""
    # Create Excel file
    writer = pd.ExcelWriter('QA for Sites in {} - Combined Series.xlsx'.format(csv_input), engine='xlsxwriter')
    # Export measurement list
    dataframe.to_excel(writer, sheet_name='QualityAssessment')
    worksheet = writer.sheets['QualityAssessment']
    worksheet.set_column('A:A', 3)
    worksheet.set_column('B:B', 15)
    worksheet.set_column('C:C', 8)
    worksheet.set_column('D:H', 12)
    worksheet.set_column('I:N', 15)
    worksheet.set_column('O:Q', 12)    
    # Save file
    writer.save()


def main():
    """This function controls the execution of the main program"""
    
    # Get site list
    csv_input = get_filename()
    site_list = read_csv(csv_input)
    
    # Create empty dataframe to append results into
    master = pd.DataFrame(columns = ['Site','InHilltop','MeasTypes','MeasUsed','StartDate','EndDate',
                                     'TotalDays','DaysWithData','TotalReports','MinExtraction',
                                     'MeanExtraction','MaxExtraction','NegativeValues','Spikes > 5sd',
                                     'Spikes > 10sd','Spikes > 20sd'])     
       
    # Iterate through site list
    for wap in site_list:
        site = wap.rstrip("\n")
        print("Processing {}".format(site))
        
        try:
            # Extract measurement list
            mslist = get_measurement_list(site)
            meas_types = len(mslist)
            data_exists = 'Y'
        except ValueError:
            print("{0} has no data in the Hilltop WaterUse.hts file".format(site))            
            data_exists = 'N'
        
        if data_exists == 'Y':
            # Process measurement list
            mslist2 = process_measurement_list(mslist)
            # Extract water use data
            wu_data = extract_and_combine_data(mslist2, site)
            # Convert water use data to a common unit
            vol_data = convert_water_use_data(wu_data)          
            # Summarise any negative values in the water use dataset
            neg_count = summarise_negative_values(vol_data)
            # Remove negative values from water use dataset
            vol_data2 = remove_negative_values(vol_data)
            # Calculate spike detection parameters
            mean, sd = calculate_spike_parameters(vol_data2)            
            # Detect spikes
            vol_stats = detect_spikes(vol_data2, mean, sd)         
            # Summarise water use statistics
            summary_stats = generate_summary_stats(vol_stats, site, data_exists, meas_types, neg_count, mean)
            # Append into results dataframe
            master = pd.concat([master, summary_stats], ignore_index=True)
        
        elif data_exists == 'N':
            # Record missing site
            missing_info = record_missing_site(site, data_exists)
            # Append into results dataframe
            master = pd.concat([master, missing_info], ignore_index=True) 
        
    # Export water use statistics to Excel
    export_summary_stats(master, csv_input)
    print("")
    print("Quality Assessment has been exported to Excel")

main()