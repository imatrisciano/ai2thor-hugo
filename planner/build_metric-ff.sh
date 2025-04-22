#!/bin/sh

echo "Updating source code..."
#Download/update metric-ff source code
git submodule update --init

echo "Building..."
#Build metric-ff v1.0
make -C metric-ff-crossplatform/v1.0/

echo "Copying bianry..."
#Copy compiled binary into the metric-ff folder
cp metric-ff-crossplatform/ff-v1.0 metric-ff/ff

echo "Done."
