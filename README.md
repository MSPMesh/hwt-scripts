# hwt-scripts
A collection of scripts for processing and combining "splash" data from https://www.heywhatsthat.com/   
## Usage   
These scripts require `python` and the `pillow` python package.   
```bash
pip install pillow
```
Create a splash on HWT and click the `View in Google Earth: day` button near the top right of the website to export the data as a KMZ file. Once you have one or more of these KMZ files, place them in the same folder as the python scripts.  
Then run one of the following commands to process the KMZ files:

### To create a single KMZ file with all the data combined:  
```bash
python merge_kmz.py
```
This will create a new file called `CombinedSanitized.kmz` in the same folder that contains all the data from the KMZ files. The color of the splash will be based on the number of overlapping splashes. The color scale is as follows:
- 1 splash: Red
- 2 splashes: Yellow
- 3+ splashes: Green

### To rank the KMZ files by their splash coverage:  
```bash 
python rank_kmz.py
``` 
Will order all the nodes by how much coverage they have in pixels and in square miles. The output will be a CSV string that will be printed to the console. 


### To strip out identifying information from the KMZ files:  
```bash
python strip_kmz.py
```
This will edit each KMZ file in place and remove the identifying information from the splash. 

### To un-merge a KML file exported from Google Earth:  
```bash
python unmerger.py
```
This will look for a KML file in the same folder as the script and unmerge it into separate KMZ files. 