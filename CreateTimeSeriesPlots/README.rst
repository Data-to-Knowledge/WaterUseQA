=============================================================================
Water Use Data Assessment Part 2: Time-series Analysis and Visualisation
=============================================================================

Aims
=====

Part 2 of the project aims to create analytical tools that can be used to analyse and visualise the entire water use time-series for selected WAPs. The tools are intended to support work such as catchment modelling, which requires detailed assessment of historic water use data.

Requirements
---------------

In order to run the associated Python programs the user will need to have installed:

-	Python Anaconda (and the pandas, seaborn, matplotlib and datetime modules)  
-	The hilltop-py package developed by Mike Exner-Kitteridge.

Two of the Python programs (which deal with consent conditions) also require access to the CrcActSiteSumm table. This table is stored in the ConsentsReporting database on the edwprod01 server.

Python Programs
-----------------

Four sets of programs have been developed that are intended to let the user explore water use data in differing levels of detail:

1.	Water meter list generator (created by HG & MEK Environment Canterbury)
2.	Quality Assessment programs
3.	Time-series Analysis programs
4.	Monthly Visualisation programs

1.	Water meter list generator (created by HG & MEK Environment Canterbury)
==========================================================================

This program generates a list of water meters for a user defined catchment.
Line 57 of the script is where the user will define the catchment of interest. Example below:

-	site_filter = {'SwazName': ['Hakataramea River']}

2.	Quality Assessment Programs
=============================

These programs provide the most general assessment. They are intended to be run over a list of WAPs to give an initial assessment of the water use data that exists for each WAP, and the quality of that data. 

There are two variations of the Quality Assessment programs.

Quality Assessment - WAP List - Combined Series V2.py
--------------------------------------------------------

Input:
	A csv file containing a list of WAPs
Output:
	An Excel spreadsheet containing QA statistics
Description:
	Hilltop sometimes contains multiple measures of water use for a single WAP (eg, some combination of Compliance Volume, Volume, Volume [Flow], Volume [Average Flow], or Water Meter measurements). In order to produce time series plots it is necessary to stitch these different measures together while taking care to avoid overlaps. This program lets you perform a quality assessment on the ‘Combined Series’ that is used to produce the time-series plots.
Notes on the ‘Combined Series':
	When a WAP has more than one measure of water use for a given period of time, it is necessary to include just one of these measures (so as to avoid double or triple counting water use). The method used in this program to create a ‘Combined Series’ is as follows:

1.	Find the measurement type with the earliest start date (Measurement 1) and extract the entire time-series for Measurement 1.
2.	If there is another measurement type with data that follows on from Measurement 1, extract data for this measurement type (Measurement 2). Avoid any overlap with Measurement 1 by using the end_date for Measurement 1 to determine the start_date for Measurement 2.
3.	Repeat this process for any additional measurement types.



=============================================	 ===========================================================	==================================================================================================================
Water use data in Hilltop                    	 Water use data included in Combined series						Notes
=============================================	 ===========================================================	==================================================================================================================
Compliance volume (01/07/2012 to 08/05/2016)	 Water use data from 01/07/2012 to 08/05/2016 is included		This is classified as Measurement 1 and the entire time series is extracted
Volume (01/07/2015 to 30/06/2019)				 Data from 09/05/2016 to 30/06/2019 is included					The start date for the extraction (09/05/2016) is the day that follows the end of the Measurement 1 time series
=============================================    ===========================================================    ==================================================================================================================




Quality Assessment - WAP List – By Measurement Type V2.py
-----------------------------------------------------------

Input:
	A csv file containing a list of WAPs
Output:
	An Excel spreadsheet containing QA statistics
Description:
	This variation produces a quality assessment for each type of water use measurement that a WAP has. For example, in the case of BY20/0088-M1 which has two measurement types, a quality assessment is provided for each of the two data series (Compliance Volume and Volume).



