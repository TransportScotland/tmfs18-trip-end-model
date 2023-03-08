# Introduction

## Overview
The Trip End Model contains two main stages:

**Stage 1:** Prepares the underlying car and public transport travel
demand inputs for the TMfS demand model (i.e. trip ends). These trip
ends include movements associated with airport zones. This stage of
the Trip End Model is scripted in the Python programming language
based on previous Visual Basic applications; and

**Stage 2:** Prepares 'add in' matrices (using a Cube Voyager
application), which are travel demand inputs used within the TMfS
forecasting process, but not part of the core demand model. The Cube
Voyager application uses inputs created from Stage 1 to generate
education travel matrices, external trips (travel movements with an
origin or destination located outside Scotland), and goods vehicle
movements.

## Trip End Model History

This TMfS18 Trip End Model was developed based on previous versions
developed and updated as part of TMfS. The Trip End Model was originally
a spreadsheet type model developed for TMfS02. This process was updated
during the development of TMfS05 to include goods vehicle matrix
creation processes controlled by Visual Basic programming. The TMfS18
Trip End Model uses a combination of Python programming and Cube Voyager
software.
