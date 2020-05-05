# TMfS18 Trip End Model

This is the first stage of the trip end model for TMfS18. The process produces the underlying car and public transport travel demand inputs for the demand model including movements associated with airport zones.

## Usage

### Structure
The trip end model relies on defined folder structures. The following 2 directories must be specified:

 * Delta Root
 * TMfS Root

Delta root contains sub-folders named after the scenario code with the TELMoS planning data within them. E.g.

 * Delta Root
  * DL
    * tav_18DL.csv
    * tmfs_18DL.csv
    * trfl18DL.dat


TMfS Root contains the 'Factors' folder and the 'Runs' folder. 'Factors' has the trip rates, area definitions, and growth rates required by the trip end model. 'Runs' contains the base year trip ends and the output from the trip end model. It has the following structure:

* TMfS Root 
  * Runs
    * 18
        * Demand
            * ADL
    * 20 
        * Demand
            * BDL
