#!/bin/bash
inp_vid="videos/class_04_25_19_1sec.mp4"
sav_box="boxes/class_04_25_19_1sec.pkl"
sav_vid="videos/class_04_25_19_1sec_out.mp4"
ove_vid="videos/class_04_25_19_1sec_overlay.avi"
con_vid="videos/class_04_25_19_1sec_overlay.mp4"
imdir="images"
data="records.db"
loc="TJ200C"
fps=60
dtime="2019-05-10"
inp_mod="models/class.h5"

source ~/miniconda3/etc/profile.d/conda.sh

echo "Detecting Faces In Video " $inp_vid " taken at " $loc " and taken in " $fps " frames per second"
python3 detection.py --video $inp_vid --track --no-display --save-boxes $sav_box --save-video $sav_vid --imagedir $imdir --database $data --location $loc --fps $fps
echo "Saved Data to " $data " and raw images to " $imdir " and boxes at " $sav_box

echo "Classifying Faces From Database " $data " taken on " $dtime " at " $loc " with model " $inp_mod
conda activate sys
python3 class_train.py --database $data --datetime $dtime --location $loc --load $inp_mod --test 
echo "Saved Classifications To " $data

echo "Leaving Conda Environment"
conda deactivate

echo "Overlaying Video " $inp_vid " taken on " $dtime " at " $loc " in " $fps " frames per second to " $ove_vid
python3 tag.py --database $data --datetime $dtime --location $loc --names --option 9 --video $inp_vid --save-video $ove_vid --fps $fps

echo "Converting Video " $ove_vid " To " $con_vid
ffmpeg -i $ove_vid $con_vid

echo "Finished"

