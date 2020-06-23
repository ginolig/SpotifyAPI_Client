# SpotifyAPI_Client
Not (yet) fully implemented Client for the Spotify API (https://developer.spotify.com/).

I started following this [excellent tutorial](https://youtu.be/xdq6Gz33khQ) and then implemented some functions by my own.
A specific thing I wanted was to be able to create and update a public playlist, whose contents were all the songs I have liked.

It was made using Jupyter Notebook via pipenv, so you may want to install them (or just grab the ```cliente_spotify.py``` file).

Oh and that minimal GUI is in Spanish.

## Install Instructions
#### This is only if you want to setup a virtual environment and use Jupyter for development stages.
1. If you don't have pipenv, install it using: ```pip install pipenv```.
2. Clone this repo somewhere and navigate to the folder.
3. Create the virtual environment with python 3.8 and install Jupyter: ```pipenv install --python 3.8 jupyter```.
4. Run Jupyter: ```pipenv run jupyter notebook```. You must be where you created the virtual env (root of cloned repository).
