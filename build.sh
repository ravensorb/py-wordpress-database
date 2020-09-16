#!/bin/bash

echo "-------------------------------------------------------------------------------------------"
echo "Incrementing Version..."
if [ "$1" == "bump" ]; then
    bumpversion patch
fi

echo "-------------------------------------------------------------------------------------------"
echo "Building..."
python3 setup.py build
python3 setup.py sdist bdist_wheel

echo "-------------------------------------------------------------------------------------------"
echo "Validating"
twine check dist/*
retVal=$?
if [ $retVal -ne 0 ]; then
    echo "Error in package. Please fix and try again..."
    exit $retVal
fi

echo "-------------------------------------------------------------------------------------------"
echo "Installing Locally"
sudo python3 setup.py install
echo "-------------------------------------------------------------------------------------------"

rm -r *.egg-info
